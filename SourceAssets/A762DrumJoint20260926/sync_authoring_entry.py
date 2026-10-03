"""Refresh only the drum entry in the shared A762 accessory authoring package."""
import json
import shutil
from pathlib import Path

O = Path(__file__).resolve().parent
ACC = O.parent / 'A762Meshy20260920/Accessories05'
backup = O / 'Before/Accessories05'
backup.mkdir(parents=True, exist_ok=True)
for relative in ('authoring.json', 'SM_A762_drum.blend', 'Exports/SM_A762_drum.fbx'):
    src = ACC / relative
    dst = backup / relative
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

shutil.copy2(O / 'Exports/SM_A762_drum.fbx', ACC / 'Exports/SM_A762_drum.fbx')
shutil.copy2(O / 'SM_A762_drum.blend', ACC / 'SM_A762_drum.blend')
path = ACC / 'authoring.json'
report = json.loads(path.read_text(encoding='utf-8'))
report['meshes']['drum'] = {
    'name': 'SM_A762_drum',
    'materials': {
        'A762_drum_0': '/Game/Weapons/LargeDrumUpgrade20260920/AKM/M_AKM_DrumSurface',
        'A762_drum_1': '/Game/Weapons/A762/Accessories05/Materials/M_A762_drum_1',
        'A762_drum_2': '/Game/Weapons/LargeDrumUpgrade20260920/AKM/M_AKM_DrumSurface',
        'A762_drum_Neck': 'A762_FACTORY_MAGAZINE_FINISH',
        'A762_drum_Inside': 'A762_FACTORY_MAGAZINE_INTERIOR'},
    'sockets': {},
    'source': 'A762DrumJoint20260926: preserved drum, continuous closed tower and seated well interface'}
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_DRUM_AUTHORING_ENTRY_UPDATED')
