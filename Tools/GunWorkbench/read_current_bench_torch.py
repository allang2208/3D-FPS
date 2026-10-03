"""Read current mesh identity and torch attachment for the reported scene issue."""
import json,datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchLayoutDiagnosis20260928')
ROOT.mkdir(parents=True,exist_ok=True)
def path(o):return o.get_path_name() if o else None
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=sub.get_game_world() or sub.get_editor_world()
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entries=[e for e in palette.get_editor_property('components') if str(e.get_editor_property('id'))=='gun_workbench_table']
result={'world':path(world),'palette':[],'benches':[],'torches':[]}
for entry in entries:
    mesh=entry.get_editor_property('mesh')
    result['palette'].append({'mesh':path(mesh),'bounds':str(mesh.get_bounds()),'source':list(mesh.get_editor_property('asset_import_data').extract_filenames()),
        'footprint':str(entry.get_editor_property('footprint')),'pivot_offset':str(entry.get_editor_property('pivot_offset_cm')),
        'materials':[{'slot':str(s.material_slot_name),'asset':path(s.material_interface)} for s in mesh.get_editor_property('static_materials')]})
pawn=u.GameplayStatics.get_player_pawn(world,0)
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    kind=actor.get_class().get_name()
    if kind=='BronzeTorch':
        parent=actor.get_attach_parent_actor()
        result['torches'].append({'actor':path(actor),'parent':path(parent),'owner':path(actor.get_owner()),'transform':str(actor.get_actor_transform()),
            'relative_location':str(actor.get_editor_property('root_component').get_editor_property('relative_location')),
            'relative_rotation':str(actor.get_editor_property('root_component').get_editor_property('relative_rotation')),
            'distance_cm':actor.get_distance_to(pawn) if pawn else None})
    if kind not in ('VoxelBuildPrefabActor','StaticMeshActor'):continue
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh
        if not mesh or 'GunWorkbench' not in path(mesh):continue
        result['benches'].append({'actor':path(actor),'mesh':path(mesh),'transform':str(component.get_world_transform()),
            'source':list(mesh.get_editor_property('asset_import_data').extract_filenames()),'bounds':str(mesh.get_bounds()),
            'distance_cm':actor.get_distance_to(pawn) if pawn else None,
            'materials':[path(component.get_material(i)) for i in range(component.get_num_materials())]})
for key in ('benches','torches'):result[key].sort(key=lambda e:e['distance_cm'] or 0)
out=ROOT/('state-'+datetime.datetime.now().strftime('%H%M%S')+'.json')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('BENCH_TORCH_STATE '+json.dumps({'file':str(out),'world':result['world'],'palette_mesh':[e['mesh'] for e in result['palette']],
    'benches':result['benches'][:2],'torches':result['torches'][:3]},ensure_ascii=False))
