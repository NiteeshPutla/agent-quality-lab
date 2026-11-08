import random
from collections import defaultdict
from statistics import mean

def compare(a,b,margin=.05):
    if a['state']!='completed' or b['state']!='completed': raise ValueError('Both runs must be completed')
    for key in ('dataset_hash','split','repeats','scorer_version','judge_provider','judge_model'):
        if a['spec'].get(key)!=b['spec'].get(key): raise ValueError('Incomparable '+key)
    if (a['spec']['provider']=='offline') != (b['spec']['provider']=='offline'): raise ValueError('Cannot compare offline and live runs')
    aa={(r['case_id'],r['sample']):r for r in a['results']}
    bb={(r['case_id'],r['sample']):r for r in b['results']}
    if not aa or aa.keys()!=bb.keys(): raise ValueError('Unmatched results')
    metric='semantic_quality' if a['spec'].get('judge_provider') else 'quality'
    clusters=defaultdict(list)
    safety_regressions=[]
    for key,r in aa.items():
        other=bb[key]
        clusters[r['cluster']].append(other['scores'][metric]-r['scores'][metric])
        if other['scores']['safety']<r['scores']['safety']: safety_regressions.append(key[0])
    values=[mean(v) for v in clusters.values()]
    rng=random.Random(42)
    boot=sorted(mean(rng.choices(values,k=len(values))) for _ in range(5000))
    low,high=boot[125],boot[4874]
    status='insufficient_data' if len(values)<20 else 'regression' if high < -margin else 'improvement' if low>margin else 'inconclusive'
    if safety_regressions: status='safety_regression'
    return {'status':status,'metric':metric,'mean_delta':mean(values),'ci95':[low,high],
            'independent_clusters':len(values),'safety_regressions':sorted(set(safety_regressions)),
            'promotion_allowed':status=='improvement','margin':margin,
            'method':'paired cluster bootstrap; equal cluster weight; 5000 resamples; seed 42'}
