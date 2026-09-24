"""Import the central square altar, preserving all marble/gold/sapphire slots."""
import json
import re
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent
ROOT='/Game/Props/SquareAltar20260922'
PATH=ROOT+'/SM_SquareAltar'
A=u.AssetToolsHelpers.get_asset_tools()
E=u.EditorAssetLibrary
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh=True;options.import_as_skeletal=False
options.import_materials=False;options.import_textures=False
data=options.static_mesh_import_data
data.combine_meshes=True;data.auto_generate_collision=False
data.generate_lightmap_u_vs=True;data.transform_vertex_to_absolute=True
data.convert_scene=True;data.convert_scene_unit=True
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task=u.AssetImportTask();task.filename=str(HERE/'Authored/SM_SquareAltar.fbx')
task.destination_path=ROOT;task.destination_name='SM_SquareAltar'
task.automated=True;task.replace_existing=False;task.save=False
task.options=options;task.factory=u.FbxFactory()
if u.load_asset(PATH):raise RuntimeError('Altar already exists; do not overwrite an unknown revision')
A.import_asset_tasks([task])
mesh=u.load_asset(PATH)
if not mesh:raise RuntimeError('Altar FBX import failed')
materials=[]
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    name=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
    mat=u.load_asset(ROOT+'/Materials/M_'+name)
    if not mat:raise RuntimeError('Required altar material missing: '+name)
    mesh.set_material(i,mat);materials.append(mat.get_path_name())
# A concave top needs triangle collision; one convex box would fill the basin.
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True
mesh.set_editor_property('nanite_settings',nanite)
E.set_metadata_tag(mesh,'SourceReference','gamedev/assets/terrain/defense_base.png')
E.set_metadata_tag(mesh,'GeometryAuthoring','Reconstructed from 2D reference; unseen faces symmetric')
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PATH)],False):raise RuntimeError('Altar mesh save failed')
(HERE/'mesh_receipt.json').write_text(json.dumps({'asset':mesh.get_path_name(),'materials':materials,'saved':True,'runtime_tested':False},indent=2),encoding='utf-8')
print('SQUARE_ALTAR_MESH_SAVED '+mesh.get_path_name())
