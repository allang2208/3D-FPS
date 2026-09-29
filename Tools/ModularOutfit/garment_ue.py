"""UE commandlet helpers. Preserve mesh attributes; snapshot all saved LODs."""
import json
from pathlib import Path
import unreal as u
from garment_pipeline import read, write, digest, asset_file

G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries

def transform(t):
    return dict(p=list(t.translation.to_tuple()),q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],s=list(t.scale3d.to_tuple()))

def dynamic(asset,lod=0):
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved LOD '+asset.get_path_name()+':'+str(lod))
    return dm

def snapshot(asset,lod=0):
    # Use source LOD0 for authoring indices; render LODs are also captured for QA.
    dm=dynamic(asset,lod);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    d=dict(source=asset.get_path_name(),asset_sha256=digest(asset_file(asset.get_path_name())),lod=lod,
        positions=[[p.x,p.y,p.z] for p in ps],triangles=[[t.x,t.y,t.z] for t in ts],
        rest={str(b.name):transform(b.world_transform) for b in bones},weights=[],materials=[],
        slots=[str(m.material_slot_name) for m in asset.get_editor_property('materials')])
    for i in range(len(ps)):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Invalid saved vertex '+str(i))
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    for i in range(len(ts)):d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    return d

def source_snapshot(asset):
    # Source model IDs are needed when applying edits; do not mix with render IDs.
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source unavailable')
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    d=dict(source=asset.get_path_name(),positions=[[p.x,p.y,p.z] for p in ps],triangles=[[t.x,t.y,t.z] for t in ts],rest={str(b.name):transform(b.world_transform) for b in bones},weights=[],materials=[])
    for i in range(len(ps)):
        _,ws,valid=B.get_vertex_bone_weights(dm,i);d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    for i in range(len(ts)):d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    return dm,d

def save_candidate(dm,source,destination,folder,local_corrections=None,binding=None,recompute_normals=False):
    if u.EditorAssetLibrary.does_asset_exist(destination):raise RuntimeError('Use a new candidate path: '+destination)
    asset=u.EditorAssetLibrary.duplicate_asset((binding or source).get_path_name(),destination)
    if not asset:raise RuntimeError('Cannot duplicate candidate')
    slots=list(source.get_editor_property('materials'))
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[m.material_interface for m in slots],new_material_slot_names=[m.material_slot_name for m in slots],enable_recompute_normals=recompute_normals,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write candidate')
    subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):raise RuntimeError('LOD setup failed')
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.AssetToolsHelpers.get_asset_tools().create_asset(destination.rsplit('/',1)[1]+'_LODPolicy',destination.rsplit('/',1)[0],u.SkeletalMeshLODSettings,factory)
    if not policy:raise RuntimeError('Cannot create garment LOD policy')
    lods=[]
    for index in range(3):
        info=u.SkeletalMeshLODGroupSettings();settings=info.get_editor_property('reduction_settings')
        settings.set_editor_property('num_of_triangles_percentage',[1.,.9,.8][index])
        settings.set_editor_property('lock_edges',True)
        settings.set_editor_property('enforce_bone_boundaries',True)
        settings.set_editor_property('merge_coincident_vert_bones',False)
        settings.set_editor_property('welding_threshold',0.)
        settings.set_editor_property('improve_triangles_for_cloth',True)
        info.set_editor_property('reduction_settings',settings)
        info.set_editor_property('screen_size',u.PerPlatformFloat(default=[1.,.2,.08][index]));lods.append(info)
    policy.set_editor_property('lod_groups',lods)
    if not u.EditorAssetLibrary.save_loaded_asset(policy,False):raise RuntimeError('LOD policy save')
    asset.set_editor_property('lod_settings',policy)
    # UE 5.8 moved per-mesh LOD info into FSkeletalMeshSourceModel. Assigning
    # a policy alone does not replace settings of existing imported LODs.
    models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):
        model.set_editor_property('reduction_settings',lods[i].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    if not subsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD generation failed')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or u.EditorAssetLibrary.save_loaded_asset(asset,False)):raise RuntimeError('Save failed')
    receipt=dict(asset=asset.get_path_name(),asset_sha256=digest(asset_file(asset.get_path_name())),snapshots={},local_corrections=local_corrections or [])
    for lod in range(3):
        path=Path(folder)/('LOD'+str(lod)+'.json');write(path,snapshot(asset,lod));receipt['snapshots'][str(lod)]=dict(path=str(path),sha256=digest(path))
    write(Path(folder)/'source.json',source_snapshot(asset)[1]);write(Path(folder)/'saved.json',receipt)
    return receipt

def derive_bound(source_path,native_path,destination,folder,correction_edits=None):
    """Transport geometry AND weights to the native bind; never publish here.

    correction_edits is an explicitly authored JSON file in target coordinates,
    with vertex_id/position/weights. Existing per-profile fixes must be supplied
    rather than silently discarded by regeneration.
    """
    source=u.load_asset(source_path);native=u.load_asset(native_path)
    dm,data=source_snapshot(source);_,target=source_snapshot(native)
    # Dual-wield sources can contain one arm despite retaining both bone chains.
    # Infer the rendered arm side from influences, never from the profile suffix.
    mass={s:sum(v for weights in target['weights'] for n,v in weights.items() if n.endswith('_'+s) and n.startswith(('upperarm','lowerarm','hand_'))) for s in ('l','r')}
    sides={s for s,value in mass.items() if value>max(mass.values())*.05}
    if not sides:raise RuntimeError('Native asset has no supported arm geometry')
    discarded=[]
    if len(sides)==1:
        side=next(iter(sides))
        def belongs(i):
            w=data['weights'][i];return sum(v for n,v in w.items() if n.endswith('_'+side))>=sum(v for n,v in w.items() if n.endswith('_'+('r' if side=='l' else 'l')))
        for i,face in enumerate(data['triangles']):
            if not all(belongs(v) for v in face):
                discarded.append(i)
    def matrix(t):
        q=t['q'];return u.Transform(location=u.Vector(*t['p']),rotation=u.Quat(*q).rotator(),scale=u.Vector(*t['s']))
    # Transform positions through each weighted source-bone local frame, then
    # through the target bone world frame, preserving native centimetre scales.
    transforms={n:(matrix(data['rest'][n]),matrix(target['rest'][n])) for w in data['weights'] for n in w}
    for i,(p,weights) in enumerate(zip(data['positions'],data['weights'])):
        out=u.Vector(0,0,0)
        for n,w in weights.items():
            a,b=transforms[n];out+=b.transform_location(a.inverse_transform_location(u.Vector(*p)))*w
        u.GeometryScript_MeshEdits.set_vertex_position(dm,i,out,True)
    corrections=[]
    if correction_edits:
        corrections=[dict(path=str(Path(correction_edits).resolve()),sha256=digest(correction_edits))]
        _,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
        for edit in read(correction_edits):
            if 'position' in edit:u.GeometryScript_MeshEdits.set_vertex_position(dm,edit['vertex_id'],u.Vector(*edit['position']),True)
            if 'weights' in edit:
                _,ok=B.set_vertex_bone_weights(dm,edit['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=v) for n,v in edit['weights'].items()])
                if not ok:raise RuntimeError('Native correction vertex')
    for i in discarded:
        _,ok=u.GeometryScript_MeshEdits.delete_triangle_from_mesh(dm,i,True)
        if not ok:raise RuntimeError('Single-arm filtering failed')
    receipt=save_candidate(dm,source,destination,folder,corrections,binding=native,recompute_normals=True)
    receipt['native_source']=native_path;write(Path(folder)/'saved.json',receipt);return receipt

def collect_motion(manifest_path):
    import math
    manifest=read(manifest_path);folder=Path(manifest_path).parent/'motion';folder.mkdir(exist_ok=True)
    for profile,candidate in manifest['candidates'].items():
        mesh=u.load_asset(candidate['native_source'])
        _,native=source_snapshot(mesh);names=sorted({n for ref in candidate['snapshots'].values() for w in read(ref['path'])['weights'] for n in w})
        if not set(names).issubset(native['rest']):raise RuntimeError('Missing native bones '+profile)
        opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
        poses=[]
        for group,clips in manifest['actions'][profile].items():
            for path in clips:
                clip=u.load_asset(path)
                if not isinstance(clip,u.AnimSequence):raise RuntimeError('Expected animation '+path)
                duration=clip.get_play_length();count=max(2,math.ceil(duration*20)+1)
                for i in range(count):
                    time=duration*i/(count-1);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
                    poses.append(dict(group=group,clip=path,time=time,bones={n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
        write(folder/(profile+'.json'),dict(asset_sha256=candidate['asset_sha256'],native_source=candidate['native_source'],native_sha256=digest(asset_file(candidate['native_source'])),native_rest=native['rest'],clips={p:digest(asset_file(p)) for clips in manifest['actions'][profile].values() for p in clips},poses=poses))
