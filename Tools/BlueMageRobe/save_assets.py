"""Save the approved robe, native bindings and embedded Chaos skirt assets."""
import json,hashlib,gc,sys,importlib.util
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import materials
DEST=materials.DEST;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
CLOTH_REVISION='20261019-hipfit-restored-v1'
ACTIVE_BODY_REVISION='FacingFix20261020'
receipt_path=R/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(saved={},runtime_tested=False)
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):return materials.load(path)
def save(asset):materials.save(asset)
def cloth_pose_physics(asset):
    cloths=list(asset.get_editor_property('mesh_clothing_assets'))
    if len(cloths)!=1:raise RuntimeError('Robe requires one continuous cloth asset')
    physics=cloths[0].get_editor_property('physics_asset')
    if not physics:raise RuntimeError('Robe body collision is missing')
    # UE ComputeRequiredBones includes the mesh PhysicsAsset. The pelvis-only
    # skirt cannot itself keep thigh/calf/foot bones in the CopyPose evaluation.
    # Runtime garment components remain NoCollision and never simulate bodies.
    asset.set_editor_property('physics_asset',physics)
def dynamic(d,ref=None,display=False):
    ids={str(b.name):b.index for b in B.get_all_bones_info(ref)[1]} if ref else {};ps=[];ns=[];uv=[];ws=[];fs=[];slots=[];lookup={}
    for fi,face in enumerate(d['triangles']):
        if display and d['triangle_materials'][fi]==9:continue
        tri=[]
        for ci,vi in enumerate(face):
            normal=d['normals'][fi][ci];tex=d['uv'][fi][ci];key=(vi,*[round(x,7) for x in normal+tex])
            if key not in lookup:lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*normal));uv.append(u.Vector2D(*tex));ws.append(d['weights'][vi])
            tri.append(lookup[key])
        fs.append(u.IntVector(*tri));slots.append(d['triangle_materials'][fi])
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uv,triangles=fs),0,True)
    if dm.get_triangle_count()!=len(fs):raise RuntimeError('Triangle construction failed '+d['profile'])
    if ref:
        B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
        for i,bindings in enumerate(ws):
            _,ok=B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in bindings.items()])
            if not ok:raise RuntimeError('Native binding failed '+d['profile'])
    for i,slot in enumerate(slots):u.GeometryScript_Materials.set_triangle_material_id(dm,i,slot,True)
    return dm
def skeletal(file,mats,body=False,group=None,revision=None):
    raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();d=json.loads(raw);profile=file.stem;key=(group or ('Body' if body else 'FP'))+'/'+profile;folder=DEST+(('/'+revision+'/') if revision else ('/CalfRestore20261019/' if group=='Underlayers' else '/'+ACTIVE_BODY_REVISION+'/' if body else '/'))+key;name='SK_'+profile+'_BlueMageRobe';path=folder+'/'+name;asset=u.load_asset(path)
    if asset and E.get_metadata_tag(asset,'BlueMageRobeSHA')==sha and (not body or E.get_metadata_tag(asset,'BlueMageClothRevision')==CLOTH_REVISION):
        if body:cloth_pose_physics(asset);save(asset)
        receipt['saved'][key]=dict(asset=asset.get_path_name(),author_sha256=sha,native=d['binding_source'],triangles=len(d['triangles']),lod_count=S.get_lod_count(asset),chaos_skirt=body);record();print('BLUE_ROBE_ALREADY_SAVED',key,flush=True);return
    source=load(d['binding_source']);ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native input failed '+profile)
    dm=dynamic(d,ref);asset=asset or A.duplicate_asset(name,folder,source)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh write failed '+profile)
    slots=list(asset.get_editor_property('materials'))
    for i,slot in enumerate(slots):slot.set_editor_property('material_slot_name',d['material_slots'][i])
    asset.set_editor_property('materials',slots)
    build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset);factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.load_asset(path+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory);groups=[]
    for ratio,screen in zip((1.,.65,.35) if body or group=='Underlayers' else (1.,1.,1.),(1.,.18,.075)):
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for prop,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(prop,value)
        group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);asset.set_editor_property('lod_settings',policy);models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD construction failed '+profile)
    asset.set_editor_property('physics_asset',None)
    if body and not u.FPSModularOutfitComponent.build_mage_robe_drape(asset):raise RuntimeError('Chaos skirt construction failed '+profile)
    if body:
        cloth_pose_physics(asset);E.set_metadata_tag(asset,'BlueMageClothRevision',CLOTH_REVISION)
    E.set_metadata_tag(asset,'BlueMageRobeSHA',sha);E.set_metadata_tag(asset,'SourceContract',d['contract']);save(asset)
    receipt['saved'][key]=dict(asset=asset.get_path_name(),author_sha256=sha,native=d['binding_source'],triangles=len(d['triangles']),lod_count=S.get_lod_count(asset),chaos_skirt=body);record();print('BLUE_ROBE_SAVED',key,flush=True)
def displays(mats):
    d=json.loads((R/'Authored/Body/Jason.json').read_text());T=u.GeometryScript_MeshTransforms
    spec=importlib.util.spec_from_file_location('robe_static_io',str(P/'Tools/ChainmailPants/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io);io.DEST=DEST
    for kind in ('Icon','Pickup'):
        dm=dynamic(d,display=True)
        if kind=='Icon':T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0))
        else:
            center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)];T.translate_mesh(dm,u.Vector(*[-v for v in center]));T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
        receipt[kind.lower()]=io.static(dm,DEST+'/'+kind+'s/SM_BlueMageRobe_'+kind,mats);record()
    file=R/'ue_blue_mage_robe.png'
    if not file.exists():print('BLUE_ROBE_ICON_PENDING',flush=True);return
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST+'/Icons';task.destination_name='T_BlueMageRobe_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);asset=load(DEST+'/Icons/T_BlueMageRobe_Icon')
    for prop,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():asset.set_editor_property(prop,value)
    save(asset);receipt['icon_texture']=asset.get_path_name();record()
def main():
    receipt['completed']=False;record()
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Preserve clothing assets during PIE')
    E.make_directory(DEST)
    if receipt.get('materials'):mats={k:[load(p) for p in v] for k,v in receipt['materials'].items()}
    else:
        lengths={p:json.loads((R/'Authored/Body'/(p+'.json')).read_text())['cloth_dimensions']['length_cm'] for p in ('Body','Jason')};mats=materials.create(lengths);receipt['materials']={k:[a.get_path_name() for a in v] for k,v in mats.items()};record()
    for file in sorted((R/'Authored/Body').glob('*.json')):
        skeletal(file,mats[file.stem.split('_')[0]],True);gc.collect();u.SystemLibrary.collect_garbage()
    for file in sorted((R/'Authored/FP').glob('*.json')):
        skeletal(file,mats['FP']);gc.collect();u.SystemLibrary.collect_garbage()
    displays(mats['Jason'])
    sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'))
    from save_icons import apply_item
    apply_item('ue_blue_mage_robe')
    receipt['completed']=bool(receipt.get('icon_texture'));record();print('BLUE_ROBE_ASSETS_COMPLETE',receipt['completed'],len(receipt['saved']),flush=True)
if __name__=='__main__':main()
