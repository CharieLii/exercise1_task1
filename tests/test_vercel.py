import os
import unittest
from unittest.mock import patch

from src.app import create_app


class VercelConfigurationTests(unittest.TestCase):
    def test_cloud_upload_limit_and_public_configuration(self):
        with patch.dict(os.environ, {'VERCEL': '1'}):
            app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        self.assertEqual(app.config['MAX_IMAGE_BYTES'], 4 * 1024 * 1024)
        self.assertLess(app.config['MAX_CONTENT_LENGTH'], 4.5 * 1024 * 1024)
        response = app.test_client().get('/api/config')
        self.assertEqual(response.json, {'max_image_bytes': 4 * 1024 * 1024})
        self.assertTrue(app.static_folder.endswith('/public'))

    def test_local_upload_limit_is_unchanged(self):
        with patch.dict(os.environ, {'VERCEL': '0'}):
            app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        self.assertEqual(app.config['MAX_IMAGE_BYTES'], 5 * 1024 * 1024)
        self.assertTrue(app.static_folder.endswith('/src/static'))


if __name__ == '__main__':
    unittest.main()
