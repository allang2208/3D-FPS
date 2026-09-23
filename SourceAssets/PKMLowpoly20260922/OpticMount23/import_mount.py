"""Save a private mount and receiver-derived dry/wet materials in background."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';D=P+'/OpticMount23'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
before=json.loads((O/'materials_before.json').read_text())
body_path=P+'/Accessories14/SK_PKM_Manny_Modular'
body_material=next(s['material'] for s in before['meshes'][body_path] if s['slot']=='PKM_QBZ_Body')
wet_material=before['wet_mapping'][body_material]
def save(a):
 if not E.save_asset(a.get_path_name().split('.')[0],False):raise RuntimeError('Save failed '+a.get_path_name())
textures={}
for channel in ['BaseColor','ORM','Normal']:
 t=u.AssetImportTask();t.filename=str(O/'Textures'/('T_PKM23_Metal_'+channel+'.png'))
 t.destination_path=D+'/Textures';t.destination_name='T_PKM23_Metal_'+channel
 t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
 tex=u.load_asset(t.destination_path+'/'+t.destination_name)
 tex.srgb=channel=='BaseColor';tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
 tex.address_x=u.TextureAddress.TA_MIRROR;tex.address_y=u.TextureAddress.TA_MIRROR
 tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT
 if channel=='Normal':tex.flip_green_channel=True
 save(tex);textures[channel]=tex
materials={};compilation={}
for kind,source in [('Dry',body_material),('Wet',wet_material)]:
 path=D+'/Materials/M_PKM23_Mount_'+kind
 m=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
 replaced=[]
 for n in L.get_material_expressions(m):
  if not isinstance(n,u.MaterialExpressionTextureSample):continue
  tex=n.get_editor_property('texture')
  if not tex:continue
  for channel in textures:
   if tex.get_name().endswith('_'+channel) and 'PKM_QBZ_Body' in tex.get_name():
    n.set_editor_property('texture',textures[channel]);replaced.append(channel)
    # Source graph uses UV0. The new mesh carries the same tangent UV0.
 if sorted(replaced)!=['BaseColor','Normal','ORM']:raise RuntimeError('Receiver texture remap incomplete '+str(replaced))
 E.set_metadata_tag(m,'WeaponFinishReference',body_material)
 E.set_metadata_tag(m,'PKM23_Coating','Actual receiver top patch, 24x50 mm, UV0; geometric edge normals')
 if kind=='Wet':E.set_metadata_tag(m,'PKM20_WetSource',materials['Dry'].get_path_name())
 compilation[kind]=[str(v) for v in L.recompile_material(m)];save(m);materials[kind]=m
 if compilation[kind]:raise RuntimeError('Mount material compilation failed '+str(compilation[kind]))

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 options=u.FbxImportUI();options.automated_import_should_detect_type=False
 options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 options.import_materials=False;options.import_textures=False;options.import_animations=False
 options.set_editor_property('reset_to_fbx_on_material_conflict',True)
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
 data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 t=u.AssetImportTask();t.filename=str(O/'Exports/SM_PKM_optic_rail.fbx');t.destination_path=D
 t.destination_name='SM_PKM_optic_rail';t.options=options;t.factory=u.FbxFactory()
 t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
 mesh=u.load_asset(D+'/SM_PKM_optic_rail')
 if not t.imported_object_paths or not mesh:raise RuntimeError('Mount mesh import failed')
 slots=mesh.static_materials
 for i,s in enumerate(slots):s.material_interface=materials['Dry'];slots[i]=s
 mesh.set_editor_property('static_materials',slots)
 E.set_metadata_tag(mesh,'PKM23_Source','Motion21 receiver; contoured cover-mounted adapter')
 E.set_metadata_tag(mesh,'WeaponFinishReference',body_material);save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

# Merge only this new pair into the existing PKM table.
table=u.load_asset(P+'/Finish20/DA_PKM_WetMaterials')
mapping=dict(table.get_editor_property('wet_materials'));mapping[materials['Dry'].get_path_name()]=materials['Wet']
table.set_editor_property('wet_materials',mapping);save(table)
b=mesh.get_bounds()
report={'asset':mesh.get_path_name(),'saved':True,'size_cm':list((b.box_extent*2).to_tuple()),
 'actual_slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials],
 'reference':body_material,'wet':materials['Wet'].get_path_name(),'weather_table':table.get_path_name(),
 'compiler_errors':compilation,'game_tested':False}
(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('PKM23_MOUNT_SAVED',json.dumps(report))
