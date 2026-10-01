"""Read the existing HK416 session only; never start PIE or change equipment."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'game_world_running':bool(w),'screenshot_requested':False,'components':[]}
if w:
    for actor in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        if actor.get_class().get_name()!='FPSGAMECharacter':continue
        body=next((c for c in actor.get_components_by_class(u.SkeletalMeshComponent) if c.get_name()=='AKMViewmodel'),None)
        mesh=body.get_skeletal_mesh_asset() if body else None
        if not mesh or '/Weapons/HK416/' not in mesh.get_path_name():continue
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            m=c.get_static_mesh()
            if m and '/HK416/' in m.get_path_name():
                report['components'].append({'mesh':m.get_path_name(),'visible':c.is_visible(),'effective_materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
        u.SystemLibrary.execute_console_command(w,'HighResShot 1 filename="D:/FPS3D/FPSGAME/SourceAssets/HK416AttachmentSurface20260930/live_after.png"')
        report['screenshot_requested']=True;break
(O/'current_presentation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
