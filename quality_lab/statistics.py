"""Paired bootstrap: cases, not repeated model samples, are resampled."""
import random

def compare(baseline, candidate, margin=0.05, samples=3000):
    if baseline['dataset_sha256'] != candidate['dataset_sha256'] or baseline['split'] != candidate['split']:
        raise ValueError('Runs must use the same dataset version and split')
    a = {r['id']: r['scores']['quality'] for r in baseline['rows']}
    b = {r['id']: r['scores']['quality'] for r in candidate['rows']}
    if not a or a.keys() != b.keys():
        raise ValueError('Runs must contain identical, nonempty case sets')
    diffs = [b[k]-a[k] for k in sorted(a)]
    rng = random.Random(42)
    boot = sorted(sum(rng.choice(diffs) for _ in diffs)/len(diffs) for _ in range(samples))
    low, high = boot[int(samples*.025)], boot[min(samples-1,int(samples*.975))]
    status = 'regression' if high < -margin else 'improvement' if low > margin else 'inconclusive'
    return {'mean_delta': sum(diffs)/len(diffs), 'ci95': [low,high], 'status': status,
            'cases':len(diffs), 'margin':margin, 'warning':'Small synthetic samples support learning, not deployment decisions.'}
