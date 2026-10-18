"""Read the current M870 poses and shoulder surfaces for the requested repair."""
import gzip, hashlib, json, math
from pathlib import Path
import unreal as u

O=Path(__file__).parent; P=O.parents[1]
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def load(path):
    a=u.load_asset(path)
    if not a: raise RuntimeError('Missing '+path)
    return a
def digest(path):
    return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def write(name,data):
    with gzip.open(O/name,'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))

live={}
try:
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    pawn=u.GameplayStatics.get_player_character(world,0) if world else None
    if pawn:
        camera=pawn.get_component_by_class(u.CameraComponent)
        live['camera']=pack(camera.get_world_transform()) if camera else None
        live['camera_fov']=float(camera.field_of_view) if camera else None
        live['meshes']=[]
        for component in pawn.get_components_by_class(u.SkeletalMeshComponent):
            asset=component.get_editor_property('skeletal_mesh_asset')
            if not asset:continue
            if '/M870/' not in asset.get_path_name() and 'Chainmail' not in asset.get_path_name() and 'chainmail' not in asset.get_path_name():continue
            row={'name':component.get_name(),'mesh':asset.get_path_name(),'world':pack(component.get_world_transform()),
                 'bones':{n:pack(component.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l')}}
            anim=component.get_anim_instance()
            if anim:
                for name in ('action_clip','action_time','action_alpha','grip_profile'):
                    try:
                        value=anim.get_editor_property(name);row[name]=value.get_path_name() if isinstance(value,u.Object) else value
                    except Exception:pass
            live['meshes'].append(row)
except Exception as error:live['read_error']=str(error)
(O/'live_read.json').write_text(json.dumps(live,indent=2),encoding='utf-8')

config=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
native='/Game/Weapons/M870/Tactical20261015/SK_M870_V7'
profile=config['profiles'][native+'.SK_M870_V7']
paths={'native':native,'skin':profile['native_bare_skin'],
       'shirt':config['items']['ue_chainmail_shirt']['rig_meshes'][profile['rig_profile']]}
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
meshes={}
for key,path in paths.items():
    asset=load(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read mesh '+path)
    _,pv,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
    _,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    data={'path':asset.get_path_name(),'sha256':digest(path),
          'positions':[[v.x,v.y,v.z] for v in ps],'triangles':[[t.x,t.y,t.z] for t in ts],
          'rest':{str(b.name):pack(b.world_transform) for b in bones},
          'parents':{str(b.name):names.get(b.parent_index) for b in bones},'weights':[],
          'materials':[str(m.material_slot_name) for m in asset.materials],
          'triangle_materials':[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))]}
    for i in range(len(ps)):
        _,ws,ok=B.get_vertex_bone_weights(dm,i)
        if not ok:raise RuntimeError('Invalid weights '+key+':'+str(i))
        data['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    write(key+'.json.gz',data);meshes[key]=data
    print('M870_ROOT_MESH',key,len(ps),len(ts),flush=True)

mesh=load(native);names=list(meshes['native']['rest'])
root='/Game/Weapons/M870/Tactical20261015/Animations/A_M870_'
roles={role:root+role for role in ('idle','inspect','reload_continuous','reload_full','cycle')}
for state in ('normal','empty'):
    for count in range(1,8):roles[f'loader_{state}_{count}']=f'/Game/Weapons/M870/Speedloader20261016/Animations/A_M870_loader_{state}_{count}'
data={'fps':30,'source_mode':'AnimationLibrary data-model local transforms','names':names,
      'parents':meshes['native']['parents'],'clips':{},'profiles':{},'ruler':{}}
for role,path in roles.items():
    clip=load(path);duration=clip.get_play_length();count=max(1,math.ceil(duration*30))
    times=[duration*i/count for i in range(count+1)] if role!='idle' else [0.]
    rows=[[pack(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,time,False,mesh)] for time in times]
    data['clips'][role]={'path':clip.get_path_name(),'sha256':digest(path),'duration':duration,'times':times,'rows':rows}
    print('M870_ROOT_CLIP',role,len(times),flush=True)
for family in ('vertical','canted','prism','angled'):
    a=load('/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_'+family)
    data['profiles'][family]={'path':a.get_path_name(),'sha256':digest(a.get_path_name()),'clips':[
        {'base':c.get_editor_property('base').get_path_name(),'duration':float(c.get_editor_property('duration')),
         'retained':c.get_editor_property('retained').get_path_name() if c.get_editor_property('retained') else None,
         'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),
                    'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]}
        for c in a.get_editor_property('clips')]}
ruler=load('/Game/Weapons/M4ContactImpactFinal/A_AKM_idle')
for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight'):
    chain=u.AnimationLibrary.find_bone_path_to_root(ruler,n);world=u.Transform()
    for local in u.AnimationLibrary.get_bone_poses_for_time(ruler,chain,0.,False):world=world.multiply(local)
    data['ruler'][n]=pack(world)
write('poses.json.gz',data)
(O/'inputs_receipt.json').write_text(json.dumps({'meshes':{k:{'path':v['path'],'sha256':v['sha256']} for k,v in meshes.items()},
    'clips':len(roles),'profile_count':4,'saved_assets':False,'game_run':False},indent=2),encoding='utf-8')
print('M870_ROOT_INPUTS_COMPLETE',flush=True)
