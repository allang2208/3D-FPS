"""Resolve vendor ground-floor assemblies required for complete production buildings."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
exec(compile((R/'read_sources.py').read_text().split('# Only an unsaved')[0],str(R/'read_sources.py'),'exec'),globals())
report=json.loads((R/'sources.json').read_text())
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
folder=PROJECT/'Content/CitySampleBuildings/Building/Library/Kit_Ref_Bldg/LevelInstance'
for p in sorted(folder.glob('BPP_*Level01*.uasset')):
    asset='/Game/'+p.relative_to(PROJECT/'Content').with_suffix('').as_posix()
    cls=E.load_blueprint_class(asset)
    if not cls:raise RuntimeError('Ground-floor blueprint missing '+asset)
    actor=aa.spawn_actor_from_class(cls,u.Vector())
    report['assemblies'][p.stem]=dict(asset=asset,components=components(actor),ground_floor=True)
    aa.destroy_actor(actor)
    (R/'sources.json').write_text(json.dumps(report),encoding='utf8')
    print('EXTERIOR_GROUND_FLOOR',p.stem,flush=True)

# Read the actual emission and water graph connections for targeted adaptation.
parents=set(m.get('parent') for m in report['materials'].values() if 'AmountOff' in m.get('scalars',{}))
report['window_masters']={}
for path in sorted(parents):
    mat=u.load_asset(path)
    while isinstance(mat,u.MaterialInstanceConstant):mat=mat.get_editor_property('parent')
    if mat.get_path_name() in report['window_masters']:continue
    row={}
    for key in ('MP_EMISSIVE_COLOR','MP_FRONT_MATERIAL','MP_MATERIAL_ATTRIBUTES'):
        prop=getattr(u.MaterialProperty,key);n=L.get_material_property_input_node(mat,prop)
        if n:row[key]=dict(name=n.get_name(),type=n.get_class().get_name(),output=L.get_material_property_input_node_output_name(mat,prop),inputs=[str(k) for k in L.get_material_expression_input_names(n)])
    row['substrate']=[dict(name=n.get_name(),type=n.get_class().get_name(),inputs=[str(k) for k in L.get_material_expression_input_names(n)]) for n in L.get_material_expressions(mat) if 'Substrate' in n.get_class().get_name()]
    report['window_masters'][mat.get_path_name()]=row

water=report['map']['BAY_Water']['components'][0]['materials'][0]
m=u.load_asset(water)
while isinstance(m,u.MaterialInstanceConstant):m=m.get_editor_property('parent')
report['water_source']=dict(instance=water,master=m.get_path_name(),custom=[dict(description=str(n.get_editor_property('description')),code=n.get_editor_property('code'),inputs=[str(k) for k in L.get_material_expression_input_names(n)]) for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)])
report['stage']='production_inputs_ready'
(R/'sources.json').write_text(json.dumps(report),encoding='utf8')
print('EXTERIOR_PRODUCTION_INPUTS_READY',len(report['assemblies']),len(report['window_masters']),flush=True)
