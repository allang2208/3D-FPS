"""Save only PKM outfit bindings and the ten contact-preserving reload edits."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
OUTFITS=PROJECT/'SourceAssets/ModularOutfit20260925'
manifest=json.loads((HERE/'install_manifest.json').read_text())
authored=json.loads((HERE/'outfit_authoring.json').read_text())
receipt_path=HERE/'install_receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {
    'revision':'ArmJoint49','meshes':{},'animations':{},'runtime_tested':False,'complete':False}
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
Q=u.GeometryScript_MeshQueries;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def disk(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(p,group='Packages'):
    relative=p.relative_to(PROJECT/'Content') if group=='Packages' else p.relative_to(OUTFITS)
    destination=HERE/'Before'/group/relative;destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.exists():shutil.copy2(p,destination)
def record():receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
def save(asset):
    asset.modify()
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Cannot save '+asset.get_path_name())

receipt['pending_animation_updates']=[path for path,entry in manifest['animations'].items()
    if receipt['animations'].get(path,{}).get('authored_tracks_sha256')!=sha(Path(entry['tracks_file']))]
if receipt['pending_animation_updates']:receipt['complete']=False
record()
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Finish active PIE before saving PKM joints')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active game world; preserve current play session')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for kind,items in [('meshes',list(manifest['meshes'].values())),('animations',[dict(v,asset=p) for p,v in manifest['animations'].items()])]:
    for data in items:
        path=data['asset'];expected=receipt[kind].get(path,{}).get('after_sha256',data['source_sha256'])
        if sha(disk(path))!=expected:raise RuntimeError('Overlapping asset edit: '+path)
        if path.split('.')[0] in dirty:raise RuntimeError('Unsaved PKM asset: '+path)
for family,info in authored.items():
    source=Path(info['source']);candidate=HERE/'Authored'/f'{family}.json'
    if sha(source) not in [info['before_sha256'],sha(candidate)]:raise RuntimeError('Overlapping outfit source edit: '+family)
    if json.loads(candidate.read_text())['bare_authored_sha256']!=sha(OUTFITS/'BarePalmV7/Authored/PKM.json'):
        raise RuntimeError('Bare binding changed after authoring: '+family)

for family,data in manifest['meshes'].items():
    path=data['asset']
    if path in receipt['meshes']:continue
    asset=u.load_asset(path);backup(disk(path))
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,bones=B.get_all_bones_info(dm);indices={str(b.name):b.index for b in bones};names={b.index:str(b.name) for b in bones}
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    ids=sorted({v for t in ts for v in [t.x,t.y,t.z]})
    if len(ids)!=len(data['weights']):raise RuntimeError('Vertex layout changed: '+family)
    touched=0
    for vi,weights in zip(ids,data['weights']):
        _,old,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Invalid original binding')
        old={names[w.bone_index]:w.weight for w in old if w.weight>0}
        if sum(abs(old.get(n,0)-weights.get(n,0)) for n in set(old)|set(weights))<1.e-5:continue
        B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=indices[n],weight=w) for n,w in weights.items()])
        touched+=1
    slots=list(asset.materials);lods=S.get_lod_count(asset)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[v.material_interface for v in slots],new_material_slot_names=[v.material_slot_name for v in slots],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save binding: '+family)
    for lod in range(lods):
        settings=S.get_lod_build_settings(asset,lod);settings.set_editor_property('use_full_precision_u_vs',True)
        S.set_lod_build_settings(asset,lod,settings)
    if lods>1 and not S.regenerate_lod(asset,lods,True,False):raise RuntimeError('Cannot rebuild PKM outfit LODs')
    E.set_metadata_tag(asset,'PKMArmJointRevision','ArmJoint49')
    E.set_metadata_tag(asset,'PKMArmJointSource',str(HERE/'Authored'/f'{family}.json'))
    E.set_metadata_tag(asset,'BareAuthoredSHA256',sha(OUTFITS/'BarePalmV7/Authored/PKM.json'))
    save(asset)
    receipt['meshes'][path]={'family':family,'vertices_reweighted':touched,'lods':lods,
        'before_sha256':data['source_sha256'],'after_sha256':sha(disk(path)),'saved':True}
    record();print('PKM_JOINT49_MESH_SAVED',family,touched,flush=True)

for path,entry in manifest['animations'].items():
    track_sha=sha(Path(entry['tracks_file']))
    if receipt['animations'].get(path,{}).get('authored_tracks_sha256')==track_sha:
        asset=u.load_asset(path)
        if E.get_metadata_tag(asset,'PKMLeftArmSource')!=entry['tracks_file']:
            E.set_metadata_tag(asset,'PKMLeftArmSource',entry['tracks_file']);save(asset)
            receipt['animations'][path]['after_sha256']=sha(disk(path));record()
        continue
    data=json.loads(Path(entry['tracks_file']).read_text());asset=u.load_asset(path);backup(disk(path))
    controller=asset.get_editor_property('controller')
    if controller is None:
        controller=u.AnimDataController();controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('PKM ArmJoint49 eased elbow support with fixed palm contact',False)
    try:
        for bone,keys in data['tracks'].items():
            if len(keys)!=data['keys']:raise RuntimeError('Incomplete track '+bone)
            if not controller.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
                [u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):raise RuntimeError('Cannot save '+bone)
    finally:controller.close_bracket(False)
    E.set_metadata_tag(asset,'PKMLeftArmRevision','ArmJoint49')
    E.set_metadata_tag(asset,'PKMLeftArmSource',entry['tracks_file'])
    E.set_metadata_tag(asset,'PKMArmJointSource',entry['tracks_file'])
    save(asset)
    receipt['animations'][path]={'keys':data['keys'],'tracks':list(data['tracks']),
        'before_sha256':entry['source_sha256'],'after_sha256':sha(disk(path)),
        'authored_tracks_sha256':track_sha,'saved':True}
    record();print('PKM_JOINT49_ANIMATION_SAVED',asset.get_name(),flush=True)

for family in manifest['meshes']:
    candidate=HERE/'Authored'/f'{family}.json';source=OUTFITS/family/'Authored/PKM.json'
    backup(source,'Sources');source.write_bytes(candidate.read_bytes())
    saved=OUTFITS/family/'Saved/PKM.json';backup(saved,'Sources')
    info=json.loads(saved.read_text());info.update(authored_sha256=sha(source),joint_revision='ArmJoint49',
        bare_authored_sha256=sha(OUTFITS/'BarePalmV7/Authored/PKM.json'),runtime_tested=False)
    saved.write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
receipt['authored_sources_published']=True;receipt['pending_animation_updates']=[];receipt['complete']=True;record()
print('PKM_ARM_JOINT49_SAVED',len(receipt['meshes']),len(receipt['animations']),flush=True)
