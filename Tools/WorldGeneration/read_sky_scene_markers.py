"""Read sky meshes and floating labels from the two authored levels; no gameplay."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/Saved/HillsSkyMarkers20260915')
out.mkdir(parents=True,exist_ok=True)
report={'maps':{},'mesh':{}}
mesh=u.load_asset('/Engine/EngineSky/SM_SkySphere')
report['mesh']={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounds()),
                'materials':[str(x) for x in mesh.get_editor_property('static_materials')]}
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
for name in ('L_TemperateHills_Initial','DayNight_Lighting'):
    if not levels.load_level('/Game/GameMaps/'+name):raise RuntimeError('Cannot read '+name)
    rows=[]
    for a in actors.get_all_level_actors():
        texts=a.get_components_by_class(u.TextRenderComponent)
        meshes=a.get_components_by_class(u.StaticMeshComponent)
        special=any(s.lower() in (a.get_actor_label()+' '+a.get_class().get_name()).lower()
                    for s in ('sky','light','sphere','text','label','marker','debug','sign'))
        row={'label':a.get_actor_label(),'name':a.get_name(),'class':a.get_class().get_name(),
             'path':a.get_path_name(),'location':str(a.get_actor_location()),'texts':[],'meshes':[],'billboards':[]}
        for c in a.get_components_by_class(u.BillboardComponent):
            sprite=c.get_editor_property('sprite')
            row['billboards'].append({'name':c.get_name(),'sprite':sprite.get_path_name() if sprite else None,
                                     'visible':c.get_editor_property('visible'),'hidden':c.get_editor_property('hidden_in_game'),
                                     'editor_only':c.get_editor_property('is_editor_only')})
        for c in a.get_components_by_class(u.ArrowComponent):
            row['billboards'].append({'name':c.get_name(),'class':'Arrow','visible':c.get_editor_property('visible'),
                                     'hidden':c.get_editor_property('hidden_in_game'),'editor_only':c.get_editor_property('is_editor_only')})
        for t in texts:
            row['texts'].append({'component':t.get_name(),'text':str(t.get_editor_property('text')),
                                'location':str(t.get_world_location()),
                                'visible':t.get_editor_property('visible'),'hidden':t.get_editor_property('hidden_in_game'),
                                'color':str(t.get_editor_property('text_render_color'))})
        for m in meshes:
            sm=m.get_editor_property('static_mesh')
            if not sm:continue
            if special or any(s in sm.get_name().lower() for s in ('sky','sphere','marker')):
                row['meshes'].append({'component':m.get_name(),'mesh':sm.get_path_name(),
                                     'location':str(m.get_world_location()),'scale':str(m.get_world_scale()),
                                     'visible':m.get_editor_property('visible'),'hidden':m.get_editor_property('hidden_in_game'),
                                     'materials':[m.get_material(i).get_path_name() if m.get_material(i) else '' for i in range(m.get_num_materials())]})
        if texts or special or row['meshes'] or row['billboards']:rows.append(row)
    report['maps'][name]=rows
(out/'scene_sources.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SKY_SCENE_MARKERS_READ')
