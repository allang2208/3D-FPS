"""Create exhaustive ordered pair fixtures for the layout-only commandlet."""
import argparse
import itertools
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('catalog', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--seed-base', type=int, default=100000)
args = parser.parse_args()
catalog = json.loads(args.catalog.read_text(encoding='utf-8-sig'))
themes = sorted(t['id'] for t in catalog['themed_routes']['routes'])
if len(themes) != 6 or len(set(themes)) != 6:
    raise ValueError('Expected six distinct themes')
# Branch assignment is solved spatially. Within each pair, order is significant.
unique = {tuple(sorted((order[i], order[i+1]) for i in (0, 2, 4)))
          for order in itertools.permutations(themes)}
cases = [{'id': f'pairing_{i:03d}', 'seed': args.seed_base+i,
          'themes': list(sum(pairs, ()))} for i, pairs in enumerate(sorted(unique))]
assert len(cases) == 120
args.output.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Prepared {len(cases)} ordered pairings: {args.output}')
