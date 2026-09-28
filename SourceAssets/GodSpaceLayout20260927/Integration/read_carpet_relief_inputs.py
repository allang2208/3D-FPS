"""Read the saved hub binding and source normal pixels for the carpet repair."""
import json
from pathlib import Path
import unreal as u

root=Path(__file__).parent
dest='/Game/Props/GodSpaceLayout20260927'
mesh=u.load_asset(dest+'/Meshes/SM_GodSpaceStructure')
report={'mesh_slots':[str(s.get_editor_property('material_interface')) for s in mesh.get_editor_property('static_materials')], 'actors':[], 'exports':[], 'texture_settings':{}}
for v in ['01','02']:
    for ch in ['N','R']:
        name='T_Carpet_'+v+'_'+ch
        tex=u.load_asset('/Game/SubstrateMaterials/Textures/02_Upholstery/Textiles/'+name)
        task=u.AssetExportTask();task.object=tex;task.filename=str(root/'CarpetSources'/(name+'.tga'))
        task.exporter=u.TextureExporterTGA();task.automated=True;task.prompt=False;task.replace_identical=True
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+name)
        report['exports'].append(task.filename)
        report['texture_settings'][name]={p:str(tex.get_editor_property(p)) for p in ['flip_green_channel','compression_settings','srgb']}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
worlds=[]
if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
    worlds.append(u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting'))
else:
    worlds=[editor.get_editor_world(),editor.get_game_world()]
for world in worlds:
    if not world:continue
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
        c=actor.static_mesh_component
        if c.static_mesh!=mesh:continue
        report['actors'].append({'world':world.get_path_name(),'actor':actor.get_path_name(),
            'location':str(actor.get_actor_location()),'rotation':str(actor.get_actor_rotation()),'scale':str(actor.get_actor_scale3d()),
            'materials':[str(c.get_material(i)) for i in range(c.get_num_materials())],
            'overrides':str(c.get_editor_property('override_materials')),
            'streaming_multiplier':c.get_editor_property('streaming_distance_multiplier')})
mat=u.load_asset(dest+'/Materials/M_GodSpaceNavyCarpet')
report['material']={p:str(mat.get_editor_property(p)) for p in ['shading_model','use_material_attributes','tangent_space_normal']}
report['uv_channel_data']=[str(s.get_editor_property('uv_channel_data')) for s in mesh.get_editor_property('static_materials')]
(root/'Receipts/carpet-relief-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CARPET_RELIEF_INPUTS '+json.dumps(report))
