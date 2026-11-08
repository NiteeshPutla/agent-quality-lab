import asyncio
import json
import os
import signal
import uuid
from .store import Store, Conflict
from .engine import evaluate_case

async def process_one(store):
    owner=str(uuid.uuid4())
    job=store.claim(owner)
    if not job: return False
    rid=job['id']; stop=asyncio.Event()
    async def heartbeat():
        while not stop.is_set():
            await asyncio.sleep(10)
            if not store.renew(rid,owner):
                task.cancel()
                return
    async def execute():
        existing=store.get(rid,job['tenant'])['results']
        done={(r['case_id'],r['sample']) for r in existing}
        for case in job['snapshot']['cases']:
            for sample in range(job['spec']['repeats']):
                if (case['id'],sample) in done: continue
                if not store.renew(rid,owner): raise Conflict('lease_lost')
                result=await evaluate_case(case,job['snapshot']['documents'],job['spec'],sample)
                store.put(rid,owner,case['id'],sample,result)
        store.finish(rid,owner)
    task=asyncio.create_task(execute()); pulse=asyncio.create_task(heartbeat())
    try:
        await task
    except asyncio.CancelledError:
        pass # Lease recovery resumes interrupted jobs; cancellation fences writes.
    except Exception as exc:
        store.finish(rid,owner,type(exc).__name__)
        print(json.dumps({'event':'run_failed','run_id':rid,'error_type':type(exc).__name__}),flush=True)
    finally:
        stop.set(); pulse.cancel()
        await asyncio.gather(pulse,return_exceptions=True)
    return True

async def main():
    store=Store(os.environ.get('LAB_DB','var/lab.db'))
    stop=asyncio.Event()
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM): loop.add_signal_handler(sig,stop.set)
    while not stop.is_set():
        if not await process_one(store):
            try: await asyncio.wait_for(stop.wait(),timeout=1)
            except asyncio.TimeoutError: pass

if __name__=='__main__': asyncio.run(main())
