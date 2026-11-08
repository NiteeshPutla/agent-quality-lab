import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from .core import ROOT, evaluate
from .statistics import compare

RUNS = ROOT / 'runs'

def save(name, run):
    RUNS.mkdir(exist_ok=True)
    path = RUNS / name
    path.write_text(json.dumps(run, indent=2)+'\n')
    return path

def serve(port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/api/runs':
                payload = json.dumps([{'name':p.name, 'run':json.loads(p.read_text())} for p in sorted(RUNS.glob('*.json'))]).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
            elif self.path == '/':
                payload = (ROOT/'web/index.html').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
            else:
                self.send_error(404)
                return
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    server = HTTPServer(('127.0.0.1',port), Handler)
    print('Dashboard: http://127.0.0.1:%s' % port, flush=True)
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser(description='Agent Quality Lab — offline learning environment')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    ev = sub.add_parser('eval')
    ev.add_argument('--prompt',choices=['baseline','candidate'],default='baseline')
    ev.add_argument('--split',choices=['dev','holdout'],default='dev')
    ev.add_argument('--route',choices=['auto','economy','strong','broken'],default='auto')
    ev.add_argument('--output',default='evaluation.json')
    cmp = sub.add_parser('compare')
    cmp.add_argument('baseline',type=Path)
    cmp.add_argument('candidate',type=Path)
    srv = sub.add_parser('serve')
    srv.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    prompts = json.loads((ROOT/'data/prompts.json').read_text())
    if args.command == 'serve':
        serve(args.port)
    elif args.command == 'compare':
        result = compare(json.loads(args.baseline.read_text()),json.loads(args.candidate.read_text()))
        print(json.dumps(result,indent=2))
        if result['status'] == 'regression':
            raise SystemExit(1)
    elif args.command == 'eval':
        if Path(args.output).name != args.output or not args.output.endswith('.json'):
            parser.error('--output must be a JSON filename, without directories')
        run = evaluate(prompts[args.prompt],args.split,args.route)
        print(save(args.output,run))
        print('Mean quality: %.3f (simulated)' % run['mean_quality'])
    else:
        # Bounded proposer: choose candidates using dev ONLY; no automatic deployment.
        baseline = evaluate(prompts['baseline'])
        candidate = evaluate(prompts['candidate'])
        comparison = compare(baseline,candidate)
        safe = all(r['scores']['safety'] == 1 for r in candidate['rows'])
        selected = 'candidate' if candidate['mean_quality'] > baseline['mean_quality'] and safe else 'baseline'
        save('baseline.json',baseline)
        save('candidate.json',candidate)
        save('holdout.json',evaluate(prompts[selected], 'holdout'))
        print(json.dumps({'dev_comparison':comparison,'selected_on_dev':selected,
                         'holdout':'runs/holdout.json','deployment':'manual review required'},indent=2))
