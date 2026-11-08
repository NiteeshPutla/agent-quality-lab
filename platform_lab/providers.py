import asyncio
import json
import os
import random
import httpx

class ProviderFailure(Exception): pass

async def generate(provider, model, system, payload, client=None):
    """Bound the entire retry chain. Never retry authentication or schema failures."""
    if provider not in ('openai','anthropic'):
        raise ProviderFailure('unsupported_provider')
    key=os.environ.get('OPENAI_API_KEY' if provider=='openai' else 'ANTHROPIC_API_KEY')
    if not key: raise ProviderFailure('missing_provider_key')
    text=json.dumps(payload)
    if provider=='openai':
        url='https://api.openai.com/v1/responses'
        headers={'Authorization':'Bearer '+key}
        body={'model':model,'instructions':system,'input':text,'max_output_tokens':1200,'store':False}
    else:
        url='https://api.anthropic.com/v1/messages'
        headers={'x-api-key':key,'anthropic-version':'2023-06-01'}
        body={'model':model,'system':system,'messages':[{'role':'user','content':text}],'max_tokens':1200}
    async def request(http):
        for attempt in range(3):
            try:
                r=await http.post(url,headers=headers,json=body,timeout=20)
                if r.status_code==429 or r.status_code>=500:
                    if attempt==2: raise ProviderFailure('transient_retries_exhausted')
                    await asyncio.sleep(min(2, .25*2**attempt)+random.random()*.1)
                    continue
                if r.status_code>=400: raise ProviderFailure('provider_http_'+str(r.status_code))
                data=r.json()
                if provider=='openai':
                    if data.get('status')!='completed': raise ProviderFailure('incomplete_response')
                    output=''.join(part.get('text','') for item in data.get('output',[]) for part in item.get('content',[]) if part.get('type')=='output_text')
                else:
                    if data.get('stop_reason')!='end_turn': raise ProviderFailure('incomplete_response')
                    output=''.join(part.get('text','') for part in data.get('content',[]) if part.get('type')=='text')
                return output, {'usage':data.get('usage',{}),'model':data.get('model',model),'attempts':attempt+1}
            except httpx.RequestError:
                if attempt==2: raise ProviderFailure('transport_failure') from None
                await asyncio.sleep(.25*2**attempt)
        raise ProviderFailure('retry_exhausted')
    async def run():
        if client: return await request(client)
        async with httpx.AsyncClient(follow_redirects=False) as http: return await request(http)
    try:
        return await asyncio.wait_for(run(),timeout=60)
    except asyncio.TimeoutError:
        raise ProviderFailure('deadline_exceeded') from None
