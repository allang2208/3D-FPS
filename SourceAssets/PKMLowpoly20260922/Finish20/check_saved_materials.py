"""Requested PKM material/rain inspection, reads saved assets without a world."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.MaterialEditingLibrary
before=json.loads((O/'materials_before.json').read_text())
receipt=json.loads((O/'finish_import.json').read_text())
table=u.load_asset(receipt['wet_library'])
mapping={str(k):v.get_path_name() for k,v in table.get_editor_property('wet_materials').items() if v}
report={'mesh_count':0,'slot_count':0,'covered_surface_slots':0,'excluded_slots':[],
        'materials':[],'problems':[],'world_started':False,'shader_compilation':[]}
def root(m,prop):return L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+prop))
def sources(m,expr):
 seen=set();todo=[expr] if expr else []
 while todo:
  n=todo.pop()
  if not n or n in seen:continue
  seen.add(n);todo+=list(L.get_inputs_for_material_expression(m,n))
 return seen
def textures(m,prop):
 result=[]
 for n in sources(m,root(m,prop)):
  try:
   t=n.get_editor_property('texture')
   if t:result.append(t.get_path_name())
  except Exception:pass
 return sorted(result)
for row in before['meshes']:
 mesh=u.load_asset(row['asset'])
 slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 report['mesh_count']+=1
 if len(slots)!=len(row['slots']):report['problems'].append('Slot count '+row['asset'])
 for old in row['slots']:
  s=slots[old['index']];path=s.material_interface.get_path_name();report['slot_count']+=1
  expected=receipt['dry'].get(old['material'],old['material'])
  if str(s.material_slot_name)!=old['slot'] or path!=expected:report['problems'].append('Slot binding '+row['asset']+' '+str(old['index']))
  if old['material'] in receipt['dry']:
   if path not in mapping:report['problems'].append('Missing rain '+path)
   else:report['covered_surface_slots']+=1
  else:report['excluded_slots'].append({'mesh':row['asset'],'slot':old['slot'],'material':path})
for old_path,dry_path in receipt['dry'].items():
 original_asset=u.load_asset(old_path);dry_asset=u.load_asset(dry_path)
 original=original_asset.get_base_material();dry=dry_asset.get_base_material()
 wet=u.load_asset(mapping[dry_path]).get_base_material()
 data={'original':old_path,'dry':dry_path,'wet':mapping[dry_path],
       'normal_textures_preserved':textures(original,'NORMAL')==textures(dry,'NORMAL'),
       'ao_textures_preserved':textures(original,'AMBIENT_OCCLUSION')==textures(dry,'AMBIENT_OCCLUSION')}
 wet_nodes=L.get_material_expressions(wet)
 params=[n for n in wet_nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='WeaponWetness']
 data['wetness_zero_default']=len(params)==1 and params[0].get_editor_property('default_value')==0
 for prop in ['BASE_COLOR','ROUGHNESS','NORMAL']:
  data['wet_drives_'+prop.lower()]=bool(params and params[0] in sources(wet,root(wet,prop)))
 bead=[n for n in wet_nodes if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='WeatherBeads']
 data['dry_beads_disabled']=bool(bead and 'coverage=saturate(Wet*20.0)' in bead[0].get_editor_property('code'))
 data['normal_mode_preserved']=dry.get_editor_property('tangent_space_normal')==original.get_editor_property('tangent_space_normal')
 if isinstance(original_asset,u.MaterialInstanceConstant):
  data['instance_overrides_preserved']=all(str(original_asset.get_editor_property(k))==str(dry_asset.get_editor_property(k))
    for k in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values'])
 for key,value in data.items():
  if value is False:report['problems'].append(dry_path+' '+key)
 report['materials'].append(data)
for path in receipt['compiled']:
 material=u.load_asset(path)
 errors=list(L.recompile_material(material))
 stats=L.get_statistics(material)
 row={'material':path,'errors':[str(e) for e in errors],
      'pixel_instructions':stats.num_pixel_shader_instructions,
      'samplers':stats.num_samplers}
 report['shader_compilation'].append(row)
 if errors:report['problems'].append('Shader compilation '+path+' '+str(errors))
 print('PKM20_COMPILED',path,len(errors),flush=True)
report['before_covered_surface_slots']=sum(bool(r['wet']) for r in receipt['coverage_before'] if r['material'] in receipt['dry'])
report['wet_pairs']=len(mapping)
(O/'material_rain_check.json').write_text(json.dumps(report,indent=2))
print('PKM20_SAVED_MATERIAL_CHECK',json.dumps({k:v for k,v in report.items() if k not in ['materials','excluded_slots','shader_compilation']}),flush=True)
if report['problems']:raise RuntimeError('PKM material/rain problems; see material_rain_check.json')
