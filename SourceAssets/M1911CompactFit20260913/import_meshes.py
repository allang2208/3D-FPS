"""Import compact geometry, retaining the installed M1911 coating/optics/wet mappings."""
import unreal as u, json, os
from pathlib import Path

O=Path(__file__).parent; S=O.parent; D='/Game/Weapons/M1911/CompactFit20260913'
A=u.AssetToolsHelpers.get_asset_tools(); E=u.EditorAssetLibrary
optics=json.loads((O/'optics_authoring.json').read_text())
tactical=json.loads((O/'tactical_authoring.json').read_text())
old_optics=json.loads((S/'M1911Attachments20260913/installed.json').read_text())
old_tactical=json.loads((S/'M1911Tactical20260913/installed.json').read_text())['parts']
source_optics=json.loads((S/'M1911Attachments20260913/sources.json').read_text())['parts']
report=json.loads((O/'installed.json').read_text()) if (O/'installed.json').exists() else {}

for key,author in {**optics,**tactical}.items():
    if os.environ.get('M1911_COMPACT_OPTICS_ONLY')=='1' and key in tactical:continue
    device=key in tactical
    name='SM_TacticalDevice' if device else 'SM_M1911_'+key
    folder=D+'/'+key if device else D+'/Meshes'
    task=u.AssetImportTask();task.filename=author['fbx' if device else 'file']
    task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=options
    A.import_asset_tasks([task]);mesh=u.load_asset(folder+'/'+name)
    if mesh is None:raise RuntimeError('Mesh import failed '+key)
    aliases={}
    if not device:
        for exported,slot in zip(author['source_export_slots'],source_optics[key]['slots']):
            aliases[exported]=slot['slot'];aliases[exported.replace('.','_')]=slot['slot']
        aliases['M1911_AdapterSteel']='M1911_AdapterSteel'
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        exported=str(slot.material_slot_name)
        if device:
            collar='Collar' in exported
            material=old_tactical[key]['collar_material' if collar else 'body_material']
            label='M_Tactical_Collar' if collar else 'M_Tactical_'+key
        else:
            label=aliases[exported];material=old_optics[key]['slots'][label]
        binding=u.load_asset(material)
        if binding is None:raise RuntimeError('Missing existing coating '+material)
        slot.material_interface=binding;slot.material_slot_name=u.Name(label);slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'M1911CompactFit','20260913')
    E.set_metadata_tag(mesh,'M1911PreviousMesh',old_tactical[key]['mesh'] if device else old_optics[key]['mesh'])
    E.set_metadata_tag(mesh,'M1911PhysicalCoatingUV',str(author['uv_index']))
    if not E.save_loaded_asset(mesh,only_if_is_dirty=False):raise RuntimeError('Could not save '+mesh.get_path_name())
    box=mesh.get_bounding_box()
    report[key]={'mesh':mesh.get_path_name(),'slots':{str(slot.material_slot_name):slot.material_interface.get_path_name() for slot in slots},
                 'bounds_cm':{'min':list(box.min.to_tuple()),'max':list(box.max.to_tuple())},
                 'sockets_cm':{str(socket.socket_name):list(socket.relative_location.to_tuple()) for socket in
                               [mesh.find_socket(name) for name in ['Emitter','AimGuide','MountForward','MountUp','AimCenter','Muzzle']] if socket},
                 'coating_uv':author['uv_index'],'material_policy':'reuse installed M1911 dry materials and existing rain mappings'}
    (O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.log('M1911_COMPACT_IMPORTED '+key)
u.log('M1911_COMPACT_IMPORT_COMPLETE')
