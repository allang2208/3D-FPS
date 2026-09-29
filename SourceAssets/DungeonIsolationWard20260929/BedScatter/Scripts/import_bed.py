"""Import the fitted production bed without opening or saving a sample map."""
import hashlib
import json
import re
import runpy
import sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
WARD=ROOT.parent
PROJECT=WARD.parents[1]
cfg=json.loads((WARD/'Config/room.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'bed-manifest.json').read_text(encoding='utf-8'))
E=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; bed install pending')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def guard(asset):
    if asset.get_path_name().split('.')[0] in dirty:raise RuntimeError('Preserve unsaved asset '+asset.get_path_name())

path=cfg['bed_scatter']['mesh']
if path in dirty:raise RuntimeError('Preserve unsaved ward bed')
source=u.load_asset(manifest['source_mesh'])
if not source:raise RuntimeError('Missing imported hospital bed')
task=u.AssetImportTask();task.filename=manifest['fbx']
task.destination_path=path.rsplit('/',1)[0];task.destination_name=manifest['mesh']
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=options;task.factory=u.FbxFactory()
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
mesh=u.load_asset(path)
if not mesh:raise RuntimeError('Bed mesh import failed')
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
material_changes=[]
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
    material=u.load_asset(manifest['materials'][name])
    if not material:raise RuntimeError('Missing approved bed material '+name)
    material_changes.append(ensure_material_usage(material,guard));mesh.set_material(index,material)
body=mesh.get_editor_property('body_setup')
body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
shape_count=len(body.get_editor_property('agg_geom').get_editor_property('convex_elems'))
if shape_count!=manifest['collision_hulls']:raise RuntimeError('Bed collision import incomplete')
# Preserve the source render policy; instanced usage is persisted above.
mesh.set_editor_property('nanite_settings',source.get_editor_property('nanite_settings').copy())
if mesh.get_editor_property('nanite_settings').enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):
    raise RuntimeError('Bed Nanite build failed')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Bed save failed')

receipt=dict(stage='ward_bed_asset_saved',mesh=path,collision_hulls=shape_count,
    source_sha256=hashlib.sha256(Path(manifest['fbx']).read_bytes()).hexdigest(),
    source_mesh_preserved=manifest['source_mesh'],credit=manifest['credit'],gameplay_tested=False)
(ROOT/'Receipts/import-asset.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('WARD_BED_ASSET_SAVED',json.dumps(receipt,ensure_ascii=False),flush=True)
