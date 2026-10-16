from pathlib import Path
from datetime import datetime
import json
ROOT=Path(__file__).resolve().parent
def build(name):
    p=ROOT/name
    content=p.read_text('utf8',errors='replace') if p.exists() else ''
    return {'log':str(p),'status':'succeeded' if 'Result: Succeeded' in content else 'pending_or_failed'}
report={'updated_at':datetime.now().astimezone().isoformat(),
    'review':'source and catalog inspection only','recipes_reviewed':8,
    'coverage':['recipe selection','product image','effect parameters','material count and escrow',
        'resume without paying again','claim','half refund','full-inventory failure','duplicate request guards','async receipt and queued intent'],
    'changes':['current recipe readiness notice','snapshot cache bound to Job ID','shared resume eligibility',
        'queued start/resume intent bound to recipe and Job ID','discard confirmation bound to Job ID and revision',
        'post-settlement double-click guard','inventory-sync button gates and feedback'],
    'game':build('build-game-accepted.log'),'editor':build('build-editor.log'),
    'interactive_editor_started':False,'game_started':False,'tests_run':False,'runtime_acceptance':False}
(ROOT/'delivery.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps({k:report[k] for k in ('game','editor')},indent=2))
