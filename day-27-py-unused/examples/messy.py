"""Example file with several unused imports (for the README demo).

Run: python ../py_unused.py messy.py
Expected: 3 unused imports (sys, OrderedDict, requests).
"""

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

import requests  # left over from a refactor


def load_config(path):
    """Read a JSON config file and return the parsed dict."""
    text = Path(path).read_text()
    return json.loads(text)


def count_items(items):
    return Counter(items)


if __name__ == "__main__":
    print(count_items(["a", "b", "a"]))
