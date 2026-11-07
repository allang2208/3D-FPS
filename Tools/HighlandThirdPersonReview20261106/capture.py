"""Requested offline third-person graph capture. Does not save game assets."""
from pathlib import Path
import json
import hashlib
import os
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(os.environ.get('HIGHLAND_REVIEW_OUTPUT', ROOT / 'Saved/HighlandThirdPersonReview20261106/native-v3'))
OUT.mkdir(parents=True, exist_ok=True)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world, f'fps.body.DiagnoseHighlandMotion {OUT.as_posix()}')
if not (OUT / 'report.json').exists():
    raise RuntimeError('Native capture did not complete')
catalog = json.loads((ROOT / 'Content/ColdSteelData/highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
parts = {}
for blade in ['highland_broadblade', 'highland_ridge_piercer']:
    for grip in ['factory', 'long_twohand']:
        rows = []
        for slot, option in [('blade_1', blade), ('guard', 'factory'), ('grip', grip), ('pommel', 'factory')]:
            spec = catalog['slots'][slot][option]
            mesh_path = spec.get('mesh_by_blade', {}).get(blade, spec['mesh'])
            mesh = u.load_asset(mesh_path)
            if not mesh:
                raise RuntimeError(mesh_path)
            stem = hashlib.sha1(mesh_path.encode()).hexdigest()[:8] + '_' + mesh.get_name()
            target = OUT / 'parts' / (stem + '.fbx')
            target.parent.mkdir(exist_ok=True)
            if not target.exists():
                task = u.AssetExportTask()
                task.object = mesh
                task.filename = str(target)
                task.automated = True
                task.prompt = False
                task.replace_identical = False
                task.options = u.FbxExportOption()
                if not u.Exporter.run_asset_export_task(task):
                    raise RuntimeError(str(target))
            location = list(spec.get('location_cm', [0, 0, 0]))
            if slot == 'pommel':
                location = [a+b for a,b in zip(location, catalog['slots']['grip'][grip].get('pommel_offset_cm', [0,0,0]))]
            rows.append(dict(slot=slot, mesh=mesh_path, file=target.name,
                             location=location,
                             scale=spec.get('scale', [1, 1, 1])))
        parts[blade + '/' + grip] = rows
(OUT / 'parts.json').write_text(json.dumps(parts, indent=2))
source_lengths = {}
for grip in ['Standard', 'LongGrip']:
    for suffix in ['', '_FromReady']:
        name = f'A_Highland_BreakSweep_{grip}{suffix}'
        asset = u.load_asset(f'/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104/{name}')
        source_lengths[name] = asset.get_play_length() if asset else None
    for phase in ['Charge', 'Release', 'Counter']:
        name = f'A_Highland_Ridge_{grip}_{phase}'
        asset = u.load_asset(f'/Game/Weapons/HighlandClaymore20260922/RidgeThrust20261105/{name}')
        source_lengths[name] = asset.get_play_length() if asset else None
(OUT / 'first-person-durations.json').write_text(json.dumps(source_lengths, indent=2))
print('HIGHLAND_THIRD_PERSON_CAPTURE_COMPLETE', OUT)
