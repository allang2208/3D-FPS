import unreal,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/Consumables5080_20260910/UE');D='/Game/Items/Consumables';tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
manifest=json.loads((P/'manifest.json').read_text());report={}
def imp(path,name,dest,options=None):
 t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=dest;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
 if options:t.options=options
 tools.import_asset_tasks([t]);return unreal.load_asset(dest+'/'+name)
for asset,data in manifest.items():
 dest=D+'/'+asset
 opts=unreal.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False;opts.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;opts.automated_import_should_detect_type=False
 opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.generate_lightmap_u_vs=True;opts.static_mesh_import_data.auto_generate_collision=False
 mesh=imp(P/(asset+'.fbx'),'SM_'+asset,dest,opts);assert isinstance(mesh,unreal.StaticMesh),asset
 materials={}
 for index,(name,v) in enumerate(data['materials'].items()):
  mn='M_'+asset+'_'+str(index);m=unreal.load_asset(dest+'/'+mn) or tools.create_asset(mn,dest,unreal.Material,unreal.MaterialFactoryNew());lib.delete_all_material_expressions(m)
  m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
  c=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.constant=unreal.LinearColor(*v['Base Color']);lib.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
  if 'texture' in v:
   tex=imp(P/v['texture'],'T_'+asset+'_'+str(index),dest);n=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample);n.texture=tex;lib.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
  for val,prop in [(v['Roughness'],unreal.MaterialProperty.MP_ROUGHNESS),(v['Metallic'],unreal.MaterialProperty.MP_METALLIC)]:
   n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=val;lib.connect_material_property(n,'',prop)
  if 'glass' in name.lower():
   m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING);m.set_editor_property('two_sided',True)
   n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=.16 if 'glass' in name.lower() else .78;lib.connect_material_property(n,'',unreal.MaterialProperty.MP_OPACITY)
  lib.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m);materials[name]=m
 for i,slot in enumerate(mesh.static_materials):
  slot_name=str(slot.material_slot_name)
  name=next((n for n in materials if n.replace(' ','_').replace('.','_')==slot_name or n==slot_name),None)
  if name is None:raise RuntimeError('Unmapped material slot: '+asset+' '+slot_name+' '+str(list(materials)))
  mesh.set_material(i,materials[name])
 ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
 unreal.EditorAssetLibrary.save_loaded_asset(mesh);report[asset]={'mesh':mesh.get_path_name(),'slots':len(mesh.static_materials),'bounds':str(mesh.get_bounds())}
Path('D:/FPS3D/FPSGAME/Saved/ConsumablesImport.json').write_text(json.dumps(report,indent=2));unreal.log('CONSUMABLE_IMPORT_PASS')
