import json, unreal as u
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/WorkbenchMaterialUnification20261108')
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
report={'palette':[],'meshes':{},'materials':{},'missing':[],'tests_run':False,'renders_run':False}
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
if not palette:raise RuntimeError('Palette missing')
paths=set()
for row in palette.get_editor_property('components'):
 id=str(row.get_editor_property('id'))
 if any(x in id.lower() for x in ('workbench','woodwork','casting','forg','anvil','smelt','alchemy','potion')):
  d={'id':id,'display_name':str(row.get_editor_property('display_name'))}
  for key in ('mesh','surface'):
   ob=row.get_editor_property(key);d[key]=ob.get_path_name() if ob else None
  report['palette'].append(d)
  if d['mesh']:paths.add(d['mesh'])
  if d['surface']:report['materials'][d['surface']]={}
paths.update(['/Game/Building/WoodworkingBenchV6Controls20261013/SM_WoodworkingBenchBody','/Game/Building/WoodworkingBenchV6Controls20261013/SM_WoodworkingSawBlade','/Game/Building/PotionWorkbench20261015/ThermometerV9/SM_AlchemyBody'])
for folder in ['/Game/Building/PotionWorkbench20261015/RuntimeV2/Meshes','/Game/Building/PotionWorkbench20261015/InteractionV7','/Game/Building/PotionWorkbench20261015/InteractionV10','/Game/Building/PotionWorkbench20261015/RefinementV4']:
 for p in E.list_assets(folder,True,False):
  if p.rsplit('/',1)[-1].startswith('SM_'):paths.add(p)
for p in sorted(paths):
 ob=u.load_asset(p)
 if not isinstance(ob,u.StaticMesh):report['missing'].append(p);continue
 slots=[]
 for i,s in enumerate(ob.static_materials):
  m=s.material_interface;mp=m.get_path_name() if m else None
  slots.append({'index':i,'slot':str(s.material_slot_name),'material':mp})
  if mp:report['materials'][mp]={}
  else:report['missing'].append(p+' slot '+str(i))
 report['meshes'][ob.get_path_name()]={'slots':slots,'lods':ob.get_num_lods(),'triangles':[ob.get_num_triangles(i) for i in range(ob.get_num_lods())]}
queue=list(report['materials'])
for path in queue:
 m=u.load_asset(path)
 if not m:report['missing'].append(path);continue
 d={'class':m.get_class().get_name()}
 if isinstance(m,u.MaterialInstanceConstant):
  parent=m.get_editor_property('parent');d['parent']=parent.get_path_name() if parent else None
  for key in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values']:
   vals=[]
   for x in m.get_editor_property(key):
    val=x.parameter_value
    vals.append({'name':str(x.parameter_info.name),'value':val.get_path_name() if isinstance(val,u.Object) else str(val)})
   d[key]=vals
  if parent and parent.get_path_name() not in report['materials']:report['materials'][parent.get_path_name()]={};queue.append(parent.get_path_name())
 elif isinstance(m,u.Material):
  d['blend_mode']=str(m.get_editor_property('blend_mode'));d['shading_model']=str(m.get_editor_property('shading_model'))
  d['inputs']={}
  for name in ['BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION','FRONT_MATERIAL']:
   n=L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+name))
   d['inputs'][name]=n.get_class().get_name() if n else None
  d['nodes']=[]
  for n in L.get_material_expressions(m):
   nd={'class':n.get_class().get_name(),'name':n.get_name()}
   for key in ['parameter_name','default_value','texture','r','constant','sampler_type','code']:
    try:
     val=n.get_editor_property(key)
     nd[key]=val.get_path_name() if isinstance(val,u.Object) else str(val)
    except Exception:pass
   d['nodes'].append(nd)
 report['materials'][path]=d
(R/'Receipts/audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('WORKBENCH_AUDIT '+json.dumps({'palette':report['palette'],'mesh_count':len(report['meshes']),'material_count':len(report['materials']),'missing':report['missing']},ensure_ascii=False))
