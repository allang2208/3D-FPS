"""Read the three existing halls before their requested lighting revision."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP')
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);previous=editor.get_editor_world()
previous=previous.get_path_name().split('.')[0] if previous else None
result={}
for name in ('L_ReceptionHall_Subject','L_FacilityTransit_Subject','L_FacilityTransit_Alternate_Subject'):
    path='/Game/GameMaps/Design/'+name
    world=u.EditorLoadingAndSavingUtils.load_map(path)
    if not world:raise RuntimeError('Missing existing hall '+path)
    data=dict(lights=[],postprocess=[],diffusers=[]);result[path]=data
    for a in AA.get_all_level_actors():
        label=a.get_actor_label()
        for c in a.get_components_by_class(u.LightComponent):
            p=a.get_actor_location()
            d=dict(label=label,type=c.get_class().get_name(),position=[p.x,p.y,p.z],intensity=c.get_editor_property('intensity'))
            if isinstance(c,u.LocalLightComponent):
                d['radius']=c.get_editor_property('attenuation_radius')
                d['indirect']=c.get_editor_property('indirect_lighting_intensity')
            data['lights'].append(d)
        if isinstance(a,u.PostProcessVolume):
            s=a.get_editor_property('settings')
            data['postprocess'].append(dict(label=label,unbound=a.unbound,priority=a.priority,
                values={k:s.get_editor_property(k) for k in ('auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','indirect_lighting_intensity','bloom_intensity')}))
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if c.static_mesh and ('Diffuser' in c.static_mesh.get_name() or any('Glow' in str(c.get_material(i)) for i in range(c.get_num_materials()))):
                data['diffusers'].append(dict(label=label,mesh=c.static_mesh.get_path_name(),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
(ROOT/'Config/before.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
if not commandlet and previous:u.EditorLoadingAndSavingUtils.load_map(previous)
print('HALL_LIGHTING_SOURCE_READ',[(k,len(v['lights']),len(v['diffusers'])) for k,v in result.items()])
