import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
mesh=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10')
out={'pie':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),
 'asset':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),
 'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials],
 'dirty':[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
for name in ['get_bone_weights','get_vertex_bone_weights','get_bone_info','get_all_bones_info']:
 f=getattr(u.GeometryScript_BoneWeights,name,None)
 if f:out[name]=f.__doc__
out['sha256']=hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest()
(O/'current.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
