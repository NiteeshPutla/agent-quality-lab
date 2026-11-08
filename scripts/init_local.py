"""Create local configuration once; never overwrite existing credentials."""
import json
import secrets
from pathlib import Path
path=Path('.env')
if path.exists():
    raise SystemExit('.env already exists; leaving it unchanged.')
token=secrets.token_urlsafe(32)
with path.open('x') as file:
    file.write("LAB_TOKENS='"+json.dumps({token:'acme'})+"'\nLAB_DB=var/lab.db\nLAB_ALLOW_LIVE=0\n")
path.chmod(0o600)
print('Created .env. Copy its token into the dashboard when connecting.')
