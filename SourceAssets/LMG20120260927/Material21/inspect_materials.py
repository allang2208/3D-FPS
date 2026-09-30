"""User-requested A762 optic binding and material graph inspection; no PIE."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent; O.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary
report={'meshes':{},'materials':{},'textures':{},'game_tested':False,'rendered':False}
def serial(v):
    if isinstance(v,u.Object):return v.get_path_name()
    if isinstance(v,u.LinearColor):return [v.r,v.g,v.b,v.a]
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    return str(v)
def material(m):
    p=m.get_path_name()
    if p in report['materials']:return p
    b=m.get_base_material(); d={'base':b.get_path_name(),'class':m.get_class().get_name(),'parameters':{},'nodes':{},'outputs':{}}
    report['materials'][p]=d
    for kind in ['scalar','vector','texture','static_switch']:
        method='get_material_instance_' if isinstance(m,u.MaterialInstanceConstant) else 'get_material_default_'
        d['parameters'][kind]={str(n):serial(getattr(L,method+kind+'_parameter_value')(m,n)) for n in getattr(L,'get_'+kind+'_parameter_names')(b)}
    for prop in ['blend_mode','two_sided','shading_model']:
        try:d[prop]=serial(b.get_editor_property(prop))
        except Exception:pass
    for n in L.get_material_expressions(b):
        e={'class':n.get_class().get_name(),'inputs':[serial(x) for x in L.get_inputs_for_material_expression(b,n)],'input_names':list(map(str,L.get_material_expression_input_names(n)))}
        for prop in ['texture','coordinate_index','parameter_name','default_value','r','constant','const_a','const_b','const_alpha','const_min','const_max','material_function','sampler_type','description','code']:
            try:e[prop]=serial(n.get_editor_property(prop))
            except Exception:pass
        t=e.get('texture')
        if t and t not in report['textures']:
            tex=u.load_asset(t)
            report['textures'][t]={'srgb':tex.get_editor_property('srgb'),'compression':str(tex.get_editor_property('compression_settings')),'sources':list(tex.get_editor_property('asset_import_data').extract_filenames())}
        d['nodes'][n.get_path_name()]=e
    for name in ['BASE_COLOR','ROUGHNESS','METALLIC','SPECULAR','NORMAL','AMBIENT_OCCLUSION','OPACITY','OPACITY_MASK','EMISSIVE_COLOR']:
        prop=getattr(u.MaterialProperty,'MP_'+name)
        d['outputs'][name]={'node':serial(L.get_material_property_input_node(b,prop)),'pin':str(L.get_material_property_input_node_output_name(b,prop))}
    return p

roots=['/Game/Weapons/LMG201/Production20260927', '/Game/Weapons/LMG201/Cover10']
for root in roots:
 for path in u.EditorAssetLibrary.list_assets(root, True, False):
  # Current runtime body plus current separately attached stock parts/optics.
  if not ('/SM_LMG201_' in path or '/SK_LMG201_Cover10.' in path):continue
  mesh=u.load_asset(path)
  if not isinstance(mesh,(u.StaticMesh,u.SkeletalMesh)):continue
  slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
  report['meshes'][mesh.get_path_name()]={'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
  for s in slots:
   m=s.material_interface
   if m and m.get_path_name().startswith('/Game/Weapons/LMG201/'):
    material(m)
# Record common parents and texture settings, without modifying any assets.
for path in list(report['materials']):
 base=report['materials'][path]['base']
 if base not in report['materials']:material(u.load_asset(base))
for path in report['textures']:
 tex=u.load_asset(path)
 for prop in ['flip_green_channel','lod_bias','lod_group','max_texture_size','virtual_texture_streaming']:
  report['textures'][path][prop]=serial(tex.get_editor_property(prop))
(O/'before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
u.log('LMG201_MATERIAL_INSPECTION_SAVED meshes='+str(len(report['meshes']))+' materials='+str(len(report['materials'])))
