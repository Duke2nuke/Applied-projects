# LOCAL EDUCATIONAL LAB — own code only, never run against real systems
"""Local scanner for the lab project (LAB ONLY).

LOCAL EDUCATIONAL LAB — own code only, never run against real systems.
Reads ONLY the .py files in this project folder — no network, no external
systems, no other folders. It reports, per file, the first occurrence of
each of the 3 intentional flaw types in app.py:
  - SQL injection: a SELECT built with an f-string / string formatting.
  - Reflected XSS: user input returned in an f-string with no escape().
  - Plaintext password storage: an INSERT storing a password with no hash.

It deliberately skips itself (audit.py) and test_lab.py: those files
contain the pattern strings used to detect the flaws, which would
otherwise be false positives. Run:  python audit.py
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SKIP_FILES = {"audit.py", "test_lab.py"}

SQL_INJECTION = "SQL injection"
REFLECTED_XSS = "Reflected XSS"
PLAINTEXT_PASSWORD = "Plaintext password storage"


def _is_sqli(line):
    return "SELECT" in line and ("f\"" in line or "f'" in line) and "{" in line


def _is_xss(line):
    return (
        "return" in line
        and ("f\"" in line or "f'" in line)
        and "{" in line
        and "<" in line  # echoed into HTML, not a plain string return
        and "escape" not in line
    )


def _is_plaintext_password(line):
    return (
        "INSERT" in line
        and "password" in line.lower()
        and "hash" not in line.lower()
    )


DETECTORS = [
    (SQL_INJECTION, _is_sqli, "query built with string formatting, not parameters"),
    (REFLECTED_XSS, _is_xss, "user input echoed into a page with no HTML escaping"),
    (
        PLAINTEXT_PASSWORD,
        _is_plaintext_password,
        "password stored without hashing",
    ),
]


def scan_file(path):
    """Scan one local file; return at most one finding per flaw type."""
    path = Path(path)
    findings = []
    seen = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for flaw_type, detector, detail in DETECTORS:
            if flaw_type not in seen and detector(line):
                seen.add(flaw_type)
                findings.append(
                    {
                        "file": path.name,
                        "line": lineno,
                        "type": flaw_type,
                        "detail": detail,
                    }
                )
    return findings


def scan_project(directory=None):
    """Scan every .py file in this project folder only (except audit/test)."""
    directory = Path(directory) if directory else BASE_DIR
    findings = []
    for path in sorted(directory.glob("*.py")):
        if path.name in SKIP_FILES:
            continue
        findings.extend(scan_file(path))
    return findings


def main():
    findings = scan_project()
    for path in sorted(p for p in BASE_DIR.glob("*.py") if p.name not in SKIP_FILES):
        file_findings = [f for f in findings if f["file"] == path.name]
        print(f"{path.name}: {len(file_findings)} flaw(s)")
        for finding in file_findings:
            print(
                f"  line {finding['line']}: {finding['type']} — {finding['detail']}"
            )
    print(f"Total: {len(findings)} flaw(s) in this project folder only.")


if __name__ == "__main__":
    main()
