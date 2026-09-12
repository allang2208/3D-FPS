"""Compare reports from separate engine runs; no duplicate generator implementation."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('first',type=Path)
p.add_argument('continued',type=Path)
p.add_argument('different_seed',type=Path)
p.add_argument('--output',type=Path)
args=p.parse_args()
a,b,c=[json.loads(path.read_text(encoding='utf-8-sig')) for path in (args.first,args.continued,args.different_seed)]
layers=['treeHash','rockHash','shrubHash','grassHash']
checks={
    'continue_preserves_seed':a['seed']==b['seed'],
    'continue_preserves_every_layer':all(a[k]==b[k] for k in layers),
    'continue_preserves_terrain':all(a[k]==b[k] for k in ('heightMinM','heightMaxM')),
    'different_seed_changes_every_layer':a['seed']!=c['seed'] and all(a[k]!=c[k] for k in layers),
    'different_seed_changes_terrain':any(a[k]!=c[k] for k in ('heightMinM','heightMaxM')),
    'all_runs_have_hills':all(v['heightMaxM']-v['heightMinM']>18 for v in (a,b,c)),
    'all_runs_match_collision':all(v['traceMaxErrorCm']<15 for v in (a,b,c)),
}
result={'passed':all(checks.values()),'checks':checks,'inputs':[str(v) for v in (args.first,args.continued,args.different_seed)]}
text=json.dumps(result,indent=2)
print(text)
if args.output:args.output.write_text(text,encoding='utf-8')
raise SystemExit(0 if result['passed'] else 1)
