import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;root='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'
options=u.AnimPoseEvaluationOptions();options.set_editor_property('evaluation_type',u.AnimDataEvalType.COMPRESSED)
idle=u.load_asset(root+'idle');ref=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,options)
names=[n for n in u.AnimationLibrary.get_animation_track_names(idle) if str(n).startswith(('thumb','index','middle','ring','pinky'))]
out={'units':'Raw API translation values; inspect coordinate calibration before converting to physical units','samples':[],'coordinate_probe':{}}
def tr(t):return {'translation':list(t.translation.to_tuple()),'scale':list(t.scale3d.to_tuple()),'rotation':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]}
for n in ['root','WPN_root','WPN_SOCKET_Muzzle','WPN_RearSight','lowerarm_l','hand_l','ring_01_l','ring_02_l']:
 out['coordinate_probe'][n]={'local':tr(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)),'world':tr(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD))}
for clip,frames in {'equip':[64,80,94,100,116], 'reload':[128,180,220,240,252], 'reload_empty':[128,220,240,310,344,350,366]}.items():
 a=u.load_asset(root+clip)
 for f in frames:
  p=u.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,options);row=[]
  for n in names:
   x=u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL);y=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL);v=x.translation-y.translation
   row.append({'bone':str(n),'local_translation_delta_api_units':math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z)})
  out['samples'].append({'clip':clip,'frame':f,'finger_tracks':sorted(row,key=lambda r:r['local_translation_delta_api_units'],reverse=True)})
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular')
out['runtime_mesh']={'path':mesh.get_path_name(),'source':list(mesh.get_editor_property('asset_import_data').extract_filenames())}
(O/'ue_finger_tracks.json').write_text(json.dumps(out,indent=2));print('SVD_AUDIT_FINGER_TRACKS_DONE',flush=True)
