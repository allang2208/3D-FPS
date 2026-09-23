"""Import/save only the new PKM subtree through the project's editor bridge."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R=O.parent;P='/Game/Weapons/PKMLowpoly20260922'
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'saved':[],'complete':False};materials={};textures={}
def save(asset):
 if not asset or not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+str(asset))
 report['saved'].append(asset.get_path_name());(O/'geometry_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def loadfile(file,dest,name,options=None):
 existing=u.load_asset(dest+'/'+name)
 if existing and str(file).endswith('.png'):return existing
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
 if options:task.options=options;task.factory=u.FbxFactory();task.replace_existing_settings=True
 flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
 try:
  if options:u.SystemLibrary.execute_console_command(None,flag+' 0')
  A.import_asset_tasks([task])
 finally:
  if options:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
 asset=u.load_asset(dest+'/'+name)
 if not asset:raise RuntimeError('Import failed: '+name)
 return asset
donor=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
if not donor:raise RuntimeError('Current Manny material donor is unavailable')
bindings={str(slot.material_slot_name):slot.material_interface for slot in donor.get_editor_property('materials')}
settings=json.loads((R/'finish_settings.json').read_text(encoding='utf-8'))['materials']
interior=dict(next(x for x in settings if x['name']=='PKM_BluedSteel'));interior['name']='PKM_InteriorSteel';interior['roughness']=.52;settings.append(interior)
for file in (R/'Refinement01/Textures').glob('*.png'):
 channel=file.stem.rsplit('_',1)[1];tex=loadfile(file,P+'/Textures','T_'+file.stem)
 tex.set_editor_property('srgb',channel=='BaseColor')
 if channel=='Normal':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
 elif channel=='Roughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
 save(tex);textures[file.stem]=tex
def link(node,out,prop):
 if not M.connect_material_property(node,out,prop):raise RuntimeError('Material connection failed: '+str(prop))
for spec in settings:
 name=spec['name'];path=P+'/Materials/M_'+name
 mat=u.load_asset(path)
 if not mat:
  mat=A.create_asset('M_'+name,P+'/Materials',u.Material,u.MaterialFactoryNew());M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
  for channel,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Normal',u.MaterialProperty.MP_NORMAL)]:
   base='PKM_BluedSteel' if name=='PKM_InteriorSteel' else name
   if name=='PKM_InteriorSteel' and channel=='Roughness':
    n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',.52);link(n,'',prop);continue
   n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[base+'_'+channel])
   n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
   if channel=='Normal':
    flat=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',u.LinearColor(0,0,1,1))
    mix=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate);mix.set_editor_property('const_alpha',.3)
    M.connect_material_expressions(flat,'',mix,'A');M.connect_material_expressions(n,'RGB',mix,'B')
    normalize=M.create_material_expression(mat,u.MaterialExpressionNormalize);M.connect_material_expressions(mix,'',normalize,'VectorInput');link(normalize,'',prop)
   else:link(n,'RGB' if channel=='BaseColor' else 'R',prop)
  metal=M.create_material_expression(mat,u.MaterialExpressionConstant);metal.set_editor_property('r',spec['metallic']);link(metal,'',u.MaterialProperty.MP_METALLIC)
  M.recompile_material(mat)
 save(mat);materials[name]=mat
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
opt.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
# This is a private PKM skeleton: update its rest axes together with the mesh.
opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',True)
existing_mesh=u.load_asset(P+'/SK_PKM_Manny')
if existing_mesh:opt.skeleton=existing_mesh.skeleton
# A separate skeleton contains the PKM mechanical tracks; never extend the M4 skeleton.
mesh=loadfile(O/'Exports/SK_PKM_Manny.fbx',P,'SK_PKM_Manny',opt)
slots=mesh.get_editor_property('materials');mapping={}
for i,slot in enumerate(slots):
 name=str(slot.material_slot_name);base=name.split('__')[0].split('.')[0];material=materials.get(base) or bindings.get(name) or bindings.get(base)
 if not material:raise RuntimeError('Missing PKM material binding: '+name+' donor='+str(list(bindings)))
 slot.material_interface=material;slots[i]=slot;mapping[name]=material.get_path_name()
mesh.set_editor_property('materials',slots);save(mesh);save(mesh.skeleton)
report.update(complete=True,mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),bindings=mapping,tested=False)
(O/'geometry_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8');u.log('PKM geometry and materials saved.')
