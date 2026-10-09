import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateTable

from src.app import create_app
from src.database import import_sqlite, neon_database_url
from src.models.note import Note, NoteImage
from src.models.user import db


class DatabaseImageTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def note(self, title='Photo note'):
        response = self.client.post('/api/notes', json={'title': title, 'content': 'Hello'})
        self.assertEqual(response.status_code, 201)
        return response.json['id']

    def image_bytes(self, image_format='PNG'):
        buffer = io.BytesIO()
        Image.new('RGB', (8, 8), 'blue').save(buffer, format=image_format)
        return buffer.getvalue()

    def upload(self, note_id, data, filename='photo.png'):
        return self.client.post(f'/api/notes/{note_id}/images',
                                data={'image': (io.BytesIO(data), filename)},
                                content_type='multipart/form-data')

    def test_upload_persistence_metadata_download_and_delete(self):
        note_id = self.note()
        data = self.image_bytes()
        response = self.upload(note_id, data, '../../photo.png')
        self.assertEqual(response.status_code, 201)
        image = response.json
        self.assertEqual(image['filename'], 'photo.png')
        self.assertEqual(image['content_type'], 'image/png')
        self.assertEqual(image['size'], len(data))
        db.session.remove()
        stored = self.client.get(f'/api/notes/{note_id}').json
        self.assertEqual(stored['images'][0]['id'], image['id'])
        self.assertNotIn('data', stored['images'][0])
        downloaded = self.client.get(image['url'])
        self.assertEqual(downloaded.data, data)
        self.assertEqual(downloaded.headers['X-Content-Type-Options'], 'nosniff')
        another_note = self.note('Another')
        self.assertEqual(self.client.get(f"/api/notes/{another_note}/images/{image['id']}").status_code, 404)
        self.assertEqual(self.client.delete(image['url']).status_code, 204)
        self.assertEqual(self.client.get(image['url']).status_code, 404)
        self.assertEqual(self.client.get(f'/api/notes/{note_id}').json['images'], [])

    def test_deleting_note_removes_image_data(self):
        note_id = self.note()
        uploaded = self.upload(note_id, self.image_bytes()).json
        self.assertEqual(self.client.delete(f'/api/notes/{note_id}').status_code, 204)
        self.assertEqual(NoteImage.query.count(), 0)
        self.assertEqual(self.client.get(uploaded['url']).status_code, 404)

    def test_invalid_files_and_limits(self):
        note_id = self.note()
        for data in (b'', b'not an image', b'<svg></svg>'):
            self.assertEqual(self.upload(note_id, data).status_code, 400)
        self.assertEqual(self.client.post(f'/api/notes/{note_id}/images').status_code, 400)
        self.assertEqual(self.upload(999, self.image_bytes()).status_code, 404)
        self.app.config['MAX_IMAGE_BYTES'] = 8
        self.assertEqual(self.upload(note_id, self.image_bytes()).status_code, 413)
        self.assertEqual(NoteImage.query.count(), 0)

    def test_supported_image_formats(self):
        note_id = self.note()
        for image_format in ('PNG', 'JPEG', 'GIF', 'WEBP'):
            self.assertEqual(self.upload(note_id, self.image_bytes(image_format)).status_code, 201)

    def test_heic_bytes_with_jpeg_filename_are_converted(self):
        note_id = self.note()
        data = self.image_bytes('HEIF')
        self.assertNotEqual(data[:2], b'\xff\xd8')
        response = self.upload(note_id, data, 'iphone-photo.jpg')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['filename'], 'iphone-photo.jpg')
        self.assertEqual(response.json['content_type'], 'image/jpeg')
        downloaded = self.client.get(response.json['url'])
        with Image.open(io.BytesIO(downloaded.data)) as image:
            self.assertEqual(image.format, 'JPEG')
            image.load()
            self.assertEqual(image.size, (8, 8))

    def test_heic_extension_is_normalized(self):
        note_id = self.note()
        response = self.upload(note_id, self.image_bytes('HEIF'), 'photo.heic')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['filename'], 'photo.jpg')

    def test_request_limit_returns_json(self):
        note_id = self.note()
        self.app.config['MAX_CONTENT_LENGTH'] = 32
        response = self.upload(note_id, self.image_bytes())
        self.assertEqual(response.status_code, 413)
        self.assertIn('error', response.json)
        self.assertEqual(NoteImage.query.count(), 0)

    def test_neon_url_and_postgres_binary_schema(self):
        url = make_url(neon_database_url('postgresql://owner:password@ep-test.neon.tech/neondb?channel_binding=require'))
        self.assertEqual(url.drivername, 'postgresql+psycopg')
        self.assertEqual(url.query['sslmode'], 'require')
        self.assertEqual(url.query['channel_binding'], 'require')
        secure = make_url(neon_database_url('postgres://owner:password@host/db?sslmode=verify-full'))
        self.assertEqual(secure.query['sslmode'], 'verify-full')
        for invalid in ('', 'sqlite:///app.db', 'not a connection string', 'postgresql:///db'):
            with self.assertRaises(ValueError):
                neon_database_url(invalid)
        schema = str(CreateTable(NoteImage.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn('BYTEA', schema)

    def test_normal_app_requires_neon_configuration(self):
        with patch('src.app.load_dotenv'), patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'DATABASE_URL'):
                create_app()

    def test_sqlite_import_preserves_ids_and_source_and_refuses_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'old.db'
            with sqlite3.connect(source) as connection:
                connection.execute('CREATE TABLE note (id INTEGER PRIMARY KEY, title TEXT, content TEXT, created_at TEXT, updated_at TEXT)')
                connection.execute('INSERT INTO note VALUES (7, ?, ?, ?, ?)',
                                   ('原始笔记', 'Existing content', '2026-10-09 12:00:00', '2026-10-09 13:00:00'))
                connection.execute('CREATE TABLE user (id INTEGER PRIMARY KEY, username TEXT, email TEXT)')
                connection.execute("INSERT INTO user VALUES (3, 'old-user', 'user@example.com')")
            original = source.read_bytes()
            self.assertEqual(import_sqlite(source), (1, 1))
            imported = db.session.get(Note, 7)
            self.assertEqual(imported.title, '原始笔记')
            self.assertEqual(imported.updated_at.hour, 13)
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'empty target'):
                import_sqlite(source)
            self.assertEqual(Note.query.count(), 1)

    def test_failed_migration_rolls_back_all_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'invalid.db'
            with sqlite3.connect(source) as connection:
                connection.execute('CREATE TABLE note (id INTEGER PRIMARY KEY, title TEXT, content TEXT, created_at TEXT, updated_at TEXT)')
                connection.execute("INSERT INTO note VALUES (1, 'Valid', 'Body', NULL, NULL)")
                connection.execute("INSERT INTO note VALUES (2, 'Invalid', 'Body', 'invalid timestamp', NULL)")
            with self.assertRaises(ValueError):
                import_sqlite(source)
            self.assertEqual(Note.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
