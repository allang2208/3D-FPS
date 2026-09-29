import unreal as u,json
from pathlib import Path
out={}
worlds=[]
try: worlds=list(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() for _ in [0])
except Exception as e: out['world_error']=str(e)
out['worlds']=[]
for w in worlds:
 if not w: continue
 row={'world':w.get_path_name(),'actors':[]}
 for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
  comps=a.get_components_by_class(u.SkeletalMeshComponent)
  cams=a.get_components_by_class(u.CameraComponent)
  if not comps and not cams: continue
  ar={'actor':a.get_path_name(),'components':[],'cameras':[]}
  for c in comps:
   cr={'name':c.get_name(),'location':str(c.get_world_location()),'rotation':str(c.get_world_rotation())}
   for p in ['skeletal_mesh','leader_pose_component','visible','hidden_in_game','only_owner_see','owner_no_see','forced_lod_model','predicted_lod_level','first_person_primitive_type']:
    try:
     v=c.get_editor_property(p);cr[p]=v.get_path_name() if isinstance(v,u.Object) else str(v)
    except Exception as e:cr[p]=str(e)
   cr['materials']=[m.get_path_name() if m else None for m in c.get_materials()]
   ar['components'].append(cr)
  for c in cams: ar['cameras'].append({'name':c.get_name(),'location':str(c.get_world_location()),'rotation':str(c.get_world_rotation())})
  row['actors'].append(ar)
 out['worlds'].append(row)
Path('D:/FPS3D/FPSGAME/SourceAssets/SVDRuntimeDiagnosis20260929/live.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
