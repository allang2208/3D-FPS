"""Inspect the reported untextured grips; no mutation, rendering, or PIE launch."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;D='/Game/Weapons/SharedSwordGrips20260927';L=u.MaterialEditingLibrary
result={'materials':[],'meshes':[],'live':[],'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
for key in ['Leather','Steel','Textile']:
 m=u.load_asset(D+'/Materials/M_SharedGrip_'+key)
 row={'material':m.get_path_name(),'properties':{},'textures':[]}
 for field in ['MP_BASE_COLOR','MP_METALLIC','MP_ROUGHNESS','MP_NORMAL','MP_FRONT_MATERIAL','MP_MATERIAL_ATTRIBUTES']:
  prop=getattr(u.MaterialProperty,field,None)
  if prop is None:continue
  n=L.get_material_property_input_node(m,prop)
  row['properties'][field]=n.get_path_name() if n else None
 for tex in L.get_used_textures(m):
  row['textures'].append({'path':tex.get_path_name(),'srgb':tex.get_editor_property('srgb'),'compression':str(tex.get_editor_property('compression_settings'))})
 row['expressions']=[]
 for n in u.ObjectIterator(u.MaterialExpression):
  if n.get_outer()!=m:continue
  v={'class':n.get_class().get_name(),'path':n.get_path_name()}
  if isinstance(n,u.MaterialExpressionTextureSample):
   t=n.get_editor_property('texture');v.update(texture=t.get_path_name() if t else None,sampler=str(n.get_editor_property('sampler_type')))
  row['expressions'].append(v)
 result['materials'].append(row)
for row in json.loads((P/'models.json').read_text()):
 m=u.load_asset(D+'/'+row['host']+'/'+row['mesh'])
 result['meshes'].append({'mesh':m.get_path_name(),'materials':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in m.static_materials]})
for c in u.ObjectIterator(u.StaticMeshComponent):
 mesh=c.get_editor_property('static_mesh')
 if not mesh or not mesh.get_path_name().startswith(D):continue
 result['live'].append({'component':c.get_path_name(),'mesh':mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
(P/'material_failure_inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
