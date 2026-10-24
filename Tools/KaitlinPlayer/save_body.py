"""Save the complete female body with equipment coverage sections and native LODs."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
data = json.loads((WORK / 'Body/segmented_body.json').read_text())
E = u.EditorAssetLibrary
if E.does_asset_exist(data['asset']):
    raise RuntimeError('Body output exists; retain it before a new revision: ' + data['asset'])
source = u.load_asset(data['source'])
mesh, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
    source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if outcome != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read the complete female body.')
for triangle, material in enumerate(data['triangle_materials']):
    u.GeometryScript_Materials.set_triangle_material_id(mesh, triangle, material)
options = u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
options.use_mesh_bone_proportions = True
options.enable_recompute_normals = False
options.enable_recompute_tangents = False
options.materials = {material['slot']: u.load_asset(material['asset']) for material in data['materials']}
asset, outcome = u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(
    mesh, source.skeleton, data['asset'], options)
if outcome != u.GeometryScriptOutcomePins.SUCCESS or not asset:
    raise RuntimeError('Cannot create the segmented female body.')
asset.set_editor_property('physics_asset', source.physics_asset)
asset.set_editor_property('post_process_anim_blueprint', source.get_editor_property('post_process_anim_blueprint'))
if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):
    raise RuntimeError('Cannot configure the existing body LOD policy.')
if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(asset, 3, True, False):
    raise RuntimeError('Body LOD generation did not finish.')
if not E.save_loaded_asset(asset, False):
    raise RuntimeError('Body package was not saved.')
(WORK / 'Body/saved_asset.json').write_text(json.dumps({'mesh': asset.get_path_name(), 'source': data['source'], 'materials': data['materials']}, indent=2), encoding='utf-8')
(WORK / 'save_body_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_SEGMENTED_BODY_SAVED', asset.get_path_name(), flush=True)
