import unittest
from unittest.mock import patch
from datetime import timedelta, datetime, timezone

from jose import jwt, JWTError
from src import auth # Assuming src is in PYTHONPATH or tests are run in a way that src is discoverable
from src.config import settings # To access SECRET_KEY, ALGORITHM
from src.schemas import TokenData

class TestAuth(unittest.TestCase):

    def test_password_hashing(self):
        password = "testpassword123"
        hashed_password = auth.get_password_hash(password)
        self.assertNotEqual(password, hashed_password)
        self.assertTrue(auth.verify_password(password, hashed_password))
        self.assertFalse(auth.verify_password("wrongpassword", hashed_password))

    def test_create_access_token(self):
        data = {"sub": "testuser"}
        token = auth.create_access_token(data)

        # Decode without verification to check payload content
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_signature": False, "verify_exp": False})
        self.assertEqual(payload["sub"], "testuser")
        self.assertIn("exp", payload)

    def test_create_access_token_with_expires_delta(self):
        data = {"sub": "testuser_delta"}
        delta = timedelta(minutes=15)
        # Approximate expected expiry, allowing for small execution delay
        expected_exp_min = datetime.now(timezone.utc) + delta - timedelta(seconds=5)
        expected_exp_max = datetime.now(timezone.utc) + delta + timedelta(seconds=5)

        token = auth.create_access_token(data, expires_delta=delta)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]) # Verifies expiry too

        self.assertEqual(payload["sub"], "testuser_delta")
        self.assertIn("exp", payload)
        # token_exp_datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) # fromtimestamp is naive, needs tz
        token_exp_datetime = datetime.fromtimestamp(payload["exp"]).replace(tzinfo=timezone.utc)


        self.assertTrue(expected_exp_min <= token_exp_datetime <= expected_exp_max,
                        f"Expected expiry between {expected_exp_min} and {expected_exp_max}, but got {token_exp_datetime}")


    def test_verify_token_valid(self):
        username = "test_verify_user"
        token = auth.create_access_token({"sub": username})

        credentials_exception = Exception("Test credentials error") # Mock exception

        token_data = auth.verify_token(token, credentials_exception)
        self.assertIsInstance(token_data, TokenData)
        self.assertEqual(token_data.username, username)

    def test_verify_token_expired(self):
        username = "test_expired_user"
        # Create a token that expired 1 minute ago
        expired_delta = timedelta(minutes=-1)
        token = auth.create_access_token({"sub": username}, expires_delta=expired_delta)

        credentials_exception = JWTError("Token has expired") # More specific mock

        with self.assertRaises(JWTError): # Expecting JWTError due to expiration
            auth.verify_token(token, credentials_exception)

    def test_verify_token_invalid_signature(self):
        username = "test_invalid_sig_user"
        token_payload = {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
        # Sign with a wrong key
        invalid_token = jwt.encode(token_payload, "WRONG_SECRET_KEY", algorithm=settings.ALGORITHM)

        credentials_exception = JWTError("Invalid signature") # Mock

        with self.assertRaises(JWTError):
            auth.verify_token(invalid_token, credentials_exception)

    def test_verify_token_no_sub(self):
        # Token without 'sub' field
        token_payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
        no_sub_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # The actual exception type raised by verify_token for missing 'sub'
        # would be the credentials_exception instance passed to it.
        class MockCredentialsException(Exception):
            pass

        with self.assertRaises(MockCredentialsException):
            auth.verify_token(no_sub_token, MockCredentialsException("Username not found in token"))


if __name__ == '__main__':
    # This allows running the tests directly: python tests/unit/test_auth.py
    # For proper project testing, use `python -m unittest discover tests` from root
    unittest.main()
