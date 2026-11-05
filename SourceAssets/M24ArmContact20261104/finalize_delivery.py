"""Record the delivered previews against the exact saved profile export."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
publication=json.loads((root/'publish_receipt.json').read_text())
preview=json.loads((root/'GIF/delivery.json').read_text())
saved_hash=hashlib.sha256((root/'saved_profiles.json.gz').read_bytes()).hexdigest()
if not publication['complete'] or not preview['complete']:
    raise RuntimeError('Publication or preview export has not completed')
if preview['profile_source']!='saved_profiles.json.gz' or preview['profiles_sha256']!=saved_hash:
    raise RuntimeError('Preview export is not from the saved profiles')
publication['offline_preview_rendered']=True
publication['preview_delivery']='GIF/delivery.json'
(root/'publish_receipt.json').write_text(json.dumps(publication,indent=2))
status={'assets_saved':len(publication['saved']),'reload_entries_saved':publication['reload_clips'],
        'editable_source':'M24_ArmContact_Editable.blend','authoring_log':'author-delivery.log',
        'gif_count':len(preview['outputs']),'preview_source':'saved_profiles.json.gz',
        'new_magazine_grip_source_frames':[29.8,31,40,46],
        'offline_preview_complete':True,'runtime_tested':False}
(root/'delivery_status.json').write_text(json.dumps(status,indent=2))
print(json.dumps(status))
