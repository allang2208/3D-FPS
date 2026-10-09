"""Read current editor/PIE lighting and lamp vertex coordinates. No asset writes."""
import json,runpy,traceback
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
P=runpy.run_path(str(ROOT/'profile.py'))
report=dict(worlds=[],meshes=[],materials=[],cvars={})
def path(x):return x.get_path_name() if x else None
def v(p):return [p.x,p.y,p.z]
for key in ('r.LightFunctionQuality','r.LightFunctionAtlas','r.Deferred.UsesLightFunctionAtlas',
            'r.MegaLights.Allow','r.MegaLights.Enable','r.ForwardShading','sg.ShadowQuality'):
    report['cvars'][key]=u.SystemLibrary.get_console_variable_int_value(key)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
for kind,world in [('editor',editor.get_editor_world()),('game',editor.get_game_world())]:
    if not world:continue
    entry=dict(kind=kind,path=path(world),time=u.GameplayStatics.get_time_seconds(world),lights=[],diffusers=[])
    report['worlds'].append(entry)
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        label=a.get_actor_label()
        if not label.startswith(('Reception_','FacilityTransit_')):continue
        light=a.get_component_by_class(u.PointLightComponent)
        if light:
            f=light.get_editor_property('light_function_material')
            entry['lights'].append(dict(label=label,intensity=light.intensity,location=v(a.get_actor_location()),
                function=path(f),visible=light.is_visible(),cast_shadows=light.cast_shadows,
                fade=light.light_function_fade_distance,disabled_brightness=light.disabled_brightness))
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if c.static_mesh and 'Diffuser' in c.static_mesh.get_name():
                entry['diffusers'].append(dict(label=label,mesh=path(c.static_mesh),location=v(c.get_world_location()),
                    scale=v(c.get_world_scale()),materials=[path(c.get_material(i)) for i in range(c.get_num_materials())]))
for group,folder,meshpath in [
    ('Reception','DungeonReceptionHall20261006','/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_LightDiffusers'),
    ('Transit','DungeonFacilityTransit20261007','/Game/Dungeons/FacilityTransit20261007/Meshes/SM_FT_Hall_Diffusers')]:
    m=u.load_asset(meshpath);entry=dict(group=group,path=meshpath,bounds=str(m.get_bounds()));report['meshes'].append(entry)
    try:
        vertices,triangles,normals,uvs,tangents=u.ProceduralMeshLibrary.get_section_from_static_mesh(m,0,0)
        entry['vertices']=len(vertices)
        entry['vertex_min']=[min(getattr(p,k) for p in vertices) for k in ('x','y','z')]
        entry['vertex_max']=[max(getattr(p,k) for p in vertices) for k in ('x','y','z')]
        cfg=json.loads((P['PROJECT']/'SourceAssets'/folder/'Config/layout.json').read_text('utf8'))
        entry['mask_hits']=[]
        for light in cfg['lights']:
            x,y,z=light['position_m'];z=z+.144 if group=='Reception' else 7.037 if light['type']=='spot' else z+.07
            hits=sum(abs(p.x-x*100)<155 and abs(p.y+y*100)<24 and abs(p.z-z*100)<19 for p in vertices)
            entry['mask_hits'].append(dict(id=light['id'],fault=light['fault'],phase=light['phase'],hits=hits))
            if light.get('light_function'):
                mi=u.load_asset(light['light_function'])
                report['materials'].append(dict(path=path(mi),parent=path(mi.parent),
                    params={k:u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,k) for k in ('Phase','Fault','Dead')}))
    except Exception:entry['error']=traceback.format_exc()
(ROOT/'Receipts/diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HALL_DIAGNOSIS_CAPTURED',[(w['kind'],w['path'],len(w['lights'])) for w in report['worlds']],report['meshes'])
