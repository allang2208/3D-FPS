import json
from datetime import datetime
from pathlib import Path
O=Path(__file__).parent
receipt=json.loads((O/'install_receipt.json').read_text())
if not receipt.get('completed'):raise RuntimeError('The animation import has not finished saving')
report=dict(definition='ue_m870',recorded_at=datetime.now().astimezone().isoformat(),assets_saved=True,animation_count=len(receipt['saved']),assets=receipt['saved'],editable_source=str(O/'M870_Urban_Editable.blend'),asset_receipt=str(O/'install_receipt.json'),native_source_changed=False,build_required=False,runtime_tested=False,auditioned=False,multiplayer_tested=False,source_license='Donor reuse/redistribution permission remains unconfirmed; retained locally, not published')
(O/'delivery.json').write_text(json.dumps(report,indent=2))
print('M870_UC_DELIVERED',report['animation_count'],'saved animations')
