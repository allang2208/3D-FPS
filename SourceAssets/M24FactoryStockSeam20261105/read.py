"""Read the active factory-stock seams and material recipes for repair."""
import unreal as u, json, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
L=u.MaterialEditingLibrary
R={'meshes':{},'materials':{},'masters':{}}
paths={
 'body':'/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9',
 'advanced':'/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action',
 'cheekrest':'/Game/Weapons/M24/Surface20261027/SM_M24_m24_cheekrest',
}
def digest(a):
 p=Path(u.Paths.project_content_dir())/(a.get_path_name().split('.')[0][6:]+'.uasset')
 return hashlib.sha256(p.read_bytes()).hexdigest()
def material(m):
 path=m.get_path_name()
 if path in R['materials']:return
 base=m.get_base_material();bp=base.get_path_name()
 d={'master':bp,'sha256':digest(m),'parameters':{}}
 if isinstance(m,u.MaterialInstance):
  d['parent']=m.get_editor_property('parent').get_path_name()
  for kind in ('scalar','vector','texture'):
   vals={}
   for name in getattr(L,'get_'+kind+'_parameter_names')(base):
    v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(m,name)
    vals[str(name)]=v.get_path_name() if isinstance(v,u.Object) else [v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v
   d['parameters'][kind]=vals
 R['materials'][path]=d
 if bp not in R['masters']:
  ns=[]
  for n in L.get_material_expressions(base):
   if isinstance(n,u.MaterialExpressionCustom):ns.append({'name':str(n.get_editor_property('description')),'code':n.get_editor_property('code'),'inputs':[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]})
  R['masters'][bp]={'sha256':digest(base),'codes':ns}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 R['meshes'][key]={'path':path,'sha256':digest(mesh),'slots':[]}
 for s in slots:
  m=s.material_interface
  R['meshes'][key]['slots'].append({'slot':str(s.material_slot_name),'material':m.get_path_name() if m else None})
  if m:material(m)
material(u.load_asset('/Game/Weapons/M24/CarbonBolt20261029/Materials/MI_M24_CarbonBolt'))
(O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M24_STOCK_SEAM_INPUTS',len(R['materials']),flush=True)
