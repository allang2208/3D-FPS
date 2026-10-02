"""Save the authored M16 wrist and sprint productions; no runtime test."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
receipt_path = O / 'asset-install-completion.json'
receipt = {'revision': 2026100208, 'complete': False, 'stages': [],
    'background_commandlet': True, 'interactive_editor_started': False,
    'tested': False, 'rendered': False}

def record():
    tmp = receipt_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    tmp.replace(receipt_path)

record()
try:
    for stage, relative in [('wrist', 'Wrist/install_common_wrist_bind.py'),
                            ('sprint', 'Sprint/import_sprint_only.py')]:
        script = O / relative
        exec(compile(script.read_bytes(), str(script), 'exec'),
             {'__file__': str(script), '__name__': '__main__'})
        receipt['stages'].append(stage)
        record()
    wrist = json.loads((O / 'Wrist/installed.json').read_text(encoding='utf-8'))
    sprint = json.loads((O / 'Sprint/import-receipt.json').read_text(encoding='utf-8'))
    receipt['wrist_meshes_saved'] = len(wrist)
    receipt['sprint_animations_saved'] = len(sprint['animations'])
    receipt['sprint_profiles_saved'] = len(sprint['profiles'])
    receipt['complete'] = bool(sprint['complete'])
    record()
    u.log('M16_SPRINT_DOOR_ASSET_INSTALL_COMPLETE ' + json.dumps(receipt))
except Exception as error:
    receipt['error'] = str(error)
    record()
    raise
