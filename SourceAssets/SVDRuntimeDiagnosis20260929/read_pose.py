import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDRuntimeDiagnosis20260929')
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_class().get_name()=='FPSGAMECharacter');comps=a.get_components_by_class(u.SkeletalMeshComponent);src=next(c for c in comps if c.get_name()=='AKMViewmodel');cam=a.get_components_by_class(u.CameraComponent)[0]
d={'camera':tr(cam.get_world_transform()),'source':tr(src.get_world_transform()),'bones':{str(n):tr(src.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in src.get_all_socket_names()},'components':[]}
anim=src.get_anim_instance();d['anim']={}
for prop in ['idle_clip','aim_clip','action_clip','action_time','action_alpha','aim_alpha']:
 try:
  v=anim.get_editor_property(prop);d['anim'][prop]=v.get_path_name() if isinstance(v,u.Object) else v
 except Exception as e:d['anim'][prop]=str(e)
for c in comps:
 if c!=src and c.get_editor_property('leader_pose_component')!=src:continue
 row={'name':c.get_name(),'methods':[n for n in dir(c) if 'lod' in n.lower() or 'section' in n.lower()]}
 try:row['lod']=c.get_predicted_lod_level()
 except:pass
 try:row['sections']=[[c.is_material_section_shown(i,lod) for i in range(c.get_num_materials())] for lod in range(3)]
 except Exception as e:row['section_error']=str(e)
 d['components'].append(row)
(R/'live-pose.json').write_text(json.dumps(d,indent=2));print(json.dumps({'anim':d['anim'],'components':d['components']}))
