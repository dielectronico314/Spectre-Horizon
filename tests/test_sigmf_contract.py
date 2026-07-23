import unittest
import json
import os

class TestSigMFContract(unittest.TestCase):
    def test_schema_exists(self):
        schema_path = os.path.join(os.path.dirname(__file__), "..", "rf-spectrum", "schema", "sigmf_v0.1.schema.json")
        self.assertTrue(os.path.exists(schema_path), "JSON Schema file must exist")

    def test_schema_valid_json(self):
        schema_path = os.path.join(os.path.dirname(__file__), "..", "rf-spectrum", "schema", "sigmf_v0.1.schema.json")
        with open(schema_path, "r") as f:
            data = json.load(f)
        self.assertIn("required", data["properties"]["global"], "Schema must have required global fields")

if __name__ == '__main__':
    unittest.main()
