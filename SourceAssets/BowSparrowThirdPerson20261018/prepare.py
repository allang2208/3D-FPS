"""Read current bow contacts and retarget licensed Sparrow takes to Jason.

Production inputs and new isolated packages only; no gameplay or rendering.
"""
import gzip, hashlib, json, math
from pathlib import Path
import unreal as u

O=Path(__file__).parent; ROOT=O.parents[1]
DEST='/Game/Characters/JasonPlayer20261003/BowSparrow20261018'
BASE='/Game/ParagonSparrow/Characters/Heroes/Sparrow'
lib=u.EditorAssetLibrary; at=u.AssetToolsHelpers.get_asset_tools()
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
bow=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8-sig'))['bow_dark']
source=u.load_asset(BASE+'/Meshes/Sparrow');target=u.load_asset(cfg['body_mesh'])
native=u.load_asset(bow['bow_viewmodel'])
selected=['idle','Travel_Mode_Idle_BowDown','RMB_Drawback','RMB_Loop','RMB_Fire','Primary_Fire_Slow']

def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def write(name,value):
    with gzip.open(O/name,'wt',encoding='utf-8') as f:json.dump(value,f,separators=(',',':'))
def skeleton(mesh):
    ref=mesh.skeleton.get_reference_pose()
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(mesh)
    parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]
    return dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,parents=parents,
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names])
def sample(mesh,clip,names):
    if not clip:raise RuntimeError('Missing requested animation')
    length=clip.get_play_length();count=max(1,round(length*30))
    times=[length*i/count for i in range(count+1)]
    rows=[[pack(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,time,False,mesh)] for time in times]
    return dict(asset=clip.get_path_name(),duration=length,times=times,frames=rows)
def save(a):
    if isinstance(a,u.AnimSequence) and not u.WeaponAnimationAuthoring.finalize_authored_animation(a):
        raise RuntimeError('Finalize failed '+a.get_path_name())
    if not lib.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def create(name,cls,factory):
    path=DEST+'/Rig/'+name
    return u.load_asset(path) if lib.does_asset_exist(path) else at.create_asset(name,DEST+'/Rig',cls,factory)

src=skeleton(source);src['clips']={}
for name in selected:
    src['clips'][name]=sample(source,u.load_asset(BASE+'/Animations/'+name),src['names'])
    print('SPARROW_SOURCE',name,src['clips'][name]['duration'],flush=True)
write('source.json.gz',src)
equipment=skeleton(native);equipment['clips']={};equipment['settings']=bow
for role in ('Idle','Draw','Hold','Release','Ready'):
    equipment['clips'][role]=sample(native,u.load_asset(bow['bow_animation_prefix']+role),equipment['names'])
write('equipment.json.gz',equipment)

ik=create('IK_Sparrow_Bow',u.IKRigDefinition,u.IKRigDefinitionFactory())
c=u.IKRigController.get_controller(ik);c.set_skeletal_mesh(source);c.set_retarget_root('pelvis')
names=src['names'];spines=[n for n in names if n.startswith('spine_') and n[-2:].isdigit()]
necks=[n for n in names if n.startswith('neck_') and n[-2:].isdigit()]
chains={'Spine':(spines[0],spines[-1]),'Head':('head','head')}
if necks:chains['Neck']=(necks[0],necks[-1])
for side in ('l','r'):
    for label,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
        a,b=start+'_'+side,end+'_'+side
        if a in names and b in names:chains[label+'_'+side]=(a,b)
    for digit in ('thumb','index','middle','ring','pinky'):
        chains[digit+'_'+side]=(digit+'_01_'+side,digit+'_03_'+side)
existing={str(ch.chain_name) for ch in c.get_retarget_chains()}
for label,(a,b) in chains.items():
    if label not in existing:c.add_retarget_chain(label,a,b,'')
save(ik)
rtg=create('RTG_Sparrow_Jason_Bow',u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,ik)
c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,u.load_asset('/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/IK_Jason_Sword'))
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if c.get_num_retarget_ops()==0:c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('Jason_Sparrow_Aligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET);c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
pending=[n for n in selected if not lib.does_asset_exist(DEST+'/Retargeted/J_Sparrow_'+n)]
if pending:
    p=u.IKRetargetBatchOperationInputs();p.assets_to_retarget=[lib.find_asset_data(src['clips'][n]['asset']) for n in pending]
    p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg
    p.prefix='J_Sparrow_';p.target_path=DEST+'/Retargeted';p.include_referenced_assets=False;p.overwrite_existing_files=False
    u.IKRetargetBatchOperation.run_batch_retarget(p)
result=skeleton(target);result['clips']={}
for name in selected:
    clip=u.load_asset(DEST+'/Retargeted/J_Sparrow_'+name)
    if not clip:raise RuntimeError('Retarget did not produce '+name)
    clip.set_preview_skeletal_mesh(target);save(clip)
    result['clips'][name]=sample(target,clip,result['names'])
    print('SPARROW_RETARGET',name,flush=True)
result['neutral']=sample(target,u.load_asset(cfg['clips']['Unarmed.Idle']),result['names'])
result['pose_scale']=cfg['pose_scale'];write('retargeted.json.gz',result)

# Read target skin for contact fitting and arm/torso clearance during authoring.
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(target,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read target skin')
_,pv,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(pv)
_,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
_,bones=B.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones}
skin={'positions':[[v.x,v.y,v.z] for v in vs],'triangles':[[t.x,t.y,t.z] for t in ts],
      'rest':{str(b.name):pack(b.world_transform) for b in bones},'weights':[]}
for i in range(len(vs)):
    _,ws,valid=B.get_vertex_bone_weights(dm,i)
    if not valid:raise RuntimeError('Invalid target vertex weights')
    skin['weights'].append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
write('skin.json.gz',skin)
(O/'prepared.json').write_text(json.dumps({'clips':{n:c['asset'] for n,c in result['clips'].items()},'skin_vertices':len(vs),'source_url':'https://www.fab.com/listings/7d76ddf0-d9ce-4d00-939e-d72793534d01','game_run':False},indent=2))
print('SPARROW_BOW_INPUTS_SAVED',flush=True)
