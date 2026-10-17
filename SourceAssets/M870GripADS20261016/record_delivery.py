import json
from datetime import datetime
from pathlib import Path
O=Path(__file__).parent
receipt=json.loads((O/'install_receipt.json').read_text())
if not receipt.get('completed'):raise RuntimeError('Animation saving is not complete')
data=dict(definition='ue_m870',recorded_at=datetime.now().astimezone().isoformat(),assets_saved=True,animation_count=len(receipt['saved']),assets=receipt['saved'],editable_source=str(O/'M870_GripADS_Editable.blend'),native_source_changed=False,build_required=False,runtime_tested=False,visual_tested=False,auditioned=False,multiplayer_tested=False)
(O/'delivery.json').write_text(json.dumps(data,indent=2))
print('M870_GRIP_DELIVERED',len(receipt['saved']),'saved animations')
