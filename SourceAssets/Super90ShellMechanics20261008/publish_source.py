"""Retain the saved mesh/inspection changes in the current authoring inputs."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
if not json.loads((O/'import_receipt.json').read_text(encoding='utf-8')).get('completed'):
    raise RuntimeError('Save the UE shell/inspection assets before publishing source')
for source,target in (
    (O/'Super90_ShellMechanics_Editable.blend',S/'Super90_Gameplay_Editable.blend'),
    (O/'Exports/SK_Super90_V7.fbx',S/'Exports/SK_Super90_V7.fbx'),
    (O/'Exports/A_Super90_inspect.fbx',S/'Exports/Animations/A_Super90_inspect.fbx')):
    shutil.copy2(source,target)
print('SUPER90_SHELL_AND_INSPECT_SOURCE_PUBLISHED')
