from datetime import datetime
from io import BytesIO
from pathlib import Path
import warnings

from flask import Blueprint, current_app, jsonify, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from werkzeug.utils import secure_filename
from src.models.note import Note, NoteImage, db
from translator import translate_note

note_bp = Blueprint('note', __name__)
register_heif_opener(thumbnails=False)


@note_bp.route('/notes/<int:note_id>/images', methods=['POST'])
def upload_note_image(note_id):
    note = db.session.get(Note, note_id)
    if note is None:
        return jsonify(error='Note not found'), 404
    upload = request.files.get('image')
    if upload is None or not upload.filename:
        return jsonify(error='Select an image file.'), 400
    limit = current_app.config.get('MAX_IMAGE_BYTES', 5 * 1024 * 1024)
    limit_mb = limit // (1024 * 1024)
    data = upload.stream.read(limit + 1)
    if len(data) > limit:
        return jsonify(error=f'Maximum image size is {limit_mb} MB.'), 413
    formats = {'PNG': 'image/png', 'JPEG': 'image/jpeg',
               'GIF': 'image/gif', 'WEBP': 'image/webp', 'HEIF': 'image/jpeg'}
    filename = (secure_filename(upload.filename) or 'image')[:255]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in formats:
                    return jsonify(error='Use a PNG, JPEG, GIF, WebP, HEIC, or HEIF image.'), 400
                content_type = formats[image.format]
                if image.width * image.height > 40000000:
                    return jsonify(error='Image dimensions are too large (maximum 40 megapixels).'), 400
                if image.format == 'HEIF':
                    # iPhone images may contain HEIC bytes even with a .jpg name.
                    # Decode and normalize for browsers that cannot display HEIC.
                    converted = ImageOps.exif_transpose(image).convert('RGB')
                    buffer = BytesIO()
                    converted.save(buffer, format='JPEG', quality=90)
                    converted.close()
                    data = buffer.getvalue()
                    filename = Path(filename).stem[:250] + '.jpg'
                    if len(data) > limit:
                        return jsonify(error=f'Converted image exceeds {limit_mb} MB. Please upload a smaller image.'), 413
                else:
                    image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        return jsonify(error='Cannot read this image. Please use a valid PNG, JPEG, GIF, WebP, HEIC, or HEIF file.'), 400
    attachment = NoteImage(
        note=note, filename=filename,
        content_type=content_type, size=len(data), data=data,
    )
    note.updated_at = datetime.utcnow()
    db.session.add(attachment)
    db.session.commit()
    return jsonify(attachment.to_dict()), 201


@note_bp.route('/notes/<int:note_id>/images/<int:image_id>', methods=['GET'])
def get_note_image(note_id, image_id):
    image = NoteImage.query.filter_by(id=image_id, note_id=note_id).first()
    if image is None:
        return jsonify(error='Image not found'), 404
    response = send_file(BytesIO(image.data), mimetype=image.content_type,
                         download_name=image.filename, max_age=0)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@note_bp.route('/notes/<int:note_id>/images/<int:image_id>', methods=['DELETE'])
def delete_note_image(note_id, image_id):
    image = NoteImage.query.filter_by(id=image_id, note_id=note_id).first()
    if image is None:
        return jsonify(error='Image not found'), 404
    image.note.updated_at = datetime.utcnow()
    db.session.delete(image)
    db.session.commit()
    return '', 204


@note_bp.route('/notes/translate', methods=['POST'])
def translate_note_draft():
    """Return a translated draft as JSON; saving is a separate action."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    try:
        result = translate_note(
            data.get('title', ''), data.get('content', ''),
            data.get('target_language', 'Simplified Chinese'),
        )
        return jsonify(result)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except RuntimeError as error:
        return jsonify({'error': str(error)}), 502

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        note = Note(title=data['title'], content=data['content'])
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not create note. Check the database connection.'}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not update note. Check the database connection.'}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Could not delete note. Check the database connection.'}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])
