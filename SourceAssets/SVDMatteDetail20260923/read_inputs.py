"""Read the exact SVD material authoring inputs; no rendering or gameplay."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
P='/Game/Weapons/SVDDragunov20260922'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
mesh=u.load_asset(P+'/Accessories20260923/SK_SVD_Modular')
meshes=[mesh]
for path in E.list_assets(P+'/Accessories20260923/Meshes',True,False):
 a=u.load_asset(path)
 if isinstance(a,u.StaticMesh):meshes.append(a)
report={'meshes':[],'materials':{},'wet':{}}
for a in meshes:
 slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 row={'asset':a.get_path_name(),'slots':[]}
 for i,s in enumerate(slots):
  m=s.material_interface
  row['slots'].append({'index':i,'slot':str(s.material_slot_name),'material':m.get_path_name() if m else None})
  if m and m.get_path_name().startswith(P):report['materials'][m.get_path_name()]={}
 report['meshes'].append(row)
for table in ['/Game/Weather/RainVisibility/DA_WeatherPresentation',P+'/Accessories20260923/DA_SVD_AttachmentWetMaterials']:
 a=u.load_asset(table)
 if a:
  for k,v in a.get_editor_property('wet_materials').items():
   if str(k) in report['materials'] and v:
    report['wet'][str(k)]=v.get_path_name();report['materials'][v.get_path_name()]={}
for path in report['materials']:
 m=u.load_asset(path);base=m.get_base_material()
 report['materials'][path]={'base':base.get_path_name(),'class':m.get_class().get_name(),'blend':str(base.blend_mode),'nodes':[]}
 for n in L.get_material_expressions(base):
  item={'class':n.get_class().get_name(),'name':n.get_name()}
  if isinstance(n,u.MaterialExpressionCustom):item.update(label=str(n.get_editor_property('description')),code=str(n.get_editor_property('code')))
  if isinstance(n,u.MaterialExpressionTextureSample):item['texture']=n.texture.get_path_name() if n.texture else None
  if isinstance(n,u.MaterialExpressionTextureCoordinate):item['uv']=n.coordinate_index
  report['materials'][path]['nodes'].append(item)
(O/'material_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SVD_FINISH_INPUT',len(meshes),len(report['materials']),len(report['wet']),flush=True)
