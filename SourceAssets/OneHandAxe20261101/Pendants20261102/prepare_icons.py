"""Promote the existing approved pendant category/empty icons to shared keys."""
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ICONS = P.parents[2] / 'Content/ColdSteelData/AttachmentIcons20260913'
jobs = []
for source, key in [
    ('ue_kukri_category_lanyard', 'category_lanyard'),
    ('ue_kukri_lanyard_no_lanyard', 'lanyard_false'),
]:
    target = ICONS / (key + '.png')
    # Existing shared artwork belongs to all hosts; do not replace it.
    if not target.exists():
        shutil.copy2(ICONS / (source + '.png'), target)
    jobs.append({'key': key, 'source': str(target), 'promoted_from': source})
(P / 'icon_deployments.json').write_text(json.dumps(jobs, indent=2) + '\n', encoding='utf-8')
print('PENDANT_SHARED_ICON_INPUTS_READY')
