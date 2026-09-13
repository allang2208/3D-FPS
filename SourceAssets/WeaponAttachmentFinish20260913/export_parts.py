import unreal as u, json, shutil
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1]
r=json.loads((O/'before.json').read_text())
selected={'M4':['drum','holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','prism','reargrip'],
          'AKM':['skeleton','qr_performance','drum','suppressor','brake','titanium_brake','vertical','canted','prism','reargrip'],
          'QBZ191':['reargrip']}
result={}
for family,keys in selected.items():
 for key in keys:
  info=r['parts'][family][key];path=info['path'];mesh=u.load_asset(path)
  if not mesh:raise RuntimeError(path)
  file=ROOT/'Content'/Path(path.removeprefix('/Game/')+'.uasset');backup=O/'Before'/file.relative_to(ROOT)
  if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
  folder=O/'Sources'/family;folder.mkdir(parents=True,exist_ok=True)
  t=u.AssetExportTask();t.object=mesh;t.filename=str(folder/(key+'.fbx'));t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.StaticMeshExporterFBX()
  opt=u.FbxExportOption();opt.ascii=False;opt.level_of_detail=False;opt.collision=False;t.options=opt
  if not u.Exporter.run_asset_export_task(t):raise RuntimeError(key)
  result[family+'/'+key]={**info,'family':family,'key':key,'fbx':t.filename}
(O/'sources.json').write_text(json.dumps(result,indent=2))
L=u.MaterialEditingLibrary
body=u.load_asset('/Game/Weapons/M4InfimaV3/Body_001')
base=body.get_base_material();fn=L.get_material_property_input_node(base,u.MaterialProperty.MP_BASE_COLOR)
report={'function':fn.get_editor_property('material_function').get_path_name(),
        'inputs':list(map(str,L.get_material_expression_input_names(fn))),
        'outputs':{str(p):str(L.get_material_property_input_node_output_name(base,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_SPECULAR]},
        'incoming':[], 'function_expressions':[]}
for n in L.get_inputs_for_material_expression(base,fn):
 report['incoming'].append(n.get_name() if n else None)
for n in L.get_material_function_expressions(fn.get_editor_property('material_function')):
 e={'class':n.get_class().get_name(),'name':n.get_name()}
 for prop in ['input_name','output_name','description','r','default_value']:
  try:e[prop]=str(n.get_editor_property(prop))
  except Exception:pass
 report['function_expressions'].append(e)
(O/'m4_surface_conversion.json').write_text(json.dumps(report,indent=2))
u.log('WEAPON_FINISH_EXPORT_COMPLETE')
