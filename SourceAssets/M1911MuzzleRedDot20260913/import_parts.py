"""Install two M1911 refinements using the existing coating and weather bindings."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent;D='/Game/Weapons/M1911/MuzzleRedDot20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
author=json.loads((O/'authoring.json').read_text())
old=json.loads((S/'M1911CompactFit20260913/installed.json').read_text())
bindings={
 'panoramic_red_dot':{
  'M_Panoramic_Glass':('Panoramic_Glass',old['panoramic_red_dot']['slots']['Panoramic_Glass']),
  'M_Panoramic_Reticle':('Panoramic_Reticle',old['panoramic_red_dot']['slots']['Panoramic_Reticle']),
  'M_Panoramic_Body':('Panoramic_Body',old['panoramic_red_dot']['slots']['Panoramic_Body']),
  'M1911_AdapterSteel':('M1911_AdapterSteel',old['panoramic_red_dot']['slots']['M1911_AdapterSteel'])},
 'brake':{key:(key,path) for key,path in old['suppressor']['slots'].items()}}
report={}
for key,info in author.items():
    name='SM_M1911_'+key
    task=u.AssetImportTask();task.filename=info['fbx'];task.destination_path=D+'/Meshes';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=options
    A.import_asset_tasks([task]);mesh=u.load_asset(task.destination_path+'/'+name)
    if mesh is None:raise RuntimeError('No imported mesh '+key)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        label,path=bindings[key][str(slot.material_slot_name)]
        material=u.load_asset(path)
        if material is None:raise RuntimeError('Missing installed material '+path)
        slot.material_interface=material;slot.material_slot_name=u.Name(label);slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'M1911Source',info['source'])
    E.set_metadata_tag(mesh,'M1911Revision','muzzle-red-dot-20260913')
    if not E.save_loaded_asset(mesh,only_if_is_dirty=False):raise RuntimeError('Could not save '+mesh.get_path_name())
    report[key]={'mesh':mesh.get_path_name(),'coating_uv':info['coating_uv'],
                 'materials':{str(slot.material_slot_name):slot.material_interface.get_path_name() for slot in slots},
                 'sockets_cm':{str(socket.socket_name):list(socket.relative_location.to_tuple()) for socket in
                               [mesh.find_socket(name) for name in ['AimCenter','Muzzle','MountForward','MountUp']] if socket}}
    (O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.log('M1911_MUZZLE_REDDOT_IMPORTED '+key)
u.log('M1911_MUZZLE_REDDOT_IMPORT_COMPLETE')
