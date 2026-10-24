import unittest

from onboardops.sanitization import is_sensitive_key, redact_sensitive_fields


class SanitizationTests(unittest.TestCase):
    def test_recognises_common_secret_key_conventions(self):
        for key in (
            "password", "api_token", "accessToken", "apiKey", "clientSecret",
            "private_key", "credentials", "AuthorizationHeader", "bearer",
        ):
            with self.subTest(key=key):
                self.assertTrue(is_sensitive_key(key))

    def test_redacts_nested_objects_but_preserves_non_secret_fields(self):
        value = {
            "apiKey": "never-export",
            "nested": [{"clientSecret": "never-export-either", "department": "IT"}],
            "count": 3,
        }
        self.assertEqual(
            redact_sensitive_fields(value),
            {
                "apiKey": "[REDACTED]",
                "nested": [{"clientSecret": "[REDACTED]", "department": "IT"}],
                "count": 3,
            },
        )


if __name__ == "__main__":
    unittest.main()
