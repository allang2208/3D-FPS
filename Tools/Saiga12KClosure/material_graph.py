import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KClosure20261018');d=json.loads((O/'Reports/parts-before.json').read_text());L=u.MaterialEditingLibrary;R={}
for key in ('eoth_holographic','holographic','laser_1'):
 path=next(iter(d['assets'][key]['slots'].values()));m=u.load_asset(path);base=m.get_base_material();row={'base':base.get_path_name(),'properties':{},'nodes':{}};R[key]=row
 stack=[]
 for name in ('MP_BASE_COLOR','MP_METALLIC','MP_ROUGHNESS','MP_NORMAL','MP_AMBIENT_OCCLUSION'):
  node=L.get_material_property_input_node(base,getattr(u.MaterialProperty,name));row['properties'][name]=node.get_path_name() if node else None
  if node:stack.append(node)
 while stack:
  n=stack.pop();path=n.get_path_name()
  if path in row['nodes']:continue
  nr={'class':n.get_class().get_name()};row['nodes'][path]=nr
  for prop in ('constant','r','g','b','a','const_a','const_b','parameter_name','texture','material_function','desc','code'):
   try:
    v=n.get_editor_property(prop);nr[prop]=v.get_path_name() if isinstance(v,u.Object) else str(v)
    if prop=='texture' and v:nr['source']=v.asset_import_data.get_first_filename()
   except Exception:pass
  nodes=L.get_inputs_for_material_expression(base,n);nr['inputs']=[x.get_path_name() if x else None for x in nodes];stack.extend(x for x in nodes if x)
R['capture_api']={cl:{n:str(getattr(getattr(u,cl),n).__doc__) for n in names if hasattr(getattr(u,cl),n)} for cl,names in [('EditorActorSubsystem',['spawn_actor_from_class']),('SkeletalMeshComponent',['set_update_animation_in_editor','set_animation','set_position','play_animation','show_material_section']),('SceneCaptureComponent2D',['show_only_component','capture_scene'])]}
(O/'Reports/material-graphs.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('MATERIAL_GRAPHS_READ')
