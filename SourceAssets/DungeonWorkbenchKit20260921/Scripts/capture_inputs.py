from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Prototype'
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; finish the current run before assembly installation')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
w=UE.get_editor_world()
if not w or w.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label=a.get_actor_label()
    if not label.startswith(('DGN_Room_WS_','DGN_WSTools_','DGN_WSSculpt_','DGN_WSFab_','DGN_WSBench_')) and label!='DGN_AV2_LightFixtures':continue
    c=a.get_component_by_class(u.StaticMeshComponent);light=a.get_component_by_class(u.LightComponent)
    r=dict(label=label,class_path=a.get_class().get_path_name(),location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),hidden=a.get_editor_property('hidden'))
    if c and c.static_mesh:r.update(mesh=c.static_mesh.get_path_name(),materials=[m.get_path_name() if m else None for m in c.get_editor_property('override_materials')],visible=c.is_visible(),cast_shadow=c.get_editor_property('cast_shadow'),collision=str(c.get_collision_profile_name()))
    if light:
        props=['intensity','temperature','use_temperature','cast_shadows','attenuation_radius','intensity_units','light_color','source_radius','source_width','source_height','inner_cone_angle','outer_cone_angle','barn_door_angle','barn_door_length']
        values={}
        for prop in props:
            try:value=light.get_editor_property(prop)
            except Exception:continue
            if prop=='light_color':value=[value.r,value.g,value.b,value.a]
            elif prop=='intensity_units':value=str(value)
            values[prop]=value
        r.update(light=values,visible=light.is_visible())
    rows.append(r)
state=dict(map=TARGET,actors=rows,tests_run=False)
(ROOT/'Receipts/scene-inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
source=ROOT/'Sources/original-scene-inputs.json'
if not source.exists():source.write_text(json.dumps(state,indent=2),encoding='utf-8')
print('WORKBENCH_ASSEMBLY_INPUTS_CAPTURED',len(rows))
