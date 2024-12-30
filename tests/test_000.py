# tests/test000.py
import unittest
from tlaloc_api_builder.builder import api_builder

class TestBuildApi(unittest.TestCase):
    def test_build_api(self):
        config = {"name": "MyAPI", "version": "1.0"}
        result = api_builder(config)
        
        # Check if the result is a dictionary
        self.assertIsInstance(result, dict)
        
        # Check if the expected keys exist in the result
        self.assertIn("status", result)
        self.assertIn("config", result)
        
        # Check the values of the result
        self.assertEqual(result["status"], "API built")
        self.assertEqual(result["config"], config)

if __name__ == "__main__":
    unittest.main()
