"""Skill reorganisation, step 4: verify routing still resolves.

The point of the reorganisation was NOT to shrink files -- it was to keep the right experience
reachable at the right time. Token counts cannot show that; unresolved pointers can.

This checks every relative markdown link in every SKILL.md and references/*.md, twice: against the
pre-change snapshot (Saved/SkillReorg20260923/skills-before) and against the current tree. If the
reorganisation broke routing, broken links would appear that the snapshot did not have.

It is a mechanical proxy for the cold-start canary check, not a substitute for it.

Run: py -3.11 SourceAssets/SkillReorg20260923/verify_links.py
"""
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'Saved' / 'SkillReorg20260923' / 'skills-before'
CURRENT = ROOT / 'skills'
HERE = Path(__file__).parent

LINK = re.compile(r'\]\(([^)]+)\)')


def check(base):
    broken, total = [], 0
    for path in sorted(base.rglob('*.md')):
        text = path.read_text(encoding='utf-8', errors='replace')
        for raw in LINK.findall(text):
            target = raw.split('#')[0].strip()
            if not target or target.startswith(('http://', 'https://', 'mailto:')):
                continue
            total += 1
            resolved = (path.parent / urllib.parse.unquote(target)).resolve()
            if not resolved.exists():
                broken.append(dict(file=str(path.relative_to(base)).replace('\\', '/'),
                                   target=target))
    return dict(total=total, broken=broken)


report = dict(snapshot=check(SNAPSHOT), current=check(CURRENT))
snap_broken = {(b['file'], b['target']) for b in report['snapshot']['broken']}
curr_broken = {(b['file'], b['target']) for b in report['current']['broken']}
report['newly_broken'] = sorted(curr_broken - snap_broken)
report['fixed'] = sorted(snap_broken - curr_broken)

(HERE / 'verify_links.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                        encoding='utf-8')
print('links: snapshot %d (%d broken) -> current %d (%d broken)'
      % (report['snapshot']['total'], len(snap_broken),
         report['current']['total'], len(curr_broken)))
print('NEWLY BROKEN: %d' % len(report['newly_broken']))
for f, t in report['newly_broken']:
    print('  %s -> %s' % (f, t))
print('fixed (were broken before): %d' % len(report['fixed']))
if report['snapshot']['broken']:
    print('pre-existing broken links in snapshot: %d' % len(report['snapshot']['broken']))
    for b in report['snapshot']['broken'][:10]:
        print('  (pre-existing) %s -> %s' % (b['file'], b['target']))
