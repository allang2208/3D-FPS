"""Read current assets for native-V9 magazine contact authoring; never save assets."""
import json,gzip,hashlib
from pathlib import Path
import unreal as u

O=Path(__file__).parent;I=O/'Inputs';I.mkdir(exist_ok=True);P=Path(u.Paths.project_dir()).resolve()
ASSETS={
 'svch':'/Game/Weapons/SVCH/Replacement20261018/RealSights20261019/SK_SVCH_RealFoldingSights',
 'svd':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock',
 'arms':'/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7'}
manifest={}
def xf(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def digest(path):
 return hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def pick(result,cls):return next(v for v in result if isinstance(v,cls))
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
for key,path in ASSETS.items():
 candidates=[O.parent/'LeftBolt20261019/Inputs'/(key+'.json.gz'),O.parent/'LeftReload20261019/InputsAfter'/(key+'.json.gz'),O.parent/'LeftReload20261019/Inputs'/(key+'.json.gz')]
 cached=next((c for c in candidates if c.exists() and json.load(gzip.open(c,'rt')).get('sha256')==digest(path)),None)
 if cached:
  import shutil
  shutil.copy2(cached,I/(key+'.json.gz'));d=json.load(gzip.open(cached,'rt'));manifest[key]={'path':path,'sha256':d['sha256'],'vertices':len(d['positions'])};continue
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names())
 data={'path':path,'sha256':digest(path),'names':[str(n) for n in names],
       'parents':[str(mod.get_parent_name(n)) for n in names],
       'reference':[xf(mod.get_bone_transform(n,True)) for n in names],
       'materials':[str(s.material_slot_name) for s in mesh.get_editor_property('materials')], 'morph_names':[m.get_name() for m in mesh.get_editor_property('morph_targets')]}
 del mod
 dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
 result=G.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
 if u.GeometryScriptOutcomePins.SUCCESS not in result:raise RuntimeError('Cannot read '+path)
 positions=L.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,False),u.GeometryScriptVectorList))
 triangles=L.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,False),u.GeometryScriptTriangleList))
 slots=L.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
 data.update(positions=[[v.x,v.y,v.z] for v in positions],triangles=[[t.x,t.y,t.z] for t in triangles],material_ids=list(slots))
 _,bones=B.get_all_bones_info(dm);data['weight_bones']=[str(b.name) for b in sorted(bones,key=lambda b:b.index)]
 data['weights']=[]
 for v in range(len(positions)):
  _,ws,valid=B.get_vertex_bone_weights(dm,v)
  data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
 with gzip.open(I/(key+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
 manifest[key]={'path':path,'sha256':data['sha256'],'vertices':len(positions),'triangles':len(triangles),'materials':data['materials']}
 print('SVCH_RELOAD_INPUT',key,len(positions),len(triangles),data['materials'],flush=True)

profile_path='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip'
profile=u.load_asset(profile_path)
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
if profile_path in dirty:raise RuntimeError('Active profile has unsaved editor work; preserve it')
before={'family':str(profile.get_editor_property('family')),'clips':[]}
for clip in profile.get_editor_property('clips'):
 row={'base':clip.get_editor_property('base').get_path_name().split('.')[0],'duration':clip.get_editor_property('duration'),'tracks':[]}
 if clip.get_editor_property('retained'):raise RuntimeError('Unexpected retained clip; preserve current profile')
 for track in clip.get_editor_property('tracks'):
  row['tracks'].append({'bone':str(track.get_editor_property('bone')),'times':list(track.get_editor_property('times')),'values':list(track.get_editor_property('values'))})
 before['clips'].append(row)
(I/'profile_before.json').write_text(json.dumps(before,separators=(',',':')))
manifest['profile']={'path':profile_path,'sha256':digest(profile_path)}

mesh=u.load_asset(ASSETS['svd']);mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names())
motion={'names':[str(n) for n in names],'parents':[str(mod.get_parent_name(n)) for n in names],'clips':{}}
del mod
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
for kind in ('idle','aim','reload','reload_empty'):
 path='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'+kind
 seq=u.load_asset(path);duration=seq.get_play_length();frames=[]
 times=[0.] if kind in ('idle','aim') else [min(i/120,duration) for i in range(round(duration*120)+1)]
 for t in times:
  frames.append([xf(pose) for pose in u.AnimationLibrary.get_bone_poses_for_time(seq,names,t,False,mesh)])
 motion['clips'][kind]={'path':path,'duration':duration,'fps':120,'evaluation':'AnimationLibrary data model at time','times':times,'frames':frames,'sha256':digest(path)}
 print('SVCH_RELOAD_CLIP',kind,len(frames),flush=True)
with gzip.open(I/'motion.json.gz','wt',encoding='utf-8') as f:json.dump(motion,f,separators=(',',':'))
(I/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('SVCH_RELOAD_INPUTS_SAVED',flush=True)

"""Read existing game-world sight instances without changing gameplay state."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
worlds=[world] if world else []
for other in u.EditorLevelLibrary.get_pie_worlds(False):
    if all(other.get_path_name()!=w.get_path_name() for w in worlds): worlds.append(other)
def prop(obj,name):
    try: return obj.get_editor_property(name)
    except Exception: return None
def xyz(v): return [v.x,v.y,v.z]
def mesh_path(c):
    if isinstance(c,u.StaticMeshComponent):
        m=c.static_mesh
    elif isinstance(c,u.SkeletalMeshComponent):
        m=c.get_skeletal_mesh_asset()
    else: m=None
    return m.get_path_name() if m else None
def state(c):
    parent=c.get_attach_parent()
    p=prop(c,'hidden_in_game')
    return dict(path=c.get_path_name(),name=c.get_name(),type=c.get_class().get_name(),
        visible=c.is_visible(),hidden_in_game=p,mesh=mesh_path(c),
        parent=parent.get_path_name() if parent else None,socket=str(c.get_attach_socket_name()),
        world_location=xyz(c.get_world_location()),relative_location=xyz(prop(c,'relative_location')),
        relative_scale=xyz(prop(c,'relative_scale3d')))
report=dict(world=world.get_name() if world else None,worlds=[w.get_path_name() for w in worlds],pawns=[])
for w in worlds:
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        components=a.get_components_by_class(u.SceneComponent)
        has_sight=any((mesh_path(c) or '').startswith('/Game/Weapons/M4FoldingSights/') for c in components)
        if not has_sight and not any(c.get_name()=='AKMViewmodel' for c in components): continue
        row=dict(actor=a.get_path_name(),class_path=a.get_class().get_path_name(),actor_hidden=prop(a,'hidden'),components=[])
        for c in components:
            if isinstance(c,(u.StaticMeshComponent,u.SkeletalMeshComponent)) or 'Camera' in c.get_name():
                row['components'].append(state(c))
        report['pawns'].append(row)
(O/'runtime_magazines_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SIGHT_RESIDUAL_RUNTIME_READ world='+str(report['world'])+' pawns='+str(len(report['pawns'])))
