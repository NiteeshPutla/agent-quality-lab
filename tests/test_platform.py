import asyncio
import copy
import json
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from fastapi.testclient import TestClient
from platform_lab.api import app
from platform_lab.store import Store, Conflict
from platform_lab.models import RunRequest
from platform_lab.dataset import load_dataset
from platform_lab.engine import retrieve, evaluate_case
from platform_lab.worker import process_one
from platform_lab.providers import generate, ProviderFailure
from platform_lab.comparison import compare

TOKEN='a'*32
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('LAB_DB',str(tmp_path/'test.db'))
    monkeypatch.setenv('LAB_TOKENS',json.dumps({TOKEN:'acme','b'*32:'other'}))
    monkeypatch.delenv('LAB_ALLOW_LIVE',raising=False)
    with TestClient(app) as c: yield c

def auth(token=TOKEN): return {'Authorization':'Bearer '+token}
def submit(client,key='request-1',**kwargs):
    return client.post('/v1/runs',headers=dict(auth(),**{'Idempotency-Key':key}),json=kwargs)

def test_auth_and_tenant_isolation(client):
    assert client.get('/v1/runs').status_code==401
    rid=submit(client).json()['id']
    assert client.get('/v1/runs/'+rid,headers=auth('b'*32)).status_code==404
    assert client.get('/v1/runs',headers=auth('b'*32)).json()==[]

def test_idempotency_conflict(client):
    first=submit(client)
    assert first.status_code==202
    assert submit(client).json()['id']==first.json()['id']
    assert submit(client,prompt='Changed prompt').status_code==409

def test_live_opt_in_and_validation(client):
    assert submit(client,provider='openai',model='configured-model').status_code==403
    assert submit(client,repeats=100).status_code==422
    assert submit(client,tenant='other').status_code==422

def test_worker_end_to_end(client,monkeypatch):
    import os
    rid=submit(client).json()['id']
    s=Store(os.environ['LAB_DB'])
    assert asyncio.run(process_one(s))
    result=client.get('/v1/runs/'+rid,headers=auth()).json()
    assert result['state']=='completed'
    assert len(result['results'])==8
    assert 'snapshot' not in result
    assert all('answer' not in r for r in result['results'])
    comparison=client.post('/v1/comparisons',headers=auth(),json={'baseline':rid,'candidate':rid})
    assert comparison.json()['status']=='insufficient_data'

def test_cancel_fences_worker(client):
    import os
    rid=submit(client).json()['id']; s=Store(os.environ['LAB_DB'])
    s.claim('first')
    assert client.post('/v1/runs/'+rid+'/cancel',headers=auth()).status_code==200
    with pytest.raises(Conflict): s.put(rid,'first','case',0,{})
    s.finish(rid,'first')
    assert s.get(rid,'acme')['state']=='cancelled'

def test_concurrent_claim_and_lease_recovery(tmp_path):
    s=Store(tmp_path/'db')
    rid=s.submit('acme','key',{}, {})
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims=list(pool.map(lambda n:s.claim(str(n)),range(4)))
    assert sum(x is not None for x in claims)==1
    with s.db() as db: db.execute('UPDATE runs SET lease=0 WHERE id=?',(rid,))
    assert s.claim('replacement')['id']==rid
    with pytest.raises(Conflict): s.put(rid,'stale','case',0,{})
    s.put(rid,'replacement','case',0,{'value':1})
    s.put(rid,'replacement','case',0,{'value':2})
    assert s.get(rid,'acme')['results']==[{'value':1}]

def test_permissions_before_retrieval():
    data=load_dataset()
    case=next(c for c in data['cases'] if c['category']=='access-control')
    assert retrieve(case,data['documents'])==[]
    case=dict(case,query='Atlas private budget')
    assert all(d['tenant']=='acme' for d in retrieve(case,data['documents']))

def test_labels_are_not_agent_inputs():
    data=load_dataset(); case=data['cases'][0]; spec=RunRequest().model_dump()
    changed=dict(case,required=['wrong'],expected_sources=[],category='other')
    a=asyncio.run(evaluate_case(case,data['documents'],spec,0))
    b=asyncio.run(evaluate_case(changed,data['documents'],spec,0))
    assert a['answer_sha256']==b['answer_sha256']

@pytest.mark.parametrize('provider',['openai','anthropic'])
def test_provider_request_and_usage(provider,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only');monkeypatch.setenv('ANTHROPIC_API_KEY','test-only')
    def handler(request):
        body=json.loads(request.content)
        assert body['model']=='test-model'
        if provider=='openai':
            assert body['store'] is False
            response={'status':'completed','model':'test-model','output':[{'content':[{'type':'output_text','text':'{}'}]}],'usage':{'input_tokens':10,'output_tokens':3}}
        else:
            response={'stop_reason':'end_turn','content':[{'type':'text','text':'{}'}],'usage':{'input_tokens':10,'output_tokens':3}}
        return httpx.Response(200,json=response)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await generate(provider,'test-model','system',{},c)
    text,metadata=asyncio.run(run())
    assert text=='{}' and metadata['usage']['input_tokens']==10

def test_provider_retry_and_auth_no_retry(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(429 if len(calls)<3 else 401,json={})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            await generate('openai','test','system',{},c)
    with pytest.raises(ProviderFailure,match='401'):asyncio.run(run())
    assert len(calls)==3

def test_invalid_model_json_fails_run(client,monkeypatch):
    import os
    monkeypatch.setenv('LAB_ALLOW_LIVE','1')
    async def invalid(*args,**kwargs):return 'not json',{}
    monkeypatch.setattr('platform_lab.engine.generate',invalid)
    rid=submit(client,provider='openai',model='test').json()['id']
    s=Store(os.environ['LAB_DB']);asyncio.run(process_one(s))
    assert s.get(rid,'acme')['state']=='failed'

def synthetic_run(value):
    return {'state':'completed','spec':{'provider':'offline'},'results':[
      {'case_id':str(i),'sample':0,'cluster':str(i),'scores':{'quality':value,'safety':1}} for i in range(30)]}

def test_statistical_gate_and_safety_override():
    a=synthetic_run(1);b=synthetic_run(0)
    assert compare(a,b)['status']=='regression'
    assert compare(b,a)['promotion_allowed']
    assert compare(a,a)['status']=='inconclusive'
    b=copy.deepcopy(a);b['results'][0]['scores']['safety']=0
    assert compare(a,b)['status']=='safety_regression'

def test_comparison_rejects_missing_samples_and_mixed_modes():
    a=synthetic_run(1); b=synthetic_run(1);b['results'].pop()
    with pytest.raises(ValueError):compare(a,b)
    b=synthetic_run(1);b['spec']['provider']='openai'
    with pytest.raises(ValueError):compare(a,b)


def test_calibration_false_passes(tmp_path):
    from platform_lab.experiments import calibrate
    path=tmp_path/'labels.jsonl'
    path.write_text('\n'.join(json.dumps(x) for x in [
        {'human_pass':False,'judge_pass':True},
        {'human_pass':True,'judge_pass':True},
        {'human_pass':False,'judge_pass':False}]))
    result=calibrate(path)
    assert result['false_pass_rate']==.5
    assert result['false_fail_rate']==0
    path.write_text('')
    with pytest.raises(ValueError):calibrate(path)

def test_improvement_uses_only_development_and_records_lineage(tmp_path,monkeypatch):
    from platform_lab import experiments
    monkeypatch.chdir(tmp_path)
    submissions=[]
    original=httpx.AsyncClient
    def handler(request):
        if request.url.path=='/v1/runs':
            submissions.append(json.loads(request.content))
            return httpx.Response(202,json={'id':str(len(submissions))})
        if request.url.path.startswith('/v1/runs/'):
            return httpx.Response(200,json={'id':request.url.path.split('/')[-1],'state':'completed','spec':{'prompt':'initial'},'results':[]})
        return httpx.Response(200,json={'status':'insufficient_data','promotion_allowed':False})
    monkeypatch.setattr(experiments.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    async def proposer(*args):return '{"prompt":"Use authorized sources; abstain when missing."}',{'usage':{}}
    monkeypatch.setattr(experiments,'generate',proposer)
    asyncio.run(experiments.improve('http://test','token','openai','test'))
    assert len(submissions)==2
    assert all(s['split']=='dev' for s in submissions)
    artifact=json.loads(next((tmp_path/'var').glob('improvement-*.json')).read_text())
    assert artifact['deployed'] is False
    assert artifact['baseline']=='1' and artifact['candidate']=='2'
