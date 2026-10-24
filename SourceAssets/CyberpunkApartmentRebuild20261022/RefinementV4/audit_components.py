"""User-requested apartment component/material inventory. No PIE or renders."""
from pathlib import Path
import json,sys,csv
import unreal as u
ROOT=Path(__file__).resolve().parent
MAP='/Game/GameMaps/L_CyberpunkApartment'
L=u.MaterialEditingLibrary
phase='after' if '-ApartmentSurfaceAfter' in u.SystemLibrary.get_command_line() else 'before'
world=u.EditorLoadingAndSavingUtils.load_map(MAP)
materials={};components=[]
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 for c in actor.get_components_by_class(u.StaticMeshComponent):
  mesh=c.static_mesh
  if not mesh:continue
  slots=[]
  for index in range(c.get_num_materials()):
   m=c.get_material(index)
   if not m:slots.append({'index':index,'missing':True});continue
   path=m.get_path_name()
   if path not in materials:
    # NullRHI may have no compiled shader texture list. Resolve source graph and
    # effective instance parameters as well; an empty shader list is not no normal.
    textures=list(L.get_material_used_textures(m))
    base=m
    while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
    if isinstance(m,u.MaterialInstanceConstant):
     for parameter in L.get_texture_parameter_names(m):
      tex=L.get_material_instance_texture_parameter_value(m,parameter)
      if tex:textures.append(tex)
    if isinstance(base,u.Material):
     visited=set()
     def walk(n):
      if not n or n.get_path_name() in visited:return
      visited.add(n.get_path_name())
      if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)):
       tex=n.get_editor_property('texture')
       if tex:textures.append(tex)
      for child in L.get_inputs_for_material_expression(base,n):walk(child)
     for prop in ('FRONT_MATERIAL','NORMAL','BASE_COLOR','ROUGHNESS','METALLIC','EMISSIVE_COLOR'):
      walk(L.get_material_property_input_node(base,getattr(u.MaterialProperty,'MP_'+prop)))
    textures=list({t.get_path_name():t for t in textures if t}.values())
    entry={'path':path,'textures':[],'normal_textures':[]}
    for tex in textures:
     if not tex:continue
     comp=str(tex.get_editor_property('compression_settings'))
     row={'path':tex.get_path_name(),'compression':comp,'srgb':tex.get_editor_property('srgb')}
     entry['textures'].append(row)
     if 'NORMALMAP' in comp:entry['normal_textures'].append(row['path'])
    if isinstance(base,u.Material):
     n=L.get_material_property_input_node(base,u.MaterialProperty.MP_NORMAL)
     entry['legacy_normal_input']=n.get_name() if n else None
     entry['master']=base.get_path_name()
    materials[path]=entry
   slots.append({'index':index,'name':str(mesh.get_editor_property('static_materials')[index].material_slot_name),'material':path})
  components.append({'actor':actor.get_actor_label(),'folder':str(actor.get_folder_path()),'component':c.get_name(),
   'mesh':mesh.get_path_name(),'visible':c.is_visible(),'hidden_in_game':c.get_editor_property('hidden_in_game'),
   'collision':str(c.get_collision_enabled()),'slots':slots})
data={'map':MAP,'phase':phase,'component_count':len(components),'materials':materials,'components':components,
      'method':'saved asset bindings and texture resources; no rendered appearance or gameplay acceptance',
      'game_run':False,'rendered':False}
(ROOT/('component-audit-'+phase+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
with (ROOT/('component-matrix-'+phase+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['actor','component','mesh','slot','material','normal_textures','visible'])
 for c in components:
  for s in c['slots']:
   m=materials.get(s.get('material'),{})
   w.writerow([c['actor'],c['component'],c['mesh'],s.get('name'),s.get('material'),';'.join(m.get('normal_textures',[])),c['visible'] and not c['hidden_in_game']])
print('APARTMENT_COMPONENT_INVENTORY',phase,len(components),len(materials))
