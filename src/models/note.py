from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    images = db.relationship('NoteImage', back_populates='note',
                             cascade='all, delete-orphan', lazy='selectin',
                             order_by='NoteImage.id')
    
    def __repr__(self):
        return f'<Note {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'images': [image.to_dict() for image in self.images],
        }


class NoteImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    data = db.deferred(db.Column(db.LargeBinary, nullable=False))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.relationship('Note', back_populates='images')

    def to_dict(self):
        return {'id': self.id, 'note_id': self.note_id, 'filename': self.filename,
                'content_type': self.content_type, 'size': self.size,
                'url': f'/api/notes/{self.note_id}/images/{self.id}'}
