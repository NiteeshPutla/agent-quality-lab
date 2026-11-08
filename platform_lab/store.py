"""Single-host durable queue. Atomic leases fence stale workers."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from .dataset import canonical, digest

class Conflict(Exception): pass
class QueueFull(Exception): pass

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.db() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
            INSERT OR IGNORE INTO schema_version VALUES(1);
            CREATE TABLE IF NOT EXISTS runs(
              id TEXT PRIMARY KEY, tenant TEXT NOT NULL, idem TEXT NOT NULL,
              request_hash TEXT NOT NULL, spec TEXT NOT NULL, snapshot TEXT NOT NULL,
              state TEXT NOT NULL, created REAL NOT NULL, owner TEXT,
              lease REAL, attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
              UNIQUE(tenant,idem));
            CREATE TABLE IF NOT EXISTS results(
              run_id TEXT NOT NULL REFERENCES runs(id), case_id TEXT NOT NULL,
              sample INTEGER NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(run_id,case_id,sample));
            CREATE INDEX IF NOT EXISTS queue_idx ON runs(state,created);
            """)
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path, timeout=10)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def submit(self, tenant, idem, spec, snapshot):
        fingerprint=digest(spec)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM runs WHERE tenant=? AND idem=?',(tenant,idem)).fetchone()
            if old:
                if old['request_hash'] != fingerprint: raise Conflict('Idempotency key reused with different request')
                return old['id']
            if c.execute("SELECT count(*) FROM runs WHERE state IN ('queued','running')").fetchone()[0]>=100:
                raise QueueFull()
            rid=str(uuid.uuid4())
            c.execute('INSERT INTO runs(id,tenant,idem,request_hash,spec,snapshot,state,created) VALUES(?,?,?,?,?,?,?,?)',
                      (rid,tenant,idem,fingerprint,canonical(spec),canonical(snapshot),'queued',time.time()))
            return rid

    def claim(self, owner, ttl=120):
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            now=time.time()
            c.execute("UPDATE runs SET state='failed',error='worker_retries_exhausted' WHERE state='running' AND lease<? AND attempts>=3",(now,))
            row=c.execute("SELECT * FROM runs WHERE state='queued' OR (state='running' AND lease<? AND attempts<3) ORDER BY created LIMIT 1",(now,)).fetchone()
            if not row: return None
            c.execute("UPDATE runs SET state='running',owner=?,lease=?,attempts=attempts+1 WHERE id=?",(owner,now+ttl,row['id']))
            return self._decode(dict(row))

    def renew(self, rid, owner, ttl=120):
        with self.db() as c:
            return c.execute("UPDATE runs SET lease=? WHERE id=? AND owner=? AND state='running' AND lease>?",(time.time()+ttl,rid,owner,time.time())).rowcount==1

    def put(self, rid, owner, case_id, sample, payload):
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            valid=c.execute("SELECT 1 FROM runs WHERE id=? AND owner=? AND state='running' AND lease>?",(rid,owner,time.time())).fetchone()
            if not valid: raise Conflict('Lease lost')
            c.execute('INSERT OR IGNORE INTO results VALUES(?,?,?,?)',(rid,case_id,sample,canonical(payload)))

    def finish(self,rid,owner,error=None):
        with self.db() as c:
            c.execute("UPDATE runs SET state=?,error=?,lease=NULL WHERE id=? AND owner=? AND state='running' AND lease>?",('failed' if error else 'completed',error,rid,owner,time.time()))

    def cancel(self,rid,tenant):
        with self.db() as c:
            c.execute("UPDATE runs SET state='cancelled',owner=NULL,lease=NULL WHERE id=? AND tenant=? AND state IN ('running','queued')",(rid,tenant))

    def _decode(self,row):
        for k in ('spec','snapshot'):
            row[k]=json.loads(row[k])
        return row

    def get(self,rid,tenant):
        with self.db() as c:
            row=c.execute('SELECT * FROM runs WHERE id=? AND tenant=?',(rid,tenant)).fetchone()
            if not row: return None
            result=self._decode(dict(row))
            result['results']=[json.loads(r[0]) for r in c.execute('SELECT payload FROM results WHERE run_id=? ORDER BY case_id,sample',(rid,))]
            return result

    def list(self,tenant):
        with self.db() as c:
            return [dict(r) for r in c.execute('SELECT id,state,created,error FROM runs WHERE tenant=? ORDER BY created DESC LIMIT 100',(tenant,))]
