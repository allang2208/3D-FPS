"""Read current reload curves and the accepted AKM grasp for scoped authoring."""
import json,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[2];S=O/'Sources';S.mkdir(exist_ok=True)
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def sha(a):return hashlib.sha256((P/'Content'/(a.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
out={'clips':{},'rigs':{}}
for rig,path in [('201','/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'),('akm','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')]:
 mesh=u.load_asset(path)
 dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 _,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm);ids={b.index:str(b.name) for b in rows}
 bones={str(b.name):dict(tr(b.world_transform),parent=ids.get(b.parent_index)) for b in rows}
 out['rigs'][rig]={'asset':path,'sha256':sha(path),'bones':bones}
 selected=[n for n in bones if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
 selected+=['WPN_root','WPN_SOCKET_Magazine','hand_r']
 for n in list(selected):
  par=bones[n]['parent']
  while par:
   if par not in selected:selected.append(par)
   par=bones[par]['parent']
 families=['base','vertical','canted','prism','angled'] if rig=='201' else ['base']
 for family in families:
  for key in ['reload','reload_empty']:
   asset=('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_'+key if family=='base' else f'/Game/Weapons/LMG201/Accessories22/Animations/{family}/A_LMG201_{family}_{key}') if rig=='201' else '/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_'+key
   clip=u.load_asset(asset);model=clip.get_editor_property('data_model_interface');count=model.get_number_of_keys();seconds=clip.get_play_length()
   opts=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE)
   rows=[]
   for i in range(count):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,seconds*i/max(1,count-1),opts)
    rows.append({n:{'local':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),'world':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))} for n in selected})
   label=rig+'_'+family+'_'+key;f=S/(label+'.json')
   info={'asset':asset,'sha256':sha(asset),'rig':rig,'family':family,'clip':key,'count':count,'seconds':seconds,'fps':[model.get_frame_rate().numerator,model.get_frame_rate().denominator],'file':str(f)}
   f.write_text(json.dumps(dict(info,poses=rows),separators=(',',':')));out['clips'][label]=info
   (O/'sources.json').write_text(json.dumps(out,indent=2));print('MAGAZINE24_SOURCE',label,count,flush=True)
print('MAGAZINE24_COLLECT_COMPLETE',flush=True)
