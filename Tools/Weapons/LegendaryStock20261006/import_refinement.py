"""Save V3 surfaces, master meshes and the nine active fitted meshes in one batch."""
import json
import runpy
from pathlib import Path

T = Path(__file__).resolve().parent
P = T.parents[2]
O = P / 'SourceAssets/LegendaryStock20261006'
R = O / 'RefinementV3'

runpy.run_path(str(T / 'import_model.py'), run_name='__main__')
runpy.run_path(str(T / 'import_fitted.py'), run_name='__main__')
master = json.loads((O / 'import-receipt.json').read_text(encoding='utf-8'))
fitted = json.loads((O / 'Integration/fitted-import-receipt.json').read_text(encoding='utf-8'))
receipt = {
    'visual_revision': 'V3_concave_shoulder_contact',
    'status': 'master_surfaces_and_nine_runtime_fittings_saved',
    'master': master,
    'fitted': fitted,
    'native_code_changed': False,
    'stats_changed': False,
    'game_tested': False,
}
(R / 'asset-install-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('TACTICAL_STOCK_V3_SAVED ' + str(R / 'asset-install-receipt.json'))
