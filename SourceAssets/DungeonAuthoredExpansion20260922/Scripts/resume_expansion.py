"""Continue the owned map copy saved before the offline map-loading failure."""
import json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'Config/assembly.json').read_text(encoding='utf-8'))
MAN=json.loads((ROOT/'Authored/connections.json').read_text(encoding='utf-8'))
TARGET=CFG['target_map']
E=u.EditorAssetLibrary
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve running game')
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Open owned expansion map first')
receipt=json.loads((ROOT/'Receipts/assembly.json').read_text(encoding='utf-8'))
if receipt['stage']!='importing' or receipt['segments']:raise RuntimeError('Already advanced: preserve saved stage')
if any(a.get_actor_label().startswith(('DGN_A_','DGN_B_','DGN_Link_')) for a in AA.get_all_level_actors()):raise RuntimeError('Assembly already started: preserve work')
def write(): (ROOT/'Receipts/assembly.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
originals=list(AA.get_all_level_actors())
art=[a for a in originals if not isinstance(a,(u.PlayerStart,u.PostProcessVolume))]
for a in art:
    a.set_editor_property('tags',list(a.get_editor_property('tags'))+[u.Name('SourceLabel:'+a.get_actor_label())])
copies=AA.duplicate_actors(art,world,u.Vector(0,0,0))
if len(copies)!=len(art):raise RuntimeError('Actor duplication incomplete; preserve live edit')

def source_label(a):
    return next(str(t).split(':',1)[1] for t in a.get_editor_property('tags') if str(t).startswith('SourceLabel:'))

for segment,group in zip(CFG['segments'],[art,copies]):
    delta=u.Transform()
    delta.set_editor_property('translation',u.Vector(*segment['location_cm']))
    delta.set_editor_property('rotation',u.Rotator(pitch=0,yaw=segment['yaw'],roll=0).quaternion())
    roots=set(group)
    initial={a:a.get_actor_transform() for a in group}
    for a in group:
        label=source_label(a)
        if a.get_attach_parent_actor() not in roots:
            a.modify()
            a.set_actor_transform(u.MathLibrary.compose_transforms(initial[a],delta),False,True)
        a.set_actor_label('DGN_'+segment['id']+'_'+label.removeprefix('DGN_'))
        a.set_folder_path('DungeonAuthoredExpansion/'+segment['id']+'/'+str(a.get_folder_path()).removeprefix('DungeonAtmosphereV2/'))
        for item in MAN:
            if item['actor']!=label:continue
            entry='EntryEnd' in label
            if (entry and segment['open_entry']) or (not entry and segment['open_exit']):
                a.get_component_by_class(u.StaticMeshComponent).set_static_mesh(u.load_asset(receipt['assets'][item['name']]))
    receipt['segments'].append(dict(id=segment['id'],actors=len(group),location_cm=segment['location_cm'],yaw=segment['yaw']))
link=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*CFG['connection']['location_cm']))
link.set_actor_label('DGN_Link_A_B');link.set_folder_path('DungeonAuthoredExpansion/Connections')
link.static_mesh_component.set_static_mesh(u.load_asset(receipt['assets']['SM_Sample_ServiceLink']))
link.static_mesh_component.set_collision_profile_name('BlockAll')
lamp=AA.spawn_actor_from_class(u.PointLight,u.Vector(2400,-1600,294))
lamp.set_actor_label('DGN_Link_InspectionLight');lamp.set_folder_path('DungeonAuthoredExpansion/Connections')
c=lamp.get_component_by_class(u.PointLightComponent)
c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(360);c.set_light_color(u.LinearColor(1,.69,.4,1));c.set_attenuation_radius(260);c.set_cast_shadows(True)
receipt['stage']='assembled'
write()
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('External actor save failed')
if not ED.save_current_level():raise RuntimeError('Map save failed; preserve live work')
receipt['stage']='map_saved';write()
print('AUTHORED_EXPANSION_SAVED',TARGET,'two full authored segments, one service connection')
