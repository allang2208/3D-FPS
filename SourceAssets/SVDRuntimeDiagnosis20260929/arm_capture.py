import unreal as u,json,time
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDRuntimeDiagnosis20260929/captures');R.mkdir(exist_ok=True)
try:u.unregister_slate_post_tick_callback(_svd_capture_handle)
except:pass
_svd_started=time.monotonic();_svd_last=0.;_svd_counts={'ads':0,'reload':0};_svd_aim_since=None

def _svd_tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def _svd_tick(dt):
 global _svd_last,_svd_aim_since
 now=time.monotonic()
 if now-_svd_started>120 or (_svd_counts['ads']>=2 and _svd_counts['reload']>=10):
  u.unregister_slate_post_tick_callback(_svd_capture_handle);print('SVD_CAPTURE_STOP',_svd_counts);return
 if now-_svd_last<.5:return
 w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
 if not w:return
 aa=[a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_class().get_name()=='FPSGAMECharacter']
 if not aa:return
 a=aa[0];aim=a.is_aiming();reload=a.is_reloading()
 if aim and _svd_aim_since is None:_svd_aim_since=now
 if not aim:_svd_aim_since=None
 kind='ads' if aim and now-_svd_aim_since>.7 else 'reload' if reload else None
 if not kind or _svd_counts[kind]>=(2 if kind=='ads' else 10):return
 comps=a.get_components_by_class(u.SkeletalMeshComponent);src=next(c for c in comps if c.get_name()=='AKMViewmodel')
 if 'SVD' not in src.get_skeletal_mesh_asset().get_path_name():return
 cam=a.get_components_by_class(u.CameraComponent)[0];idx=_svd_counts[kind];_svd_counts[kind]+=1;_svd_last=now
 d={'kind':kind,'aiming':aim,'reloading':reload,'camera':_svd_tr(cam.get_world_transform()),'source':_svd_tr(src.get_world_transform()),'fov':cam.get_editor_property('field_of_view'),'bones':{str(n):_svd_tr(src.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in src.get_all_socket_names()},'components':[]}
 for c in comps:
  if c!=src and c.get_editor_property('leader_pose_component')!=src:continue
  d['components'].append({'name':c.get_name(),'mesh':c.get_skeletal_mesh_asset().get_path_name(),'lod':c.get_predicted_lod_level(),'visible':c.is_visible()})
 (R/(kind+str(idx)+'.json')).write_text(json.dumps(d))
 u.SystemLibrary.execute_console_command(w,'HighResShot 1 filename="'+str(R/(kind+str(idx)+'.png')).replace('\\','/')+'"')
 print('SVD_CAPTURE',kind,idx)
_svd_capture_handle=u.register_slate_post_tick_callback(_svd_tick)
print('SVD_CAPTURE_ARMED_120S')
