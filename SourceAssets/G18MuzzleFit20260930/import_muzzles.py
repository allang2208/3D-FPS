"""Import/save only the three approved G18 muzzle meshes at their existing paths."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'G18Integration20260929';P=O.parents[1]
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;ROOT='/Game/Weapons/G18/Integrated20260929'
KINDS=('suppressor','tactical_suppressor','brake')
auth=json.loads((O/'authoring.json').read_text());report={'saved':[],'meshes':{},'excluded':['titanium_brake'],'runtime_tested':False}
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing asset '+path)
    return obj
def save(asset):
    if not E.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for kind in KINDS:
        entry=auth[kind];name='SM_G18_'+kind;dest=ROOT+'/Attachments';path=dest+'/'+name;file=Path(entry['fbx'])
        old=load(path);bindings={str(s.material_slot_name):s.material_interface.get_path_name() for s in old.static_materials}
        if 'M_G18_MuzzleAdapter' not in bindings:bindings['M_G18_MuzzleAdapter']=bindings['TacticalMount' if kind=='tactical_suppressor' else 'M1911_AdapterSteel']
        if kind=='suppressor':bindings['MI_MuzzleRecess']='/Game/Weapons/M4MuzzlesV1/MI_MuzzleRecess'
        before=O/'BeforePackages';before.mkdir(exist_ok=True);package=P/'Content/Weapons/G18/Integrated20260929/Attachments'/(name+'.uasset')
        if not (before/package.name).exists():shutil.copy2(package,before/package.name)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=load(path);slots=list(mesh.static_materials)
        for i,s in enumerate(slots):
            label=str(s.material_slot_name)
            if label not in bindings:raise RuntimeError('Unmapped G18 muzzle slot '+label)
            s.material_interface=load(bindings[label]);slots[i]=s
        mesh.set_editor_property('static_materials',slots);sockets={}
        for label,point in entry['sockets_blender_m'].items():
            socket=mesh.find_socket(label)
            if not socket:raise RuntimeError('Missing imported '+kind+' socket '+label)
            cm=[point[0]*100,-point[1]*100,point[2]*100];socket.set_editor_property('relative_location',u.Vector(*cm));sockets[label]=cm
        E.set_metadata_tag(mesh,'G18SourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
        E.set_metadata_tag(mesh,'G18MuzzleFit','20260930: measured G18 bore collar; explicit outlet; three approved variants only')
        save(mesh)
        report['meshes'][kind]={'asset':mesh.get_path_name(),'source':str(file),'sockets_cm':sockets,'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
path=S/'attachment_authoring.json';data=json.loads(path.read_text())
for kind in KINDS:
    data[kind].update(fbx=auth[kind]['fbx'],slots=auth[kind]['slots'],repair_source=str(O/'author_muzzles.py'),material_overrides=report['meshes'][kind]['materials'])
path.write_text(json.dumps(data,indent=2))
path=S/'icon_geometry.json';data=json.loads(path.read_text());fresh=json.loads((O/'icon_geometry.json').read_text());data.update({k:fresh[k] for k in KINDS});path.write_text(json.dumps(data,separators=(',',':')))
report['status']='three_g18_muzzles_imported_and_saved';(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('G18_THREE_MUZZLES_SAVED',flush=True)
