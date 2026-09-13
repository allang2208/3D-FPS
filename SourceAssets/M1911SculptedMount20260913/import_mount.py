"""Install the sculpted panoramic saddle with the current M1911 finish."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M1911/SculptedMount20260913/Meshes'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
auth=json.loads((O/'authoring.json').read_text())
old=json.loads((O.parent/'M1911MuzzleRedDot20260913/installed.json').read_text())['panoramic_red_dot']
name='SM_M1911_panoramic_red_dot'
task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=D;task.destination_name=name
task.automated=True;task.replace_existing=True;task.save=False
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_materials=False;options.import_textures=False;options.import_animations=False
data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=options
A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
if mesh is None:raise RuntimeError('No imported panoramic saddle')
slots=mesh.static_materials
for i,slot in enumerate(slots):
    exported=str(slot.material_slot_name)
    label=exported[2:] if exported.startswith('M_Panoramic_') else exported
    material=u.load_asset(old['materials'][label])
    if material is None:raise RuntimeError('Missing retained material '+label)
    slot.material_interface=material;slot.material_slot_name=u.Name(label);slots[i]=slot
mesh.set_editor_property('static_materials',slots)
E.set_metadata_tag(mesh,'M1911Revision','sculpted-saddle-20260913')
E.set_metadata_tag(mesh,'M1911Source',auth['source'])
E.set_metadata_tag(mesh,'M1911CoatingUV','3')
if not E.save_loaded_asset(mesh,only_if_is_dirty=False):raise RuntimeError('Could not save sculpted saddle')
report={'mesh':mesh.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},
        'coating_uv':3,'sockets_cm':{str(s.socket_name):list(s.relative_location.to_tuple()) for s in
                                   [mesh.find_socket(n) for n in ['AimCenter','MountForward','MountUp']] if s}}
(O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M1911_SCULPTED_MOUNT_IMPORTED')
