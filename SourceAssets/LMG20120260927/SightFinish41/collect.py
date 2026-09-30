import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];(O/'Exports').mkdir(exist_ok=True)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
targets={'Body':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','RearSight':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_RearSight','FrontSight':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_FrontSight','Wet':'/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials','QBZ191':'/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny'}
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
out={'pie':bool(sub and sub.get_game_world())};dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};mats={}
for key,path in targets.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 out[key]={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'dirty':path in dirty}
 if key=='Wet':
  out[key]['mapping']={str(k):v.get_path_name() for k,v in a.get_editor_property('wet_materials').items() if v};continue
 slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 out[key]['slots']=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]
 for s in slots:
  if s.material_interface:mats[s.material_interface.get_path_name()]=s.material_interface
 if key=='QBZ191':continue
 ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Exports'/('Before_'+key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.collision=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export '+path)
(O/'capture.json').write_text(json.dumps(out,indent=2))
graphs={}
for path,m in mats.items():
 if '/LMG201/' not in path and '/QBZ191/' not in path:continue
 row={'class':m.get_class().get_name()};graphs[path]=row
 if isinstance(m,u.MaterialInstance):
  row['parent']=m.get_editor_property('parent').get_path_name()
  for field in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values']:row[field]=str(m.get_editor_property(field))
  continue
 row['outputs']={str(p):str(L.get_material_property_input_node(m,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_NORMAL]};row['nodes']=[]
 for node in L.get_material_expressions(m):
  n={'name':node.get_name(),'class':node.get_class().get_name()};row['nodes'].append(n)
  for field in ['texture','parameter_name','default_value','constant','r','g','b','a','code','description','coordinate_index']:
   try:
    v=node.get_editor_property(field);n[field]=v.get_path_name() if isinstance(v,u.Object) else str(v)
   except Exception:pass
(O/'material_inputs.json').write_text(json.dumps(graphs,indent=2))
print('S41_CAPTURED',json.dumps({'pie':out['pie'],'targets':{k:{'asset':v['asset'],'dirty':v['dirty']} for k,v in out.items() if isinstance(v,dict)},'material_count':len(graphs)}),flush=True)
