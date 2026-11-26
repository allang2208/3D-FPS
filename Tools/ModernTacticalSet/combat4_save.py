"""Save fresh R4 native skeletal packages, explicitly replacing all three LODs."""
import json,hashlib,importlib.util,gc,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR4';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing native/PBR dependency '+p)
    return a
def save(a):
    if not a.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside fresh R4 revision')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
spec=importlib.util.spec_from_file_location('r4_native_io',str(P/'Tools/ChainmailPants/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
receipt=read(R/'saved.json') if (R/'saved.json').exists() else dict(wear={},materials='Existing verified earth-brown R3 textile PBR retained')
def record():
    tmp=R/'saved.json.tmp';tmp.write_text(json.dumps(receipt,indent=2),encoding='utf-8');os.replace(tmp,R/'saved.json')
manifest=read(Path(os.environ.get('TS01_R4_SAVE_PLAN',str(R/'authored.json'))));limit=int(os.environ.get('TS01_R4_BATCH_SIZE','6'));count=0;receipt['completed']=False;light_batch=False
for row in manifest['rows']:
    if not (R/'collar-fitted.json').exists() and row['rig'] in ['Jason','Kaitlin'] and not row.get('kind'):continue
    path=row['asset'];fingerprint=sha(row['file'])
    if receipt['wear'].get(path,{}).get('sha256')==fingerprint:continue
    if E.does_asset_exist(path) and not path.endswith('/SK_TS01_Combat_M16'):
        existing=u.load_asset(path)
        if existing and E.get_metadata_tag(existing,'CombatSourceSHA')==fingerprint:
            receipt['wear'][path]=dict(asset=existing.get_path_name(),sha256=fingerprint,rig=row['rig'],kind=row.get('kind'),lod_count=3);record();del existing;gc.collect();u.SystemLibrary.collect_garbage();continue
    light=row.get('kind')=='gloves' or row['rig'] not in ['Jason','Kaitlin']
    if count==0:
        light_batch=light
        if light:limit=24
    elif light_batch and not light:break
    d=read(row['file']);source=load(d['source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native skeleton read '+path)
    dm=io.dynamic(d,native);folder,name=path.rsplit('/',1);asset=u.load_asset(path) or A.duplicate_asset(name,folder,source);asset.set_editor_property('physics_asset',None)
    provenance=u.new_object(u.AssetImportData,outer=asset);provenance.scripted_add_filename(row['file'],0,'R4 native garment source');asset.set_editor_property('asset_import_data',provenance)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings);policy=u.load_asset(path+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory);groups=[]
    for screen in [1.,.18,.065]:
        group=u.SkeletalMeshLODGroupSettings();reduction=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=1.,num_of_vert_percentage=1.,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():reduction.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',reduction);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);asset.set_editor_property('lod_settings',policy);save(policy)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(m) for m in d['materials']],new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    # The source templates already carry native LODs. GeometryScript creates a
    # missing source index when writing, without relying on stale reduction caches.
    for lod in range(3):
        options.set_editor_property('defer_mesh_post_edit_change',lod<2)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native LOD write '+str(lod)+' '+path)
    for lod in range(3):
        settings=S.get_lod_build_settings(asset,lod);settings.set_editor_property('use_full_precision_u_vs',True);settings.set_editor_property('recompute_normals',False);S.set_lod_build_settings(asset,lod,settings)
    E.set_metadata_tag(asset,'CombatSourceSHA',fingerprint);E.set_metadata_tag(asset,'CombatRevision','R4 recut garment / native cuff and bone anchors');save(asset)
    receipt['wear'][path]=dict(asset=asset.get_path_name(),sha256=fingerprint,rig=row['rig'],kind=row.get('kind'),lod_count=3);record();count+=1;print('R4_SAVED',len(receipt['wear']),path,flush=True)
    del d,dm,native,source,asset;gc.collect();u.SystemLibrary.collect_garbage()
    if count>=limit:break
receipt['completed']=all(receipt['wear'].get(row['asset'],{}).get('sha256')==sha(row['file']) for row in manifest['rows']);receipt['manifest']=str(os.environ.get('TS01_R4_SAVE_PLAN',R/'authored.json'));record();print('R4_SAVE_BATCH_COMPLETE',count,receipt['completed'],flush=True)
