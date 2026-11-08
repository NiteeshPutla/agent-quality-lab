"""Explicit live experiment commands; requires a running API and worker."""
import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
import httpx
from .providers import generate

async def improve(url,token,provider,model):
    async with httpx.AsyncClient(base_url=url,headers={'Authorization':'Bearer '+token},timeout=30) as client:
        async def submit(prompt):
            r=await client.post('/v1/runs',headers={'Idempotency-Key':str(uuid.uuid4())},json={'provider':provider,'model':model,'prompt':prompt,'split':'dev'})
            r.raise_for_status(); rid=r.json()['id']; deadline=time.monotonic()+1800
            while time.monotonic()<deadline:
                r=await client.get('/v1/runs/'+rid);r.raise_for_status();run=r.json()
                if run['state']=='completed':return run
                if run['state'] in ('failed','cancelled'):raise RuntimeError('Evaluation did not complete: '+rid)
                await asyncio.sleep(2)
            raise TimeoutError('Run still pending: '+rid)
        baseline=await submit('Answer accurately and completely using the supplied sources.')
        # Only development failures enter the proposer. No held-out cases or labels.
        raw,usage=await generate(provider,model,
            'Suggest one improved instruction for a retrieval assistant. Preserve authorization, source-only answers and abstention. Return ONLY JSON with a prompt string of at most 4000 characters.',
            {'current_prompt':baseline['spec']['prompt'],'development_results':baseline['results']})
        prompt=json.loads(raw)['prompt']
        if not isinstance(prompt,str) or not 1<=len(prompt)<=4000:raise ValueError('Invalid proposed prompt')
        candidate=await submit(prompt)
        r=await client.post('/v1/comparisons',json={'baseline':baseline['id'],'candidate':candidate['id']});r.raise_for_status()
        report={'baseline':baseline['id'],'candidate':candidate['id'],'proposed_prompt':prompt,
                'proposer_usage':usage,'comparison':r.json(),'deployed':False,'candidate_budget':1}
        Path('var').mkdir(exist_ok=True)
        path=Path('var')/('improvement-'+candidate['id']+'.json')
        path.write_text(json.dumps(report,indent=2))
        print(str(path))

def calibrate(path):
    rows=[json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if not rows:raise ValueError('Empty calibration data')
    matrix=[[0,0],[0,0]]
    for row in rows:
        if type(row['human_pass']) is not bool or type(row['judge_pass']) is not bool:raise ValueError('Labels must be booleans')
        matrix[int(row['human_pass'])][int(row['judge_pass'])]+=1
    tn,fp=matrix[0];fn,tp=matrix[1]
    return {'n':len(rows),'confusion_matrix_human_rows_judge_columns':matrix,
            'agreement':(tn+tp)/len(rows),'false_pass_rate':fp/(tn+fp) if tn+fp else None,
            'false_fail_rate':fn/(fn+tp) if fn+tp else None,
            'note':'Requires independently adjudicated human labels; inspect category slices and uncertainty before gating.'}

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('calibrate');c.add_argument('jsonl')
    i=sub.add_parser('improve');i.add_argument('--provider',choices=['openai','anthropic'],required=True);i.add_argument('--model',required=True)
    args=p.parse_args()
    if args.command=='calibrate':print(json.dumps(calibrate(args.jsonl),indent=2))
    else:asyncio.run(improve('http://127.0.0.1:8765',os.environ['LAB_CLIENT_TOKEN'],args.provider,args.model))
if __name__=='__main__':main()
