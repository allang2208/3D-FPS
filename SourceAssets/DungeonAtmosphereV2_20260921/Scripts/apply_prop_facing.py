"""Point cabinet fronts and bay valves into their usable side-bay space."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world() or UE.get_editor_world().get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':
    raise RuntimeError('Dungeon editing context changed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
placements=json.loads((ROOT/'Receipts/placement-manifest.json').read_text())
for p in json.loads((ROOT/'layout.json').read_text())['props']:
    actor=actors['DGN_AV2_'+p['label']];r=u.Rotator(roll=0,pitch=0,yaw=p['yaw'])
    bounds=actor.static_mesh_component.static_mesh.get_bounds();s=p['scale'];x,y,z=p['cm']
    pivot=u.Vector(bounds.origin.x*s[0],bounds.origin.y*s[1],(bounds.origin.z-bounds.box_extent.z)*s[2])
    pos=u.Vector(x,-y,z)-u.MathLibrary.quat_rotate_vector(r.quaternion(),pivot)
    actor.set_actor_location_and_rotation(pos,r,False,True)
    for entry in placements:
        if entry['label']==p['label']:entry['yaw']=p['yaw'];entry['location_ue_cm']=list(pos.to_tuple())
statue=actors['DGN_AV2_Goddess_Candidate'];b=statue.static_mesh_component.static_mesh.get_bounds();s=statue.get_actor_scale3d()
anchor=json.loads((ROOT/'Authored/structure-manifest.json').read_text())['event_anchor_cm']
pos=u.Vector(anchor[0]-b.origin.x*s.x,-anchor[1]-b.origin.y*s.y,anchor[2]-(b.origin.z-b.box_extent.z)*s.z)
statue.set_actor_location_and_rotation(pos,u.Rotator(roll=0,pitch=0,yaw=0),False,True)
for entry in placements:
    if entry['label']=='Goddess_Candidate':entry['yaw']=0;entry['location_ue_cm']=list(pos.to_tuple())
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():raise RuntimeError('Cannot save final prop facing')
(ROOT/'Receipts/placement-manifest.json').write_text(json.dumps(placements,indent=2),encoding='utf-8')
print('V2_PROP_FACING_SAVED')
