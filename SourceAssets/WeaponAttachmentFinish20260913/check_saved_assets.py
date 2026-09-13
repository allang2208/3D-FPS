"""Scoped saved-asset readback requested by the user; no world or gameplay run."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
before=json.loads((O/'before.json').read_text());installed=json.loads((O/'installed.json').read_text())
results=[];errors=[]
def check(value,message):
 results.append({'ok':bool(value),'check':message})
 if not value:errors.append(message)
for ident,entry in installed.items():
 family,key=ident.split('/');old=before['parts'][family][key];mesh=u.load_asset(entry['mesh'])
 check(mesh is not None,ident+' saved variant loads')
 if not mesh:continue
 check(mesh.get_num_triangles(0)==old['triangles'],ident+' triangle count unchanged')
 check([str(s.material_slot_name) for s in mesh.static_materials]==[s['slot'] for s in old['slots']],ident+' original section names and order retained')
 check(E.get_metadata_tag(mesh,'WeaponFinishReference')==entry['reference'],ident+' target receiver recorded')
 for index,s in enumerate(mesh.static_materials):
  label=str(s.material_slot_name);mat=s.material_interface;check(mat.get_path_name()==entry['slots'][label],ident+'/'+label+' saved binding')
  if label not in entry['changed_slots']:
   check(mat.get_path_name()==old['slots'][index]['material'],ident+'/'+label+' non-target material preserved')
   continue
  base=mat.get_base_material();check(E.get_metadata_tag(base,'WeaponFinishReference')==entry['reference'],ident+'/'+label+' receiver-specific finish')
  exprs=L.get_material_expressions(base)
  uv=[n for n in exprs if isinstance(n,u.MaterialExpressionTextureCoordinate)]
  check(any(n.get_editor_property('coordinate_index')==entry['uv_index'] for n in uv),ident+'/'+label+' correct coating UV channel')
  textures=[n.get_editor_property('texture').get_path_name() for n in exprs if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture')]
  required=['T_M4_Receiver_BaseColor','T_M4_Receiver_Roughness'] if family=='M4' else ['T_AKM_Mount_Base_color','T_AKM_Mount_Roughness','T_AKM_Mount_Metallic']
  check(all(any(name in t for t in textures) for name in required),ident+'/'+label+' target receiver texture channels')
  original=u.load_asset(old['slots'][index]['material']).get_base_material()
  for prop in [u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialProperty.MP_OPACITY,u.MaterialProperty.MP_OPACITY_MASK,u.MaterialProperty.MP_EMISSIVE_COLOR]:
   previous=L.get_material_property_input_node(original,prop);current=L.get_material_property_input_node(base,prop)
   check((previous.get_name() if previous else None)==(current.get_name() if current else None),ident+'/'+label+' retained '+str(prop))
check(len(installed)==14,'14 selected mesh variants saved')
out={'scope':'Saved mesh/material bindings only; no gameplay or rendered comparison','mesh_count':len(installed),'checks':len(results),'failures':errors,'results':results}
(O/'asset_readback.json').write_text(json.dumps(out,indent=2))
if errors:raise RuntimeError('; '.join(errors))
u.log('WEAPON_FINISH_SAVED_ASSETS_OK '+str(len(results)))
