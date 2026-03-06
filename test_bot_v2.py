import app
import unittest
import database

class RentAppTestV2(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = app.app.test_client()
        self.app.testing = True

        # Initialize DB with test data
        database.init_db()
        database.add_test_data()

    def test_help_command(self):
        # Test the 'help' keyword
        response = self.app.post('/whatsapp', data={
            'From': 'whatsapp:+1234567890',
            'Body': 'help'
        })
        self.assertIn(b"Commands:", response.data)
        self.assertIn(b"rent", response.data)
        self.assertIn(b"screenshot", response.data)

    def test_image_upload(self):
        # Test image upload acknowledgement
        response = self.app.post('/whatsapp', data={
            'From': 'whatsapp:+1234567890',
            'Body': '',
            'NumMedia': '1'  # Simulate 1 image attached
        })
        self.assertIn(b"payment screenshot", response.data)
        self.assertIn(b"Pending manager approval", response.data)

if __name__ == '__main__':
    unittest.main()
