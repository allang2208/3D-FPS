"""Save the PKM-only animation tracks and both native/default bare-arm meshes."""
import hashlib,json,sys,shutil
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from skin_weights import binding_parameters,rebind
PROJECT=HERE.parents[2];BEFORE=HERE/'Before'
OUTFIT=PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
Q=u.GeometryScript_MeshQueries;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
snapshot=json.loads((HERE/'current_mesh.json').read_text())
parameters=binding_parameters(snapshot['bones'])
authoring=json.loads((HERE/'authoring.json').read_text())
receipt_file=HERE/'install_receipt.json'
receipt=json.loads(receipt_file.read_text()) if receipt_file.exists() else {'version':'PKM.LeftArm48','animations':{},'meshes':{},'runtime_tested':False}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def disk(path):return PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(path):
    target=BEFORE/'Packages'/path.relative_to(PROJECT/'Content')
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(path,target)
def save(asset):
    asset.modify()
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):
        raise RuntimeError('Save failed '+asset.get_path_name())
def record():receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')

world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world and ('UEDPIE' in world.get_name() or world.get_name().startswith('PIE_')):
    raise RuntimeError('Finish PIE before changing PKM assets')

inputs=[json.loads(p.read_text()) for p in sorted((HERE/'AuthoredTracks').glob('*.json'))]
if len(inputs)!=60:raise RuntimeError('Incomplete PKM animation set')
if sum(bool(x.get('contact_source')) for x in inputs)!=4:raise RuntimeError('Missing restored contact sources')
# Detect a real overlapping edit before changing any of this batch.
for data in inputs:
    path=data['asset'];expected=receipt['animations'].get(path,{}).get('after_sha256',data['source_sha256'])
    if sha(disk(path))!=expected:raise RuntimeError('PKM animation changed since authoring: '+path)
source=OUTFIT/'Authored/PKM.json'
new_source=HERE/'PKM_authored.json'
if sha(source) not in (authoring['source_authored_sha256'],sha(new_source)):
    raise RuntimeError('PKM skin source changed since authoring')

for data in inputs:
    path=data['asset']
    if path in receipt['animations']:continue
    asset=u.load_asset(path);backup(disk(path))
    controller=asset.get_editor_property('controller')
    if controller is None:
        controller=u.AnimDataController();controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('PKM LeftArm48 coherent arm segments and contact source',False)
    try:
        for name,keys in data['tracks'].items():
            if len(keys)!=data['keys']:raise RuntimeError('Incomplete track '+name)
            if not controller.set_bone_track_keys(name,[u.Vector(*k['p']) for k in keys],
                    [u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Cannot write '+name+' in '+path)
    finally:controller.close_bracket(False)
    E.set_metadata_tag(asset,'PKMLeftArmRevision','LeftArm48')
    E.set_metadata_tag(asset,'PKMLeftArmSource',str(HERE/'AuthoredTracks'/(asset.get_name()+'.json')))
    if data.get('contact_source'):E.set_metadata_tag(asset,'PKMContactSourceRestored',data['contact_action'])
    save(asset)
    receipt['animations'][path]={'keys':data['keys'],'tracks':list(data['tracks']),
        'before_sha256':data['source_sha256'],'after_sha256':sha(disk(path)),
        'contact_restored':bool(data.get('contact_source')),'saved':True}
    record();print('PKM_ARM_ANIMATION_SAVED',asset.get_name(),flush=True)

profile=snapshot['profile']
for path,material_ids in [(profile['native_bare_skin'],None),(snapshot['source'],profile['hide_source_materials'])]:
    if path in receipt['meshes']:continue
    asset=u.load_asset(path);before_sha=sha(disk(path));backup(disk(path))
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};indices={n:i for i,n in names.items()}
    _,ps,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(ps)
    _,ts,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    ids=set()
    for ti,t in enumerate(triangles):
        mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
        if valid and (material_ids is None or mat in material_ids):ids.update((t.x,t.y,t.z))
    touched=0
    for vi in sorted(ids):
        _,weights,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing vertex skin binding')
        original={names[w.bone_index]:w.weight for w in weights if w.weight>0}
        p=positions[vi];new=rebind((p.x,p.y,p.z),original,parameters)
        if sum(abs(new.get(n,0)-original.get(n,0)) for n in set(new)|set(original))<1.e-8:continue
        B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=indices[n],weight=w) for n,w in new.items()])
        touched+=1
    slots=list(asset.materials);lod_count=S.get_lod_count(asset)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+path)
    for lod in range(lod_count):
        settings=S.get_lod_build_settings(asset,lod);settings.set_editor_property('use_full_precision_u_vs',True)
        S.set_lod_build_settings(asset,lod,settings)
    if lod_count>1 and not S.regenerate_lod(asset,lod_count,True,False):raise RuntimeError('Cannot regenerate PKM arm LODs')
    E.set_metadata_tag(asset,'PKMLeftArmRevision','LeftArm48')
    save(asset)
    receipt['meshes'][path]={'vertices_reweighted':touched,'lods':lod_count,
        'before_sha256':before_sha,'after_sha256':sha(disk(path)),'saved':True}
    record();print('PKM_ARM_MESH_SAVED',asset.get_name(),touched,flush=True)

# Publish only PKM source bookkeeping, after both actual asset variants saved.
source.write_bytes(new_source.read_bytes())
for relative in ('Saved/PKM.json','NativeDefaults/PKM.json'):
    path=OUTFIT/relative;target=BEFORE/(relative.replace('/','_'))
    if not target.exists():shutil.copy2(path,target)
    data=json.loads(path.read_text());data['authored_sha256']=sha(source)
    data['left_arm_revision']='LeftArm48';data['runtime_tested']=False
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
receipt['authored_source_published']=True;receipt['complete']=True;record()
print('PKM_LEFT_ARM48_SAVED',len(receipt['animations']),len(receipt['meshes']),flush=True)
