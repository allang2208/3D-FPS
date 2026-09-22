"""Finish the already-saved authored rooms with the two generated masters only."""
from pathlib import Path
import json
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRoomInteriors20260921')
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
manifest=json.loads((ROOT/'Authored/room-manifest.json').read_text())
assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
receipt_path=ROOT/'Receipts/room-install.json';receipt=json.loads(receipt_path.read_text())
if receipt['stage'] not in ('authored_saved','finishing_generated','map_saved'):raise RuntimeError('Authoring stage is incomplete')
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve current play')
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Dungeon map is not current; preserve editor context')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
# The four source meshes corrected during this turn also dirty their external
# actor packages when reimported. Admit only those exact owned actor packages;
# any unrelated unsaved map state still stops this final save.
reimported_labels=['DGN_Room_WS_Toolboard','DGN_Room_RU_VaultBacking','DGN_Room_RU_VaultStones','DGN_Room_WS_TaskLight']
owned_dirty={actors[label].get_package().get_name() for label in reimported_labels if label in actors}
foreign_dirty=[p for p in dirty if p not in owned_dirty]
if foreign_dirty and receipt['stage']!='finishing_generated':raise RuntimeError('Unsaved map edits preserved: '+', '.join(foreign_dirty))
meshes={}
for p in manifest['new_generated']:
    mesh=u.load_asset(assets['generated'][p['id']])
    if not mesh:raise RuntimeError('Generated mesh unavailable: '+p['id'])
    meshes[p['id']]=mesh
for label in ['DGN_Room_WS_Workbench','DGN_Room_RU_OldMasonry']:
    if label not in actors:raise RuntimeError('Authored room input missing '+label)
receipt['stage']='finishing_generated';receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
placements=[]
for p in manifest['new_generated']:
    a=actors.get(p['label'])
    if not a:
        a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(p['label'])
        a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/'+('Workshop' if '_WS_' in p['label'] else 'Ruin'))
        a.set_editor_property('tags',[u.Name('DungeonRoomInteriors20260921')])
    mesh=meshes[p['id']];c=a.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll');c.set_editor_property('cast_shadow',True)
    b=mesh.get_bounds();s=p['scale'];r=u.Rotator(roll=0,pitch=0,yaw=p['yaw'])
    offset=u.Vector(b.origin.x*s[0],b.origin.y*s[1],(b.origin.z-b.box_extent.z)*s[2])
    point=u.Vector(p['cm'][0],-p['cm'][1],p['cm'][2])-u.MathLibrary.quat_rotate_vector(r.quaternion(),offset)
    a.set_actor_location_and_rotation(point,r,False,True);a.set_actor_scale3d(u.Vector(*s))
    placements.append({'actor':p['label'],'mesh':mesh.get_path_name(),'location_ue_cm':list(point.to_tuple()),'yaw':p['yaw'],'scale':s})
if not ED.save_current_level():raise RuntimeError('Final room save failed; live state retained')
receipt.update(stage='map_saved',generated_masters=len(meshes),generated_instances=len(placements),generated_placements=placements,
    source_dressed_blend=str(ROOT/'Authored/DungeonRooms_Dressed.blend'),tests_run=False,screenshots_taken=False)
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ROOM_INTERIORS_COMPLETE_SAVED',len(meshes),'generated masters;',len(placements),'instances')
