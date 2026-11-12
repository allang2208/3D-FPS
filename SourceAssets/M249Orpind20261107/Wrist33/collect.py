"""Read current saved M249 geometry and compressed actions; no asset writes."""
from pathlib import Path
import unreal as u
import json, pickle, hashlib
r=Path(__file__).resolve().parent
project=r.parents[2]
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
pie='-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
if pie: raise RuntimeError('Existing PIE retained; stop this capture')
def tr(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def record(a):
    path=a.get_path_name().split('.')[0]
    if path in dirty: raise RuntimeError('Unsaved input retained: '+path)
    hashes[path]=hashlib.sha256((project/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
hashes={}
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');record(mesh)
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Geometry unavailable')
Q,B,L=u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
_,bones=B.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index)
_,positions,_=Q.get_all_vertex_positions(dm,False);_,triangles,_=Q.get_all_triangle_indices(dm,False)
vertices=[v.to_tuple() for v in L.convert_vector_list_to_array(positions)]
faces=[(v.x,v.y,v.z) for v in L.convert_triangle_list_to_array(triangles)]
weights=[]
for i in range(len(vertices)):
    _,raw,valid=B.get_vertex_bone_weights(dm,i)
    if not valid: raise RuntimeError('Missing weights')
    weights.append([(w.bone_index,w.weight) for w in raw if w.weight>0])
names=[str(b.name) for b in bones]
geo=dict(vertices=vertices,faces=faces,weights=weights,names=names,parents=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones],sections=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(faces))],slots=[str(s.material_slot_name) for s in mesh.materials])
pickle.dump(geo,open(r/'geometry.pkl','wb'))
d={k:geo[k] for k in ('names','parents','bind')};d.update(profiles={},clips={})
for family in ('base','vertical','angled','canted','prism'):
    path='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family
    asset=u.load_asset(path);record(asset);rows=[]
    for c in asset.get_editor_property('clips'):
        v=c.get_editor_property;retained=v('retained')
        rows.append(dict(base=v('base').get_path_name(),retained=retained.get_path_name() if retained else None,duration=v('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
    d['profiles'][family]=dict(asset=path,clips=rows)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
paths=sorted({c['base'] for p in d['profiles'].values() for c in p['clips']})
for path in paths:
    a=u.load_asset(path);record(a);duration=a.get_play_length()
    fps=60;count=round(duration*fps);times=[i*duration/max(count,1) for i in range(count+1)]
    frames=[]
    for time in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,opt)
        frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    d['clips'][a.get_path_name()]=dict(duration=duration,fps=fps,times=times,frames=frames)
    print('WRIST33_READ',a.get_name(),len(frames),flush=True)
pickle.dump(d,open(r/'current.pkl','wb'))
(r/'inputs.json').write_text(json.dumps(dict(pie=pie,dirty=dirty,hashes=hashes),indent=2))
print('WRIST33_CAPTURED',len(vertices),len(d['clips']),flush=True)
