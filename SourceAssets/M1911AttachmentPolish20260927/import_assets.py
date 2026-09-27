"""Publish revised meshes at their existing paths, preserving runtime contracts."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;PROJECT=O.parents[1]
mag=json.loads((O/'magazine_authoring.json').read_text());optics=json.loads((O/'optics_authoring.json').read_text());icons=json.loads((O/'icons.json').read_text())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
entries={'ext_mag':mag,**optics};destinations={key:entry['old_asset'] for key,entry in entries.items()}
ICON_ROOT='/Game/Weapons/M1911/ExtendedMagazine20260927/PolishIcons20260927'
targets=set(destinations.values())|{ICON_ROOT+'/T_'+key for key in icons}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&targets:raise RuntimeError('Unsaved target packages; preserve editor changes: '+str(sorted(dirty&targets)))
receipt={'saved':[],'meshes':{},'icons':{},'game_tested':False,'native_change_required':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name());record()
def backup_disk(path):
    relative=Path(path.removeprefix('/Game/')+'.uasset');src=PROJECT/'Content'/relative;dst=O/'Before'/relative
    if src.exists() and not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

# Reimport the same loaded objects; never delete/recreate a referenced package.
# Unchanged paths preserve all inventory, dual-hand and preview users without a
# new DLL. Original disk packages are retained in the source revision directory.
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,entry in entries.items():
        path=destinations[key];mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Missing current attachment '+path)
        backup_disk(path)
        bindings={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
        sockets=[mesh.find_socket(name) for name in ['AimCenter','MountForward','MountUp']] if key!='ext_mag' else []
        socket_poses=[(str(s.socket_name),tuple(s.relative_location.to_tuple()),tuple(s.relative_rotation.to_tuple()),tuple(s.relative_scale.to_tuple())) for s in sockets if s]
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
        data=opt.static_mesh_import_data;data.combine_meshes=key!='ext_mag';data.import_mesh_lods=key=='ext_mag'
        data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS if key=='ext_mag' else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        prior=mesh.get_editor_property('asset_import_data')
        if isinstance(prior,u.FbxStaticMeshImportData):
            prior.set_editor_property('import_mesh_lods',key=='ext_mag');prior.set_editor_property('combine_meshes',key!='ext_mag')
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
        task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Reimport failed '+path)
        aliases={'M_HoloBody':'Holosight','M_HoloReticle':'Red_Dot','M_Panoramic_Glass':'Panoramic_Glass','M_Panoramic_Reticle':'Panoramic_Reticle','M_Panoramic_Body':'Panoramic_Body'}
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            exported=str(slot.material_slot_name);label=aliases.get(exported,exported)
            if label not in bindings:raise RuntimeError('Unbound retained material '+label+' on '+key)
            slot.material_interface=bindings[label];slot.material_slot_name=u.Name(label);slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        # Existing sockets are the active calibration and take precedence over
        # mathematically equivalent FBX round-off values.
        for socket_name,location,rotation,scale in socket_poses:
            socket=mesh.find_socket(socket_name)
            if socket is None:raise RuntimeError('Missing imported calibration socket '+socket_name)
            socket.set_editor_property('relative_location',u.Vector(*location))
            socket.set_editor_property('relative_rotation',u.Rotator(*rotation))
            socket.set_editor_property('relative_scale',u.Vector(*scale))
        E.set_metadata_tag(mesh,'M1911SurfaceRevision','RoundedTransitions20260927')
        E.set_metadata_tag(mesh,'M1911SurfaceSource',str(O))
        save(mesh);receipt['meshes'][key]={'asset':mesh.get_path_name(),'lods':mesh.get_num_lods(),
          'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'socket_policy':'retained exact current transforms'};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
for key,entry in icons.items():
    task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=ICON_ROOT;task.destination_name='T_'+key
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(ICON_ROOT+'/T_'+key)
    if not tex:raise RuntimeError('Cannot import icon '+key)
    tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
    tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(tex)
    destination=Path(entry['destination']);before=O/'Before/Icons'/destination.name
    if destination.exists() and not before.exists():before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,before)
    shutil.copy2(entry['file'],destination);receipt['icons'][key]={'asset':tex.get_path_name(),'png':str(destination)};record()
receipt['status']='imported_and_saved';record()
print('M1911_ATTACHMENT_POLISH_IMPORTED_AND_SAVED',flush=True)
