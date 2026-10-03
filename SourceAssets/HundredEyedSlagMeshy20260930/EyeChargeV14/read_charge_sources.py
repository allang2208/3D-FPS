"""Targeted read of local charge candidates requested by the user. No preview/play/save."""
import json,sys
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT.resolve():raise RuntimeError('Wrong project')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters
L=u.MaterialEditingLibrary
paths=[
 '/Game/MayuOrbs/02_Orbs/Orb_1/NiagaraSystem/NS_Orb_1_Small',
 '/Game/MayuOrbs/02_Orbs/Orb_3/NiagaraSystems/NS_Orb_3_Small',
 '/Game/MayuOrbs/02_Orbs/Orb_5/NiagaraSystems/NS_Orb_5_Small',
 '/Game/MayuOrbs/02_Orbs/Orb_1/Materials/MI_Orb_1_red',
 '/Game/MayuOrbs/02_Orbs/Orb_1/Materials/M_Orb_1',
 '/Game/MayuOrbs/02_Orbs/Orb_3/Materials/M_orb_3',
 '/Game/MayuOrbs/02_Orbs/Orb_5/Materials/M_Orb_5',
 '/Game/Skills/ElectricMagic/NS_ThunderCharge']
rows=[]
for path in paths:
 a=u.load_asset(path)
 row={'path':path,'loaded':bool(a)}
 if not a:rows.append(row);continue
 row['class']=a.get_class().get_name()
 if isinstance(a,u.NiagaraSystem):
  summary=API.call_method('GetSystemSummary',(a,))
  row['user_variables']=[v.export_text() for v in summary.get_editor_property('user_variables')]
  row['emitters']={}
  for e in emitters(a):
   item={'settings':API.call_method('GetEmitterData',(ref(a,e),)).get_editor_property('property_values'),'renderers':[],'stacks':{}}
   top=API.call_method('GetEmitterTopology',(ref(a,e),))
   for rr in top.get_editor_property('renderers'):
    ix=rr.get_editor_property('renderer_index')
    item['renderers'].append(API.call_method('GetRendererData',(ref(a,e,renderer=ix),)).get_editor_property('property_values'))
   for field in ['emitter_update_script','particle_spawn_script','particle_update_script']:
    item['stacks'][field]=[m.export_text() for m in top.get_editor_property(field).get_editor_property('modules')]
   row['emitters'][e]=item
  row['api_methods']=[n for n in dir(a) if 'param' in n or 'bound' in n or 'emit' in n]
  row['fixed_bounds']=str(a.get_editor_property('fixed_bounds'))
 if isinstance(a,u.MaterialInterface):
  row['vectors']={str(n):str(L.get_material_instance_vector_parameter_value(a,n)) if isinstance(a,u.MaterialInstanceConstant) else None for n in L.get_vector_parameter_names(a)}
  row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(a,n) if isinstance(a,u.MaterialInstanceConstant) else None for n in L.get_scalar_parameter_names(a)}
  row['textures']={str(n):str(L.get_material_instance_texture_parameter_value(a,n)) if isinstance(a,u.MaterialInstanceConstant) else None for n in L.get_texture_parameter_names(a)}
  if isinstance(a,u.Material):
   row['blend']=str(a.get_editor_property('blend_mode'))
   row['expressions']=[]
   for x in L.get_material_expressions(a):
    item={'name':x.get_name(),'class':x.get_class().get_name()}
    for key in ['texture','parameter_name','default_value','desc']:
     try:item[key]=str(x.get_editor_property(key))
     except Exception:pass
    item['inputs']=[i.get_name() if i else None for i in L.get_inputs_for_material_expression(a,x)]
    row['expressions'].append(item)
 rows.append(row)
(OUT/'charge_sources.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('SLAG_EYE_CHARGE_LOCAL_SOURCES_READ '+str(len(rows)),flush=True)
