"""Read the user's existing paused pus actor without advancing the game."""
import json
from pathlib import Path
import unreal as u

world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
actors=u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Script/FPSGAME.FatZombiePusPool'))
records=[]
for a in actors:
    c=a.get_editor_property('surface')
    mesh=c.get_dynamic_mesh()
    m=c.get_material(0)
    row={'actor':a.get_path_name(),'mesh':mesh.get_path_name(), 'triangles':mesh.get_triangle_count(),
         'material':m.get_path_name() if m else None, 'material_count':c.get_num_materials(),
         'mesh_methods':[s for s in dir(mesh) if 'color' in s or 'triangle' in s or 'vert' in s],
         'geometry_libraries':[s for s in dir(u) if 'MeshVertexColor' in s or 'MeshQuery' in s]}
    if m:
        row['visibility']=m.get_scalar_parameter_value('Visibility')
        row['dryness']=m.get_scalar_parameter_value('Dryness')
    records.append(row)
out=Path('D:/FPS3D/FPSGAME/Saved/FatZombiePusVisibility/live_mesh.json')
out.write_text(json.dumps(records,indent=2),encoding='utf-8')
print('FAT_PUS_PAUSED_MESH_RECORDED')
