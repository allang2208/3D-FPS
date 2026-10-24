"""Read current source bindings for sky reuse and the reported water shimmer."""
from pathlib import Path
import unreal as u,json,runpy
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT']
L=u.MaterialEditingLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem)
report=dict(editor_actor_subsystem=bool(AA),editor_world_subsystem=bool(u.get_editor_subsystem(u.UnrealEditorSubsystem)),maps={},materials={},collections={})
for map_path in [C['HUB'],C['MAP']]:
 world=u.EditorLoadingAndSavingUtils.load_map(map_path);rows=[]
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  label=actor.get_actor_label();cls=actor.get_class().get_path_name()
  selected=map_path==C['MAP'] or 'UltraDynamicSky' in cls or isinstance(actor,u.FPSWeatherManager)
  if not selected:continue
  row=dict(label=label,cls=cls,location=list(actor.get_actor_location().to_tuple()),scale=list(actor.get_actor_scale3d().to_tuple()),meshes=[])
  if 'UltraDynamicSky' in cls:
   row['blueprint']=cls.split('.')[0]
   bp=u.load_asset(row['blueprint'])
   try:row['editable_variables']=[str(v.get_editor_property('var_name')) for v in bp.get_editor_property('new_variables') if v.get_editor_property('property_flags')&1]
   except Exception as error:row['variable_api']=str(error)
   row['components']=[dict(name=c.get_name(),cls=c.get_class().get_name()) for c in actor.get_components_by_class(u.ActorComponent)]
  for comp in actor.get_components_by_class(u.StaticMeshComponent):
   if not comp.static_mesh:continue
   b=comp.static_mesh.get_bounding_box()
   row['meshes'].append(dict(name=comp.get_name(),mesh=comp.static_mesh.get_path_name(),visible=comp.is_visible(),bounds=[list(b.min.to_tuple()),list(b.max.to_tuple())],materials=[m.get_path_name() if m else None for m in comp.get_materials()]))
   if map_path==C['MAP'] and label=='BAY_Water':
    mat=comp.get_material(0);base=mat
    while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
    nodes=[]
    for n in L.get_material_expressions(base):
     item=dict(cls=n.get_class().get_name(),name=n.get_name())
     if isinstance(n,u.MaterialExpressionCustom):item.update(code=n.get_editor_property('code'),description=n.get_editor_property('description'))
     nodes.append(item)
    report['materials']['water']=dict(instance=mat.get_path_name(),parent=base.get_path_name(),nodes=nodes)
  rows.append(row)
 report['maps'][map_path]=rows
 (ROOT/'source-bindings.json').write_text(json.dumps(report,indent=2),encoding='utf8')
registry=u.AssetRegistryHelpers.get_asset_registry()
for data in registry.get_assets_by_path('/Game/UltraDynamicSky',True):
 if str(data.asset_class_path.asset_name)=='MaterialParameterCollection':
  obj=data.get_asset();report['collections'][obj.get_path_name()]={'scalars':[str(p.get_editor_property('parameter_name')) for p in obj.get_editor_property('scalar_parameters')],'vectors':[str(p.get_editor_property('parameter_name')) for p in obj.get_editor_property('vector_parameters')]}
(ROOT/'source-bindings.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('APARTMENT_V6_SOURCES_READ',report['editor_actor_subsystem'],report['editor_world_subsystem'])
