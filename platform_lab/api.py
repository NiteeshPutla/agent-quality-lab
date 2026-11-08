import hashlib
import hmac
import json
import math
import os
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from .models import RunRequest, Comparison
from .dataset import load_dataset, digest, ROOT
from .store import Store, Conflict, QueueFull
from .comparison import compare

app=FastAPI(title='Agent Quality Lab',version='2.0.0')

def store(): return Store(os.environ.get('LAB_DB','var/lab.db'))

def identity(authorization: str = Header(default='')):
    keys=json.loads(os.environ.get('LAB_TOKENS','{}'))
    token=authorization.removeprefix('Bearer ')
    if not authorization.startswith('Bearer ') or not token: raise HTTPException(401,'Bearer token required')
    for expected,tenant in keys.items():
        if len(expected)>=24 and hmac.compare_digest(token,expected): return tenant
    raise HTTPException(401,'Invalid token')

@app.middleware('http')
async def trace(request: Request, call_next):
    start=time.monotonic(); rid=str(uuid.uuid4())
    response=await call_next(request)
    response.headers['X-Request-ID']=rid
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    print(json.dumps({'event':'http_request','request_id':rid,'method':request.method,
                      'status':response.status_code,'latency_ms':round((time.monotonic()-start)*1000,2)}),flush=True)
    return response

@app.get('/health/live')
def live(): return {'status':'ok'}

@app.get('/health/ready')
def ready():
    if not any(len(k)>=24 for k in json.loads(os.environ.get('LAB_TOKENS','{}'))):
        raise HTTPException(503,'Configure LAB_TOKENS')
    store()
    return {'status':'ready'}

@app.get('/',response_class=HTMLResponse)
def dashboard(): return (ROOT/'web/platform.html').read_text()

@app.get('/v1/runs')
def runs(tenant=Depends(identity)): return store().list(tenant)

@app.post('/v1/runs',status_code=202)
def submit(body:RunRequest, tenant=Depends(identity), idempotency_key: str = Header(min_length=1,max_length=100)):
    if body.provider!='offline' and os.environ.get('LAB_ALLOW_LIVE')!='1': raise HTTPException(403,'Live calls disabled')
    if body.judge_provider and (os.environ.get('LAB_ALLOW_LIVE')!='1' or not body.judge_model):
        raise HTTPException(422,'Live judging requires opt-in and judge_model')
    if body.provider=='offline' and body.model!='extractive-v1': raise HTTPException(422,'Offline model must be extractive-v1')
    data=load_dataset()
    snapshot={'version':data['version'],
              'cases':[c for c in data['cases'] if c['tenant']==tenant and c['split']==body.split],
              'documents':[d for d in data['documents'] if d['tenant']==tenant]}
    if not snapshot['cases']: raise HTTPException(422,'No cases for tenant and split')
    spec=body.model_dump()
    source_hash=hashlib.sha256(b''.join(f.read_bytes() for f in sorted((ROOT/'platform_lab').glob('*.py')))).hexdigest()
    spec.update(dataset_hash=digest(snapshot),scorer_version='2.0.0',code_sha256=source_hash,prompt_sha256=digest(body.prompt))
    try: rid=store().submit(tenant,idempotency_key,spec,snapshot)
    except Conflict as e: raise HTTPException(409,str(e))
    except QueueFull: raise HTTPException(429,'Queue full')
    return {'id':rid,'url':'/v1/runs/'+rid}

@app.get('/v1/runs/{rid}')
def run(rid:str,tenant=Depends(identity)):
    row=store().get(rid,tenant)
    if not row: raise HTTPException(404,'Run not found')
    results=row['results']
    latencies=sorted(r['latency_ms'] for r in results)
    row['summary']={
        'completed_samples':len(results),
        'mean_quality':sum(r['scores']['quality'] for r in results)/len(results) if results else None,
        'safety_failures':sum(r['scores']['safety']<1 for r in results),
        'p95_latency_ms':latencies[max(0,math.ceil(.95*len(latencies))-1)] if latencies else None,
        'input_tokens':sum(r['metadata']['usage'].get('input_tokens',0) for r in results),
        'output_tokens':sum(r['metadata']['usage'].get('output_tokens',0) for r in results),
        'cost_usd':None,
    }
    for key in ('snapshot','idem','request_hash','owner'): row.pop(key,None)
    return row

@app.post('/v1/runs/{rid}/cancel')
def cancel(rid:str,tenant=Depends(identity)):
    if not store().get(rid,tenant): raise HTTPException(404,'Run not found')
    store().cancel(rid,tenant)
    return {'id':rid,'state':store().get(rid,tenant)['state']}

@app.post('/v1/comparisons')
def comparison(body:Comparison,tenant=Depends(identity)):
    a=store().get(body.baseline,tenant); b=store().get(body.candidate,tenant)
    if not a or not b: raise HTTPException(404,'Run not found')
    try: return compare(a,b,body.margin)
    except ValueError as e: raise HTTPException(422,str(e))
