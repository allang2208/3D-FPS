"""Save the corrected RSH-12 animated-pose exports and matching profiles."""
import runpy,json
from pathlib import Path
O=Path(__file__).parent;SA=O.parent/'RSH12SingleAction20261003'
runpy.run_path(str(SA/'import_assets.py'),run_name='__main__')
receipt=json.loads((SA/'import_receipt.json').read_text(encoding='utf8'))
receipt.update(revision='RSH12FireFix20261003',cause='Animation FBX baking inherited mesh REST display state; exported constant reference transforms',
 correction='Evaluate armature in POSE for all four animated fire/cock exports',mesh_reimported=False,cpp_modified=False,
 game_started=False,testing='Not run; user testing')
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH12_ANIMATED_POSE_FIX_SAVED',len(receipt['saved']),flush=True)
