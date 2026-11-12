"""Reuse the same review camera and measure across W37 and W38."""
from pathlib import Path
import json
here=Path(__file__).resolve().parent
prior=here.parent/'Wrist37/FollowupReview'
manifest=json.loads((prior/'manifest.json').read_text())
manifest['cases']=[x for x in manifest['cases'] if x['name'] in ['box_normal_base','box_empty_base']]
(here/'manifest_probe.json').write_text(json.dumps(manifest,indent=2))
for name in ['render_contact.py','package_native.py','contact_measure.py']:
    source=(prior/name).read_text()
    source=source.replace("HERE.parent.parent/'Wrist34/geometry_wrist_thirty_seven_followup'","HERE.parent/'Wrist34/geometry_wrist_thirty_eight_probe'")
    source=source.replace("HERE.parent/'render_final.py'","HERE.parent/'Wrist37/render_final.py'")
    (here/name).write_text(source)
print('Prepared matching W38 review scripts')
