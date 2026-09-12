"""Read the six retained grasp projects and reject references to archived files."""
import bpy
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
archive = json.loads((ROOT / 'Docs/Weapons/grasp-archive-20260912.json').read_text(encoding='utf-8-sig'))
moved = {(ROOT / row['original']).resolve() for row in archive['files']}
clips = ['idle', 'aim', 'fire', 'aim_fire', 'equip', 'reload', 'reload_empty', 'drum_reload', 'drum_reload_empty']
results = []
for weapon in ['m4', 'akm']:
    for variant in ['vertical', 'canted', 'prism']:
        case = 'MannyGraspDonor20260912' if variant == 'vertical' else 'VREGripExtensions20260912'
        title = 'Vertical' if variant == 'vertical' else variant
        source = ROOT / 'SourceAssets' / case / 'Final' / weapon / variant / f'{weapon.upper()}_{title}_VRE_Editable.blend'
        bpy.ops.wm.open_mainfile(filepath=str(source))
        prefix = f'A_{weapon.upper()}_{variant.title() if weapon == "m4" else variant}_'
        expected = {prefix + clip + '_VRE' for clip in clips}
        assert expected.issubset(set(bpy.data.actions.keys())), source
        refs = []
        for data in [*bpy.data.libraries, *bpy.data.images]:
            path = getattr(data, 'filepath', '')
            if not path or getattr(data, 'packed_file', None):
                continue
            resolved = Path(bpy.path.abspath(path, library=getattr(data, 'library', None))).resolve()
            assert resolved not in moved, (source, resolved)
            refs.append({'path': str(resolved), 'exists': resolved.exists()})
        results.append({'source': str(source.relative_to(ROOT)), 'actions': sorted(expected), 'references_to_archived_files': 0, 'external_references': refs})
        print('GRASP_EDITABLE_RETAINED', weapon, variant, flush=True)
(ROOT / 'Docs/Weapons/grasp-editable-references-20260912.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print('GRASP_EDITABLE_ARCHIVE_CHECK_PASS 6', flush=True)
