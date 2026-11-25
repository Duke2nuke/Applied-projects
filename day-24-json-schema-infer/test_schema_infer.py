"""Tests for schema_infer.py — run with: python -m unittest test_schema_infer -v"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_infer import infer_schema, infer_from_samples, validate  # noqa: E402


def infer(values, **kw):
    return infer_schema(values, **kw)


class TestScalars(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(infer([3]), {"$schema": infer([3])["$schema"],
                                      "type": "integer"})

    def test_mixed_int_float_is_number(self):
        self.assertEqual(infer_from_samples([3, 2.5])["type"], "number")

    def test_float_only_is_number(self):
        self.assertEqual(infer_from_samples([1.5, 2.5])["type"], "number")

    def test_string_bool_null(self):
        self.assertEqual(infer_from_samples(["a"])["type"], "string")
        self.assertEqual(infer_from_samples([True])["type"], "boolean")
        self.assertEqual(infer_from_samples([None])["type"], "null")

    def test_bool_is_not_integer(self):
        # In Python bool subclasses int; a boolean must stay boolean.
        self.assertEqual(infer_from_samples([True, False])["type"], "boolean")


class TestFormatsAndEnums(unittest.TestCase):
    def test_datetime_format_only_when_all_match(self):
        s = infer_from_samples(["2026-11-19T08:52:00Z", "2026-11-18T10:00:00Z"])
        self.assertEqual(s.get("format"), "date-time")
        mixed = infer_from_samples(["2026-11-19T08:52:00Z", "yesterday"])
        self.assertNotIn("format", mixed)

    def test_email_format(self):
        s = infer_from_samples(["a@b.com", "c@d.org"])
        self.assertEqual(s.get("format"), "email")

    def test_enum_small_closed_set(self):
        s = infer_from_samples(["active", "paused", "active", "archived"])
        self.assertEqual(s.get("enum"), ["active", "archived", "paused"])

    def test_no_enum_for_many_distinct_values(self):
        vals = ["v%d" % i for i in range(6)]
        self.assertNotIn("enum", infer_from_samples(vals))

    def test_no_enum_for_too_few_samples(self):
        self.assertNotIn("enum", infer_from_samples(["a", "b"]))


class TestObjectsAndArrays(unittest.TestCase):
    def test_required_is_intersection(self):
        s = infer_from_samples([{"a": 1, "b": 2}, {"a": 3}])
        self.assertEqual(s["required"], ["a"])
        self.assertEqual(sorted(s["properties"]), ["a", "b"])

    def test_nested_object(self):
        s = infer_from_samples([{"addr": {"city": "Delhi", "pin": 110001}}])
        self.assertEqual(s["properties"]["addr"]["properties"]["pin"]["type"],
                         "integer")

    def test_array_items_merged(self):
        s = infer_from_samples([[{"a": 1}, {"a": 2, "b": "x"}]])
        items = s["items"]
        self.assertEqual(items["required"], ["a"])
        self.assertEqual(items["properties"]["b"]["type"], "string")

    def test_mixed_type_field_is_anyof(self):
        s = infer_from_samples([{"v": 1}, {"v": "one"}, {"v": 2}])
        types = sorted(p["type"] for p in s["properties"]["v"]["anyOf"])
        self.assertEqual(types, ["integer", "string"])

    def test_strict_adds_additional_properties_false(self):
        s = infer([{"a": {"b": 1}}], strict=True)
        self.assertIs(s["additionalProperties"], False)
        self.assertIs(s["properties"]["a"]["additionalProperties"], False)


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.schema = infer([{"id": 1, "name": "x", "tags": ["a"]},
                             {"id": 2, "name": "y"}])

    def test_valid_data(self):
        self.assertEqual(validate({"id": 3, "name": "z"}, self.schema), [])

    def test_missing_required(self):
        errs = validate({"name": "z"}, self.schema)
        self.assertTrue(any("missing required" in e and "'id'" in e for e in errs))

    def test_wrong_type(self):
        errs = validate({"id": "3", "name": "z"}, self.schema)
        self.assertTrue(any("expected integer" in e for e in errs))

    def test_wrong_array_item_type(self):
        errs = validate({"id": 1, "name": "z", "tags": [5]}, self.schema)
        self.assertTrue(any("expected string" in e for e in errs))

    def test_anyof_accepts_either(self):
        schema = infer_from_samples([{"v": 1}, {"v": "one"}])
        self.assertEqual(validate({"v": 1}, schema), [])
        self.assertEqual(validate({"v": "x"}, schema), [])
        self.assertTrue(validate({"v": 1.5}, schema))


class TestCLI(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        here = os.path.dirname(os.path.abspath(__file__))
        return subprocess.run([sys.executable, "schema_infer.py", *args],
                              cwd=here, input=stdin, text=True,
                              capture_output=True)

    def test_infer_to_stdout(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as fh:
            json.dump({"a": 1}, fh)
            path = fh.name
        try:
            r = self.run_cli("infer", path)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["properties"]["a"]["type"],
                             "integer")
        finally:
            os.unlink(path)

    def test_infer_jsonl_and_stdin(self):
        r = self.run_cli("infer", "--jsonl", "-",
                         stdin='{"a": 1}\n{"a": 2, "b": "x"}\n')
        self.assertEqual(r.returncode, 0)
        schema = json.loads(r.stdout)
        self.assertEqual(schema["required"], ["a"])
        self.assertEqual(schema["properties"]["b"]["type"], "string")

    def test_validate_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            schema_p = os.path.join(d, "s.json")
            data_p = os.path.join(d, "d.json")
            with open(schema_p, "w") as fh:
                json.dump(infer([{"id": 1}]), fh)
            with open(data_p, "w") as fh:
                json.dump({"id": 2}, fh)
            self.assertEqual(self.run_cli("validate", schema_p, data_p)
                             .returncode, 0)
            with open(data_p, "w") as fh:
                json.dump({"id": "two"}, fh)
            bad = self.run_cli("validate", schema_p, data_p)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("expected integer", bad.stdout)


if __name__ == "__main__":
    unittest.main()
