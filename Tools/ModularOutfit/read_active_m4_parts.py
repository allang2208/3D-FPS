import json
from pathlib import Path
import unreal as u
r=[]
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
p=u.GameplayStatics.get_player_character(w,0) if w else None
if p:
    for c in p.get_components_by_class(u.SkeletalMeshComponent):
        mesh=c.skeletal_mesh_asset
        if not mesh or not c.is_visible():continue
        row={'name':c.get_name(),'mesh':mesh.get_path_name(),'materials':[m.get_path_name() if m else '' for m in c.get_materials()],
             'shown':[[c.is_material_section_shown(i,l) for i in range(c.get_num_materials())] for l in range(3)]}
        for key in ('leader_pose_component','forced_lod_model','min_lod_model','relative_scale3d','relative_location'):
            try:row[key]=str(c.get_editor_property(key))
            except Exception:pass
        r.append(row)
Path('D:/FPS3D/FPSGAME/Saved/M4RefinedSkinRepair20260924/live-m4.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r))
