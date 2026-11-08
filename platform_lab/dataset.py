import hashlib
import json
from pathlib import Path
from .models import Dataset

ROOT = Path(__file__).resolve().parent.parent

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def load_dataset():
    data = Dataset.model_validate_json((ROOT/'data/benchmark.json').read_text()).model_dump()
    ids = [c['id'] for c in data['cases']]
    doc_ids = [d['id'] for d in data['documents']]
    if len(ids) != len(set(ids)) or len(doc_ids) != len(set(doc_ids)):
        raise ValueError('Duplicate IDs')
    clusters = {}
    for c in data['cases']:
        if c['cluster'] in clusters and clusters[c['cluster']] != c['split']:
            raise ValueError('Cluster crosses dataset split')
        clusters[c['cluster']] = c['split']
        allowed = {d['id'] for d in data['documents'] if d['tenant']==c['tenant'] and c['principal'] in d['readers']}
        if not set(c['expected_sources']) <= allowed:
            raise ValueError('Expected source is inaccessible')
    return data
