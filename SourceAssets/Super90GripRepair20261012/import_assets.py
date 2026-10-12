"""Publish five Super90 grip interfaces and four complete current pose layers."""
import unreal as u
import gzip,json,hashlib,shutil,datetime
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
MESH_ONLY=globals().get('MESH_ONLY',False)
D='/Game/Weapons/Super90/Foregrips20261007'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def read(name):
    with gzip.open(O/(name+'.json.gz'),'rt',encoding='utf-8') as f:return json.load(f)
def asset(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def snapshot(obj):
    clips=[]
    for c in obj.get_editor_property('clips'):
        row={'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[]}
        retained=c.get_editor_property('retained')
        if retained:row['retained']=retained.get_path_name()
        for t in c.get_editor_property('tracks'):
            row['tracks'].append({'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))})
        clips.append(row)
    return clips
before=read('profiles_before');after=read('profiles_after')
profiles={} if MESH_ONLY else {key:asset(row['path']) for key,row in before.items()}
# Preserve newer parallel animation edits if the production inputs have changed.
for key,obj in profiles.items():
    if snapshot(obj)!=before[key]['clips']:raise RuntimeError('Production profile changed since export: '+key)
meshes={key:asset(D+'/Meshes/SM_Super90_'+key) for key in ('vertical','tactical_vertical','canted','prism','angled')}
materials={key:{str(s.material_slot_name):s.material_interface for s in obj.static_materials} for key,obj in meshes.items()}
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=O/'Backup'/stamp;backup.mkdir(parents=True)
receipt={'completed':False,'backup':str(backup),'saved':[],'profiles':{},'meshes':{},'runtime_tested':False,'originals':{}}
if MESH_ONLY:
    receipt=json.loads((O/'import_receipt.json').read_text());receipt['completed']=False
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def disk(obj):return P/'Content'/Path(obj.get_path_name().split('.')[0].removeprefix('/Game/')).with_suffix('.uasset')
for obj in [*meshes.values(),*profiles.values()]:
    path=disk(obj);sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if MESH_ONLY:
        if sha!=receipt['saved_sha256'][str(path)]:raise RuntimeError('Production mesh changed after first import: '+str(path))
    shutil.copy2(path,backup/path.name)
    if not MESH_ONLY:receipt['originals'][str(path)]=sha
gun=P/'Content/Weapons/Super90/Cransh20261006/SK_Super90_V7.uasset'
receipt['native_mesh_sha256']=hashlib.sha256(gun.read_bytes()).hexdigest();record()
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']:receipt['saved'].append(obj.get_path_name())
    record()
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key in meshes:
        name='SM_Super90_'+key
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_as_skeletal=False
        options.import_materials=False;options.import_textures=False;options.import_animations=False
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
        data.generate_lightmap_u_vs=False;data.remove_degenerates=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'))
        task.destination_path=D+'/Meshes';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True
        task.save=False;task.factory=u.FbxFactory();task.options=options
        A.import_asset_tasks([task]);mesh=asset(D+'/Meshes/'+name)
        slots=list(mesh.static_materials)
        for i,s in enumerate(slots):
            label=str(s.material_slot_name)
            match=label if label in materials[key] else label.replace('.','_')
            if match not in materials[key] and key=='angled' and 'Polymer' in label:
                match='Resonance_Metal_M4_001'
            if match not in materials[key]:raise RuntimeError('Material slot changed: '+key+' '+label)
            s.material_interface=materials[key][match];slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        settings=editor.get_lod_build_settings(mesh,0)
        settings.recompute_normals=False;settings.recompute_tangents=False;settings.remove_degenerates=False
        settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
        editor.set_lod_build_settings(mesh,0,settings)
        E.set_metadata_tag(mesh,'Super90GripRepair20261012','Closed rail/body interface and native fore-end fitted shoe; original grip body and material bindings')
        save(mesh);receipt['meshes'][key]={'path':mesh.get_path_name(),'slots':[str(s.material_slot_name) for s in slots]}
    for key,obj in profiles.items():
        if not obj.set_shared_clips_from_json(json.dumps(after[key])):raise RuntimeError('Profile import failed '+key)
        E.set_metadata_tag(obj,'Super90GripRepair20261012','Accepted M4 grasp anatomical frames adapted to native Super90; current 30 clips and release phases retained')
        save(obj);receipt['profiles'][key]={'path':obj.get_path_name(),'clips':len(obj.get_editor_property('clips'))}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt['native_mesh_unchanged']=hashlib.sha256(gun.read_bytes()).hexdigest()==receipt['native_mesh_sha256']
receipt['saved_sha256']={str(disk(asset(path))):hashlib.sha256(disk(asset(path)).read_bytes()).hexdigest() for path in receipt['saved']}
receipt['completed']=True;record()
print('SUPER90_GRIP_REPAIR_SAVED '+str(len(receipt['saved'])),flush=True)
