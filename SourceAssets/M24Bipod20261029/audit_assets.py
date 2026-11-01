"""Read saved source and compressed M24 bipod animations in a fresh UE process."""
import unreal as u, json, gzip, math
from pathlib import Path
O=Path(__file__).resolve().parent;R=O/'Review';R.mkdir(exist_ok=True)
with gzip.open(O/'authored.json.gz','rt') as f:auth=json.load(f)
mesh=u.load_asset(auth['mesh']);profile=u.load_asset('/Game/Weapons/M24/Bipod20261029/DA_M24_Bipod')
clips=profile.get_editor_property('clips');names=auth['names'];report={'clips':{},'assets':[]}
def pack(tr):
 p,q,s=tr.translation,tr.rotation,tr.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
out={'names':names,'rate':240,'clips':{}}
for index,family in enumerate(('base','mag10')):
 a=clips[index].get_editor_property('base');expected='/Game/Weapons/M24/Bipod20261029/A_M24_Bipod_'+family
 if not a.get_path_name().startswith(expected):raise RuntimeError('Wrong magazine clip '+family)
 settings=[]
 for mode in (u.AnimDataEvalType.SOURCE,u.AnimDataEvalType.COMPRESSED):
  opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=mode;settings.append(opt)
 rows=[];max_pos=max_rot=max_scale=0.;position_bone='';rotation_bone=''
 for i in range(round(a.get_play_length()*240)+1):
  t=i/240.;poses=[u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt) for opt in settings]
  pair=[[pack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)) for n in names] for p in poses]
  rows.append(pair[1])
  for bone,av,bv in zip(names,*pair):
   pos=math.dist(av[:3],bv[:3]);dot=abs(sum(x*y for x,y in zip(av[3:7],bv[3:7])))/math.sqrt(sum(x*x for x in av[3:7])*sum(x*x for x in bv[3:7]))
   rot=math.degrees(2*math.acos(min(1,dot)))
   if pos>max_pos:max_pos=pos;position_bone=bone
   if rot>max_rot:max_rot=rot;rotation_bone=bone
   max_scale=max(max_scale,max(abs(x-y) for x,y in zip(av[7:],bv[7:])))
 out['clips'][family]={'frames':rows}
 report['clips'][family]={'path':a.get_path_name(),'duration':a.get_play_length(),'samples':len(rows),'source_compressed_max_position':max_pos,'position_bone':position_bone,'source_compressed_max_rotation_degrees':max_rot,'rotation_bone':rotation_bone,'source_compressed_max_scale':max_scale}
for name in ('SM_M24_Bipod_Base','SM_M24_Bipod_LegA','SM_M24_Bipod_LegB'):
 a=u.load_asset('/Game/Weapons/M24/Bipod20261029/'+name)
 if not a:raise RuntimeError('Missing '+name)
 report['assets'].append({'name':name,'bounds_cm':list(a.get_bounds().box_extent.to_tuple()),'materials':[s.material_interface.get_path_name() for s in a.static_materials]})
with gzip.open(R/'compressed.json.gz','wt') as f:json.dump(out,f)
(R/'asset_readback.json').write_text(json.dumps(report,indent=2));print('M24_BIPOD_ASSET_READBACK',json.dumps(report),flush=True)
