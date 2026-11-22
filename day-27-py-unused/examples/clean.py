"""Example file with no unused imports (for the README demo).

Run: python ../py_unused.py clean.py
Expected: exit 0, "no unused imports".
"""

import json
from pathlib import Path


def load_config(path):
    """Read a JSON config file and return the parsed dict."""
    return json.loads(Path(path).read_text())


if __name__ == "__main__":
    print(load_config("config.json"))
