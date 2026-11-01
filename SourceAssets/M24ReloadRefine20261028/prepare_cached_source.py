"""Prepare the last saved authoring snapshot while the UE batch is queued."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent
src=O.parent/'M24ThumbAnatomy20261028'
data=json.loads((src/'ue_before.json').read_text())
for family in ('base','mag10'):
 data['profiles'][family]=json.loads((src/(family+'_profile.json')).read_text())['clips']
data['snapshot_origin']='Last saved thumb-anatomy export; live publication compares owned tracks'
(O/'cached_source.json').write_text(json.dumps(data))
if not (O/'ue_before.json').exists():(O/'ue_before.json').write_text(json.dumps(data))
