"""User-requested PKM material and rain-coverage inspection; no scene startup."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
P='/Game/Weapons/PKMLowpoly20260922'
paths=[P+'/Accessories14/SK_PKM_Manny_Modular',P+'/Bipod07/SM_PKM_Bipod']
paths+=list(E.list_assets(P+'/Accessories14/Meshes',recursive=False,include_folder=False))
weather=u.load_asset('/Game/Weather/RainVisibility/DA_WeatherPresentation')
mapping={str(k):v.get_path_name() for k,v in weather.get_editor_property('wet_materials').items() if v}
report={'meshes':[],'materials':{},'weather_asset':weather.get_path_name(),'coverage':[]}
def describe(m):
 p=m.get_path_name()
 if p in report['materials']:return
 base=m;overrides=[]
 while isinstance(base,u.MaterialInstance):
  overrides.append({'path':base.get_path_name(),'scalar':str(base.get_editor_property('scalar_parameter_values')),
   'texture':str(base.get_editor_property('texture_parameter_values')),'vector':str(base.get_editor_property('vector_parameter_values'))})
  base=base.get_editor_property('parent')
 data={'master':base.get_path_name(),'overrides':overrides,'blend':str(base.get_editor_property('blend_mode')),
  'tangent_space_normal':base.get_editor_property('tangent_space_normal'),'nodes':[],'outputs':{}}
 for name in ['BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION','MATERIAL_ATTRIBUTES','FRONT_MATERIAL','EMISSIVE_COLOR','OPACITY_MASK']:
  prop=getattr(u.MaterialProperty,'MP_'+name);src=L.get_material_property_input_node(base,prop)
  data['outputs'][name]=[src.get_name(),L.get_material_property_input_node_output_name(base,prop)] if src else None
 for n in L.get_material_expressions(base):
  row={'name':n.get_name(),'class':n.get_class().get_name()}
  for key in ['parameter_name','default_value','texture','coordinate_index','description','code','r','constant']:
   try:
    v=n.get_editor_property(key)
    row[key]=v.get_path_name() if isinstance(v,u.Object) else str(v)
   except Exception:pass
  data['nodes'].append(row)
 report['materials'][p]=data
for path in paths:
 mesh=u.load_asset(path)
 if not isinstance(mesh,(u.SkeletalMesh,u.StaticMesh)):continue
 slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 row={'asset':mesh.get_path_name(),'class':mesh.get_class().get_name(),'slots':[]}
 for i,s in enumerate(slots):
  m=s.material_interface
  if not m:continue
  describe(m);p=m.get_path_name();pair=mapping.get(p)
  optical=any(k in p.lower() for k in ['manny','glass','lens','reticle','beam','emissive'])
  row['slots'].append({'index':i,'slot':str(s.material_slot_name),'material':p})
  report['coverage'].append({'mesh':mesh.get_name(),'slot':i,'material':p,'wet':pair,'optical_or_hands':optical})
 report['meshes'].append(row)
(O/'materials_before.json').write_text(json.dumps(report,indent=2))
surface=[c for c in report['coverage'] if not c['optical_or_hands']]
print('PKM20_MATERIAL_READ',json.dumps({'meshes':len(report['meshes']),'unique_materials':len(report['materials']),
 'surface_slots':len(surface),'mapped_surface_slots':sum(bool(c['wet']) for c in surface),
 'unmapped_materials':sorted(set(c['material'] for c in surface if not c['wet']))}))
