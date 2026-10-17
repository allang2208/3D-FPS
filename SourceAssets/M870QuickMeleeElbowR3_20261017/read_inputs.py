"""Freeze the currently installed donor and target poses for melee authoring."""
import gzip, hashlib, json
from pathlib import Path
import unreal as u

O=Path(__file__).parent; P=O.parents[1]; S=O.parent
families=('vertical','canted','prism','angled')
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def load(path):
    obj=u.load_asset(path)
    if not obj: raise RuntimeError('Missing authoring input '+path)
    return obj
def clip_row(clip,mesh,names,times):
    rows=[]
    for t in times:
        poses=u.AnimationLibrary.get_bone_poses_for_time(clip,names,t,False,mesh)
        rows.append({n:pack(pose) for n,pose in zip(names,poses)})
    return dict(path=clip.get_path_name(),duration=clip.get_play_length(),times=times,rows=rows)
def profile_row(asset):
    return dict(path=asset.get_path_name(),family=str(asset.get_editor_property('family')),clips=[
        dict(base=c.get_editor_property('base').get_path_name(),duration=float(c.get_editor_property('duration')),
             retained=c.get_editor_property('retained').get_path_name() if c.get_editor_property('retained') else None,
             tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),
                          values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')])
        for c in asset.get_editor_property('clips')])

old=json.loads((S/'Super90QuickMelee20261008/LeftArmR5/inputs.json').read_text())
with gzip.open(S/'M870CommonFurniture20261016/Inputs/native_geometry.json.gz','rt') as f: native=json.load(f)
specs={
 'super90':dict(mesh='/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',root='/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_',
                parents=old['parents'],profiles='/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'),
 'm870':dict(mesh='/Game/Weapons/M870/Tactical20261015/SK_M870_V7',root='/Game/Weapons/M870/Tactical20261015/Animations/A_M870_',
             parents=native['parents'],profiles='/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_')}
data=dict(fps=240,source_mode='Sequence data-model tracks via AnimationLibrary, root motion disabled',weapons={},runtime_tested=False)
ruler=load('/Game/Weapons/M4ContactImpactFinal/A_AKM_idle')
data['ruler_world']={}
for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight'):
    chain=u.AnimationLibrary.find_bone_path_to_root(ruler,n)
    locals=u.AnimationLibrary.get_bone_poses_for_time(ruler,chain,0.,False)
    component=u.Transform()
    for local in locals:component=component.multiply(local)
    data['ruler_world'][n]=pack(component)
for key,spec in specs.items():
    mesh=load(spec['mesh']); idle=load(spec['root']+'idle'); melee=load(spec['root']+'quick_melee')
    names=list(spec['parents']);spec['parents']={n:p if p in names else None for n,p in spec['parents'].items()};mod=u.SkeletonModifier()
    if not mod.set_skeletal_mesh(mesh): raise RuntimeError('Cannot read native skeleton '+key)
    frames=round(melee.get_play_length()*data['fps']); times=[i/data['fps'] for i in range(frames+1)]
    row=dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,parents=spec['parents'],
             rest={n:pack(mod.get_bone_transform(n,True)) for n in names},
             idle=clip_row(idle,mesh,names,[0.]),melee=clip_row(melee,mesh,names,times),
             profiles={f:profile_row(load(spec['profiles']+f)) for f in families})
    curve='Super90MeleeArmAuthored'
    if u.AnimationLibrary.does_curve_exist(melee,curve,u.RawCurveTrackTypes.RCT_FLOAT):
        ts,vs=u.AnimationLibrary.get_float_keys(melee,curve);row['ownership_curve']=dict(name=curve,times=list(ts),values=list(vs))
    row['source_sha256']={}
    for path in [idle.get_path_name(),melee.get_path_name()]+[p['path'] for p in row['profiles'].values()]:
        physical=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        row['source_sha256'][path]=hashlib.sha256(physical.read_bytes()).hexdigest()
    data['weapons'][key]=row
    print('M870_MELEE_INPUT',key,frames+1,'samples',len(names),'bones')
data['pie_active_at_read']=bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())
with gzip.open(O/'inputs.json.gz','wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
print('M870_MELEE_INPUTS_SAVED; PIE_ACTIVE='+str(data['pie_active_at_read']))

# The unmodified viewmodel draws its baked bare arms. Read that actual surface,
# including open shoulder boundaries, as authoring constraints for this repair.
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
mesh=load(specs['m870']['mesh'])
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read M870 native skin')
_,pv,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
_,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
_,bones=B.get_all_bones_info(dm);bone_names={b.index:str(b.name) for b in bones}
skin=dict(path=mesh.get_path_name(),vertices=[[v.x,v.y,v.z] for v in ps],
          faces=[[t.x,t.y,t.z] for t in ts],rest={str(b.name):pack(b.world_transform) for b in bones},weights=[])
for vi in range(len(ps)):
    _,ws,ok=B.get_vertex_bone_weights(dm,vi)
    if not ok:raise RuntimeError('Cannot read M870 skin weights '+str(vi))
    skin['weights'].append({bone_names[w.bone_index]:w.weight for w in ws if w.weight>0})
with gzip.open(O/'native_skin.json.gz','wt',encoding='utf-8') as f:json.dump(skin,f,separators=(',',':'))
print('M870_RIGHT_ARM_SURFACE_READY',len(ps),'vertices')
