#!/usr/bin/env python
"""Generate backend/.env with fresh random secrets (never overwrites an existing file)."""
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = root / ".env"
if target.exists():
    sys.exit(f"{target} already exists - refusing to overwrite.")

text = (root / ".env.example").read_text()
text = text.replace("SECRET_KEY=change-me", f"SECRET_KEY={secrets.token_urlsafe(64)}")
text = text.replace("AUTH_PEPPER=change-me-too", f"AUTH_PEPPER={secrets.token_urlsafe(64)}")
text = text.replace("DB_PASSWORD=change-me", f"DB_PASSWORD={secrets.token_urlsafe(18)}")
target.write_text(text)
target.chmod(0o600)
print(f"Wrote {target}. Set DB_PASSWORD to match your MySQL user (see README).")
