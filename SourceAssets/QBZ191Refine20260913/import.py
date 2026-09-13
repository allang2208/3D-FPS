"""Import authored sequences and repair the disconnected roughness graph."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/QBZ191';DEST=P+'/Refined20260913';A=u.AssetToolsHelpers.get_asset_tools();lib=u.MaterialEditingLibrary
mesh=u.load_asset(P+'/Calibrated/SK_QBZ191_Manny');materials={}
for part,texpart in [('Body','Body'),('Magazine','Magazine'),('Irons','Body')]:
 name='M_QBZ191_'+part+'_Refined';path=DEST+'/Materials/'+name
 m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 lib.delete_all_material_expressions(m);lib.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 def node(cls):return lib.create_material_expression(m,cls)
 def constant(value):n=node(u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
 def wire(a,out,b,pin):
  if not lib.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed: '+b.get_name()+' / '+pin)
 for kind,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Normal',u.MaterialProperty.MP_NORMAL)]:
  tex=u.load_asset(P+'/Textures/T_QBZ191_'+texpart+'_'+kind);n=node(u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
  n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
  output='RGB' if kind in ['BaseColor','Normal'] else 'R'
  if kind=='Roughness':
   mul=node(u.MaterialExpressionMultiply);wire(n,'R',mul,'A');wire(constant(.8),'',mul,'B')
   add=node(u.MaterialExpressionAdd);wire(mul,'',add,'A');wire(constant(.06),'',add,'B')
   clamp=node(u.MaterialExpressionClamp);wire(add,'',clamp,'')
   clamp.set_editor_property('min_default',.38 if part=='Irons' else .28);clamp.set_editor_property('max_default',.78);n=clamp;output=''
  elif kind=='Normal':
   flat=node(u.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',u.LinearColor(0,0,1,1))
   blend=node(u.MaterialExpressionLinearInterpolate);wire(flat,'',blend,'A');wire(n,'RGB',blend,'B');wire(constant(.65 if part=='Irons' else .85),'',blend,'Alpha');n=blend;output=''
  if not lib.connect_material_property(n,output,prop):raise RuntimeError('Material property connection failed')
 lib.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m,False);materials[part]=m
slots=mesh.materials
for i,slot in enumerate(slots):
 name=str(slot.material_slot_name)
 if 'QBZ191' in name:slot.material_interface=materials['Irons' if 'Irons' in name else 'Magazine' if 'Magazine' in name else 'Body'];slots[i]=slot
mesh.set_editor_property('materials',slots);u.EditorAssetLibrary.save_loaded_asset(mesh,False)
build=json.loads((O/'build.json').read_text());report={}
for key,info in build.items():
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['sample_rate'])
 dest=DEST+'/Animations/'+info['family'];task=u.AssetImportTask();task.filename=info['file'];task.destination_path=dest;task.destination_name=info['name'];task.options=opt;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
 clip=u.load_asset(dest+'/'+info['name'])
 if not clip:raise RuntimeError('Animation import failed: '+key)
 clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
 if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed: '+key)
 report[key]={'asset':clip.get_path_name(),'source':info['file']};(O/'import.json').write_text(json.dumps(report,indent=2));u.log('QBZ_IMPORTED '+key)
u.log('QBZ_REFINED_IMPORT_COMPLETE')
