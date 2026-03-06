import app
import unittest
from unittest.mock import MagicMock
import database

class RentAppTest(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = app.app.test_client()
        self.app.testing = True

        # Initialize DB with test data
        database.init_db()
        database.add_test_data()

    def test_unknown_user(self):
        # Send a message from an unknown number
        response = self.app.post('/whatsapp', data={
            'From': 'whatsapp:+9999999999',
            'Body': 'Hello'
        })
        self.assertIn(b"Sorry, I don't recognize the number", response.data)

    def test_known_user_greeting(self):
        # Send a message from the known test user (+1234567890)
        response = self.app.post('/whatsapp', data={
            'From': 'whatsapp:+1234567890',
            'Body': 'Hello'
        })
        # Expect personalized greeting
        self.assertIn(b"Test Tenant", response.data)
        self.assertIn(b"Apt 101", response.data)

    def test_rent_inquiry(self):
        response = self.app.post('/whatsapp', data={
            'From': 'whatsapp:+1234567890',
            'Body': 'What is my rent?'
        })
        self.assertIn(b"15000", response.data)

if __name__ == '__main__':
    unittest.main()
