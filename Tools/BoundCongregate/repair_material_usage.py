"""Repair the missing skeletal/cloth shader permutations without reimporting geometry."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
DEST = '/Game/Monsters/BoundCongregate'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != ROOT.parent.parent / 'FPSGAME.uproject':
    raise RuntimeError('Wrong project')

meshes = [u.load_asset(DEST + '/SK_BoundCongregate'),
          u.load_asset(DEST + '/Corpse/SK_BoundCongregate_Corpse')]
materials = {}
assignments = []
for mesh in meshes:
    if not mesh:
        raise RuntimeError('Missing target mesh')
    for slot in mesh.get_editor_property('materials'):
        mat = slot.material_interface
        if not mat or not isinstance(mat, u.Material):
            raise RuntimeError('Unexpected material on ' + mesh.get_name())
        materials[mat.get_path_name()] = mat
        assignments.append(dict(mesh=mesh.get_path_name(), slot=str(slot.get_editor_property('imported_material_slot_name')), material=mat.get_path_name()))

dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = [p for p in materials if p.split('.')[0] in dirty]
if conflicts:
    raise RuntimeError('Unsaved target materials retained: ' + str(conflicts))

result = dict(cause='Missing SkeletalMesh material usage caused default material fallback',
              pie_active=bool(editor.get_game_world()), assignments=assignments, materials=[], gameplay_tested=False)
for path, mat in sorted(materials.items()):
    flags = ('used_with_skeletal_mesh', 'used_with_clothing')
    before = {key: mat.get_editor_property(key) for key in flags}
    textures = [t.get_path_name() for t in L.get_used_textures(mat)]
    for key in flags:
        mat.set_editor_property(key, True)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed: ' + path + ': ' + str(errors))
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Material save failed: ' + path)
    result['materials'].append(dict(path=path, before=before, after={k: mat.get_editor_property(k) for k in flags}, textures=textures))

(ROOT / 'Records/material_usage_fix_20261007.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
