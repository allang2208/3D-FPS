from pathlib import Path
import json,unreal as u
root=Path('D:/FPS3D/FPSGAME')
base='/Game/WorldGeneration/TemperateHills'
da=u.load_asset(base+'/DA_TemperateHillsStreaming')
report={'palette':{},'world':None,'nearby_instances':{}}
for prop in ['grass','grass_accents','river_ground_cover','river_bank_grasses','river_understory','forest_ferns']:
    try: meshes=da.get_editor_property(prop)
    except Exception: continue
    rows=[]
    for mesh in meshes:
        if hasattr(mesh,'get_bounding_box'):
            box=mesh.get_bounding_box()
            size=box.max-box.min
            rows.append([mesh.get_name(),[round(v,1) for v in (size.x,size.y,size.z)]])
    report['palette'][prop]=rows
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world and world.get_name().endswith('TemperateHills_Initial'):
    report['world']=world.get_name()
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    player=pawn.get_actor_location() if pawn else u.Vector(-12100,8700,5900)
    report['player_xyz_cm']=[player.x,player.y,player.z]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.PCGPartitionActor):
        for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if not mesh:continue
            count=c.get_instance_count()
            if not count:continue
            name=mesh.get_name()
            if name not in report['nearby_instances']:report['nearby_instances'][name]=[0,0]
            totals=report['nearby_instances'][name];totals[0]+=count
            lo=player-u.Vector(2200,2200,1200);hi=player+u.Vector(2200,2200,1200)
            totals[1]+=len(c.get_instances_overlapping_box(u.Box(min=lo,max=hi,is_valid=1),True))
(root/'SourceAssets/HillsRainforestCarpet20261111/Receipts/design-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
