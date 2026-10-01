"""Save the relocated G18 tactical meshes and icons at their existing game paths."""
import unreal as u,json,hashlib,shutil,re
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'G18Integration20260929';P=O.parents[1]
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
ROOT='/Game/Weapons/G18/Integrated20260929';report={'saved':[],'meshes':{},'runtime_tested':False}
fix=json.loads((O/'authoring.json').read_text())

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required asset is missing: '+path)
    return obj

def save(asset):
    if not E.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(report,indent=2))

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for kind,entry in fix.items():
        name='SM_G18_'+kind;dest=ROOT+'/Attachments';file=Path(entry['fbx'])
        old=load(dest+'/'+name)
        materials={re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name)):s.material_interface.get_path_name() for s in old.static_materials}
        before=O/'BeforePackages';before.mkdir(exist_ok=True)
        package=P/'Content/Weapons/G18/Integrated20260929/Attachments'/(name+'.uasset')
        if not (before/package.name).exists():shutil.copy2(package,before/package.name)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=load(dest+'/'+name);slots=list(mesh.static_materials)
        for i,s in enumerate(slots):
            label=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name))
            if label not in materials:raise RuntimeError('No existing G18 material binding for '+label)
            s.material_interface=load(materials[label]);s.material_slot_name=u.Name(label);slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        # Explicitly replace imported socket translations too: reimport may retain
        # socket objects already present on the existing static mesh.
        sockets={}
        for source_name,point in entry['sockets_blender_m'].items():
            label=source_name.removeprefix('SOCKET_');socket=mesh.find_socket(label)
            if not socket:raise RuntimeError('Imported socket is missing: '+label)
            cm=[point[0]*100,-point[1]*100,point[2]*100]
            socket.set_editor_property('relative_location',u.Vector(*cm));sockets[label]=cm
        E.set_metadata_tag(mesh,'G18SourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
        E.set_metadata_tag(mesh,'G18TacticalFit','20260930: forward 25 mm, G18 rail saddle and emitter moved together')
        save(mesh)
        report['meshes'][kind]={'path':mesh.get_path_name(),'source':str(file),'body_forward_shift_mm':25,'sockets_cm':sockets,'materials':materials}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

for file in sorted((O/'Icons').glob('*.png')):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=ROOT+'/Icons';task.destination_name=file.stem
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=load(ROOT+'/Icons/'+file.stem);tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(tex)

path=S/'attachment_authoring.json';data=json.loads(path.read_text())
for kind,entry in fix.items():
    data[kind]['fbx']=entry['fbx'];data[kind]['repair_source']=str(O/'author_fit.py')
    data[kind]['forward_shift_mm']=25;data[kind]['sockets_blender_m']=entry['sockets_blender_m']
path.write_text(json.dumps(data,indent=2))
path=S/'icon_geometry.json';data=json.loads(path.read_text());data.update(json.loads((O/'icon_geometry.json').read_text()));path.write_text(json.dumps(data,separators=(',',':')))
report['status']='tactical_fit_imported_and_saved'
(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
print('G18_TACTICAL_FIT_SAVED',flush=True)
