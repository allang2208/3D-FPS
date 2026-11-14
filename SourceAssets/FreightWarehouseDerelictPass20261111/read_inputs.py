"""Read the saved warehouse and native dust-layer graph for scoped authoring."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
L=u.MaterialEditingLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
report={'actors':[],'materials':{}}
def material(m):
    if not m:return None
    p=m.get_path_name()
    if p not in report['materials']:
        d={'base':m.get_base_material().get_path_name()}
        if isinstance(m,u.MaterialInstanceConstant):
            d['switches']={str(n):L.get_material_instance_static_switch_parameter_value(m,n) for n in L.get_static_switch_parameter_names(m)}
            d['scalars']={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)}
            d['textures']={str(n):(t.get_path_name() if (t:=L.get_material_instance_texture_parameter_value(m,n)) else None) for n in L.get_texture_parameter_names(m)}
        report['materials'][p]=d
    return p
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    p=a.get_actor_location()
    if not ('AbandonedCargoWarehouse' in [str(t) for t in a.tags] or (2100<p.x<5500 and -2400<p.y<600)):continue
    center,extent=a.get_actor_bounds(False)
    d={'name':a.get_name(),'label':a.get_actor_label(),'class':a.get_class().get_name(),'tags':[str(t) for t in a.tags],
       'position':list(p.to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple()),
       'center':list(center.to_tuple()),'extent':list(extent.to_tuple()),'components':[]}
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if c.static_mesh:d['components'].append({'name':c.get_name(),'mesh':c.static_mesh.get_path_name(),'materials':[material(c.get_material(i)) for i in range(c.get_num_materials())]})
    for c in a.get_components_by_class(u.DecalComponent):
        d['decal']={'material':material(c.get_decal_material()),'size':list(c.get_editor_property('decal_size').to_tuple())}
    report['actors'].append(d)
report['native_graph']=[]
for n in L.get_material_expressions(u.load_asset('/Game/UndergroundTunnel/Materials/Master/M_Env_Basic')):
    d={'name':n.get_name(),'class':n.get_class().get_name()}
    for k in ('parameter_name','material_function','default_value'):
        try:
            value=n.get_editor_property(k);d[k]=value.get_path_name() if isinstance(value,u.Object) else str(value)
        except Exception:pass
    d['inputs']=[v.get_name() if v else None for v in L.get_inputs_for_material_expression(u.load_asset('/Game/UndergroundTunnel/Materials/Master/M_Env_Basic'),n)]
    report['native_graph'].append(d)
report['extra_meshes']={}
for p in ['/Game/Dungeons/FacilityQuixel20261108/WoodenCableReel/Meshes/SM_WoodenCableReel',
          '/Game/Dungeons/FacilityQuixel20261108/RustyPipeJoint/Meshes/SM_RustyPipeJoint',
          '/Game/Dungeons/FacilityQuixel20261108/ConcreteRubble/Meshes/SM_ConcreteRubble']:
    m=u.load_asset(p);b=m.get_bounding_box()
    report['extra_meshes'][m.get_path_name()]={'min':list(b.min.to_tuple()),'max':list(b.max.to_tuple()),'materials':[material(s.material_interface) for s in m.static_materials]}
for key in ('Leakage','DamagedConcrete'):
    material(u.load_asset('/Game/Dungeons/FacilityQuixel20261108/'+key+'/Materials/MI_'+key))
    n='T_'+key+'_BaseOpacity';t=u.load_asset('/Game/Dungeons/FacilityQuixel20261108/'+key+'/Textures/'+n)
    (ROOT/'SourceTextures').mkdir(exist_ok=True)
    task=u.AssetExportTask();task.object=t;task.filename=str(ROOT/'SourceTextures'/(n+'.png'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterPNG()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed '+key)
(ROOT/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if previous and not previous.startswith('/Temp/') and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
print('DERELICT_AUTHORING_INPUTS_READ',flush=True)
