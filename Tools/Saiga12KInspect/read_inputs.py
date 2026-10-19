"""Read the actual shared inspect, private grip layers and native left-hand skin."""
import unreal as u
import json
from pathlib import Path

O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KInspect20261018')
P=u.AnimPoseExtensions
E=u.EditorAssetLibrary
mesh=u.load_asset('/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny')
clip=u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_inspect')
idle=u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle')
opts=u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh=mesh
opts.evaluation_type=u.AnimDataEvalType.RAW
opts.incorporate_root_motion_into_pose=False
def pack(t):
    return [getattr(t.translation,c) for c in 'xyz']+[getattr(t.rotation,c) for c in 'xyzw']+[getattr(t.scale3d,c) for c in 'xyz']
pose=P.get_anim_pose_at_time(clip,0.,opts)
names=[str(n) for n in P.get_bone_names(pose)]
duration=clip.get_play_length()
R={'clip':clip.get_path_name(),'duration':duration,'sample_rate':60,'names':names,
   'reference':{n:pack(P.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names},'frames':[],'profiles':{}}
for i in range(round(duration*60)+1):
    time=min(i/60.,duration)
    pose=P.get_anim_pose_at_time(clip,time,opts)
    R['frames'].append({'time':time,'local':{n:pack(P.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
pose=P.get_anim_pose_at_time(idle,0.,opts)
R['idle']={n:pack(P.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}
for family in ('angled','vertical','canted','prism'):
    path='/Game/Weapons/Saiga12K/Common20261017/Profiles/DA_'+family
    profile=u.load_asset(path)
    clips=[]
    for c in profile.get_editor_property('clips'):
        base=c.get_editor_property('base');retained=c.get_editor_property('retained')
        clips.append({'base':base.get_path_name(),'duration':c.get_editor_property('duration'),'retained':retained.get_path_name() if retained else None,
          'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
    R['profiles'][family]={'path':path,'family':str(profile.get_editor_property('family')),'clips':clips}
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;BW=u.GeometryScript_BoneWeights;LS=u.GeometryScript_List
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not read actual native skin')
_,bones=BW.get_all_bones_info(dm)
R['bones']=[{'name':str(b.name),'parent':b.parent_index,'world':pack(b.world_transform)} for b in bones]
_,points,_=Q.get_all_vertex_positions(dm,False);points=list(LS.convert_vector_list_to_array(points))
_,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=list(LS.convert_triangle_list_to_array(triangles))
left={i for i,b in enumerate(bones) if str(b.name).endswith('_l') and any(x in str(b.name) for x in ('hand','thumb','index','middle','ring','pinky','lowerarm','upperarm','clavicle'))}
vertices={};tris=[]
for ti,t in enumerate(triangles):
    mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
    if str(mesh.materials[mid].material_slot_name).startswith('Saiga12K_'):continue
    ids=[t.x,t.y,t.z]
    for vi in ids:
        if vi in vertices:continue
        _,weights,valid=BW.get_vertex_bone_weights(dm,vi)
        ws=[[w.bone_index,w.weight] for w in weights if w.weight>0]
        if any(b in left for b,w in ws):vertices[vi]={'p':[getattr(points[vi],c) for c in 'xyz'],'w':ws}
    if all(vi in vertices for vi in ids):tris.append(ids)
R['skin']={'vertices':vertices,'triangles':tris}
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
R['editor']={'game_world':s.get_game_world().get_path_name() if s and s.get_game_world() else None,'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(O/'Inputs/runtime-source.json').write_text(json.dumps(R),encoding='utf-8')
print(json.dumps({'duration':duration,'frames':len(R['frames']),'bones':len(bones),'left_skin_vertices':len(vertices),'editor':R['editor'],'profiles':{f:[{'base':c['base'],'retained':c['retained'],'tracks':len(c['tracks'])} for c in p['clips'] if c['base'].endswith('_inspect')] for f,p in R['profiles'].items()}}))
