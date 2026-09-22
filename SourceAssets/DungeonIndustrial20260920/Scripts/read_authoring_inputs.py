"""Read only the inputs needed to author the approved dungeon slice. No test/PIE."""
import unreal as u
import json
from pathlib import Path

root = Path('D:/FPS3D/FPSGAME')
names = ['SM_Catwalk_Floor_4x2M', 'SM_Catwalk_Stairs_2M',
         'SM_Catwalk_Floor_Railing_2M', 'SM_Column_Small_5M',
         'SM_Wall_Panel_Beams_ElectricalBox_4x2M', 'SM_Wall_Vent_Medium',
         'SM_Beam_4M', 'SM_Crate_Metal', 'SM_Door']
paths = [p for p in (root/'Content/SD_Art/Industrial_Infrastructure').rglob('SM_*.uasset')
         if p.stem in names or ('Column' in p.stem and '5M' in p.stem)]
out = {'assets': {}}
for p in paths:
    path = '/Game/' + p.relative_to(root/'Content').with_suffix('').as_posix()
    m = u.load_asset(path)
    if not m:
        continue
    b = m.get_bounds()
    out['assets'][p.stem] = {'path': path, 'origin': list(b.origin.to_tuple()),
        'extent': list(b.box_extent.to_tuple()),
        'materials': [str(s.material_interface.get_path_name()) if s.material_interface else None
                      for s in m.get_editor_property('static_materials')]}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
out['world'] = world.get_path_name() if world else None
out['dirty_maps'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
out['game_world'] = str(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())
out['api'] = {}
for cls, funcs in [(u.ModelingService, ['create_mesh', 'append_box', 'append_cylinder',
    'append_torus', 'append_mesh', 'project_uv', 'save_mesh_to_static_mesh', 'set_asset_materials',
    'bevel_polygroups', 'recompute_normals']),
    (u.Actor, ['add_component_by_class', 'add_instance_component']),
    (u.LevelEditorSubsystem, ['save_current_level_as']),
    (u.EditorLoadingAndSavingUtils, ['save_map'])]:
    for f in funcs:
        out['api'][cls.__name__+'.'+f] = getattr(getattr(cls, f, None), '__doc__', None)
if world and 'Dungeon' in world.get_name():
    out['current_actors'] = [(a.get_actor_label(), str(a.get_folder_path()))
        for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()]
path = root/'SourceAssets/DungeonIndustrial20260920/Receipts/authoring-inputs.json'
path.write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=2))
