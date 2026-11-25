#!/usr/bin/env python3
"""json-schema-infer: infer a JSON Schema (draft 2020-12) from sample JSON.

Usage:
    python schema_infer.py infer sample.json [more.json ...] [-o schema.json]
    python schema_infer.py infer --jsonl samples.jsonl [-o schema.json]
    cat sample.json | python schema_infer.py infer -
    python schema_infer.py validate schema.json data.json

The inferred schema is a *description of the samples it was shown*, not a
contract the data promised to keep. String formats (email, date-time, uri)
and enums are heuristics: they are only added when every sample agrees.
Standard library only.
"""

import argparse
import json
import re
import sys

SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)
URI_RE = re.compile(r"^https?://\S+$")

MAX_ENUM_VALUES = 5
MIN_SAMPLES_FOR_ENUM = 3


def _category(value):
    """JSON type category of a Python value decoded from JSON."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise TypeError("unsupported JSON value: %r" % (value,))


def _string_format(values):
    """A format name if every string matches the same pattern, else None."""
    if all(DATETIME_RE.match(v) for v in values):
        return "date-time"
    if all(DATE_RE.match(v) for v in values):
        return "date"
    if all(EMAIL_RE.match(v) for v in values):
        return "email"
    if all(URI_RE.match(v) for v in values):
        return "uri"
    return None


def infer_from_samples(values, allow_enum=True):
    """Infer one schema describing every value in ``values``."""
    if not values:
        return {}
    by_cat = {}
    for v in values:
        by_cat.setdefault(_category(v), []).append(v)

    # Integers and floats are one numeric family: a field that is
    # sometimes 92 and sometimes 87.5 is a "number", not an anyOf.
    if set(by_cat) == {"integer", "number"}:
        return _schema_for_category("number", by_cat["integer"] + by_cat["number"],
                                    allow_enum)

    if len(by_cat) == 1:
        cat, group = next(iter(by_cat.items()))
        return _schema_for_category(cat, group, allow_enum)

    # Mixed types: one schema per category, combined with anyOf.
    parts = [
        _schema_for_category(cat, group, allow_enum)
        for cat, group in sorted(by_cat.items())
    ]
    return {"anyOf": parts}


def _schema_for_category(cat, group, allow_enum):
    if cat in ("null", "boolean"):
        schema = {"type": cat}
    elif cat in ("integer", "number"):
        schema = {"type": "integer" if cat == "integer" else "number"}
    elif cat == "string":
        schema = {"type": "string"}
        fmt = _string_format(group)
        if fmt:
            schema["format"] = fmt
    elif cat == "array":
        schema = {"type": "array"}
        items = [item for arr in group for item in arr]
        if items:
            schema["items"] = infer_from_samples(items, allow_enum)
    elif cat == "object":
        schema = {"type": "object"}
        keys = set()
        for obj in group:
            keys.update(obj.keys())
        properties = {}
        required = []
        for key in sorted(keys):
            present = [obj[key] for obj in group if key in obj]
            properties[key] = infer_from_samples(present, allow_enum)
            if len(present) == len(group):
                required.append(key)
        schema["properties"] = properties
        if required:
            schema["required"] = sorted(required)
    else:  # pragma: no cover - _category guards this
        raise AssertionError(cat)

    # Enum heuristic: a small closed set of scalar values seen often enough.
    if allow_enum and cat in ("string", "integer", "number", "boolean"):
        distinct = sorted(set(group), key=repr)
        if 2 <= len(distinct) <= MAX_ENUM_VALUES and len(group) >= MIN_SAMPLES_FOR_ENUM:
            schema["enum"] = distinct
    return schema


def infer_schema(values, allow_enum=True, strict=False):
    """Infer a full draft 2020-12 schema document from sample values."""
    schema = infer_from_samples(values, allow_enum)
    schema = {"$schema": SCHEMA_DRAFT, **schema}
    if strict:
        _apply_strict(schema)
    return schema


def _apply_strict(schema):
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
    for sub in schema.get("properties", {}).values():
        _apply_strict(sub)
    items = schema.get("items")
    if isinstance(items, dict):
        _apply_strict(items)
    for sub in schema.get("anyOf", []):
        _apply_strict(sub)


def load_samples(paths, jsonl=False):
    """Load sample JSON values from files, or stdin for path '-'."""
    values = []
    for path in paths:
        if path == "-":
            text = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        if jsonl:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    values.append(json.loads(line))
        else:
            values.append(json.loads(text))
    return values


def validate(data, schema, path="$"):
    """Validate ``data`` against an inferred-schema subset.

    Checks type, enum, required, properties, additionalProperties,
    items and anyOf. ``format`` is annotation-only and is not enforced.
    Returns a list of human-readable error strings (empty = valid).
    """
    errors = []
    if "anyOf" in schema:
        if any(not validate(data, sub, path) for sub in schema["anyOf"]):
            return []
        return ["%s: does not match any of the allowed types" % path]

    expected = schema.get("type")
    if expected is not None:
        actual = _category(data)
        if expected == "number" and actual == "integer":
            actual = "number"  # integers are valid numbers
        if actual != expected:
            return ["%s: expected %s, got %s" % (path, expected, actual)]

    if "enum" in schema and data not in schema["enum"]:
        errors.append("%s: %r is not one of %r" % (path, data, schema["enum"]))

    if expected == "object" and isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append("%s: missing required property %r" % (path, key))
        props = schema.get("properties", {})
        for key, value in data.items():
            if key in props:
                errors.extend(validate(value, props[key], "%s.%s" % (path, key)))
            elif schema.get("additionalProperties") is False:
                errors.append("%s: unexpected property %r" % (path, key))

    if expected == "array" and isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            errors.extend(validate(item, schema["items"], "%s[%d]" % (path, i)))

    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Infer a JSON Schema from sample JSON, or validate "
        "data against a schema."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_infer = sub.add_parser("infer", help="infer a schema from sample files")
    p_infer.add_argument("files", nargs="+", help="sample JSON files ('-' = stdin)")
    p_infer.add_argument("--jsonl", action="store_true",
                         help="each line of each file is one sample")
    p_infer.add_argument("-o", "--output", help="write schema to this file")
    p_infer.add_argument("--no-enum", action="store_true",
                         help="do not add enum for small closed value sets")
    p_infer.add_argument("--strict", action="store_true",
                         help="add additionalProperties: false to objects")

    p_val = sub.add_parser("validate", help="validate data against a schema")
    p_val.add_argument("schema", help="schema JSON file")
    p_val.add_argument("data", help="data JSON file to check")

    args = parser.parse_args(argv)

    if args.command == "infer":
        try:
            values = load_samples(args.files, jsonl=args.jsonl)
        except (OSError, json.JSONDecodeError) as exc:
            print("schema-infer: cannot load samples: %s" % exc, file=sys.stderr)
            return 2
        schema = infer_schema(values, allow_enum=not args.no_enum,
                              strict=args.strict)
        text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("wrote %s (%d sample%s)" % (
                args.output, len(values), "s" if len(values) != 1 else ""))
        else:
            sys.stdout.write(text)
        return 0

    if args.command == "validate":
        try:
            with open(args.schema, encoding="utf-8") as fh:
                schema = json.load(fh)
            with open(args.data, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print("schema-infer: cannot load files: %s" % exc, file=sys.stderr)
            return 2
        errors = validate(data, schema)
        if not errors:
            print("valid")
            return 0
        print("invalid (%d error%s):" % (len(errors), "s" if len(errors) != 1 else ""))
        for err in errors:
            print("  - %s" % err)
        return 1

    return 2  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
