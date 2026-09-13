"""Author QBZ-only material variants and install fitted attachment meshes."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/QBZ191/Attachments20260913';OLD='/Game/Weapons/QBZ191/ContactWear20260913'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
sources=json.loads((O/'sources.json').read_text());models=json.loads((O/'models.json').read_text());cache={};report={'materials':{},'meshes':{}}
reference=u.load_asset(OLD+'/SK_QBZ191_Manny')
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def duplicate(source,path):
 if E.does_asset_exist(path):return u.load_asset(path)
 result=E.duplicate_asset(source,path)
 if not result:raise RuntimeError('Copy failed: '+source)
 return result
def node(mat,cls,**props):
 n=L.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(n,out,target,pin):
 pins=[str(x) for x in L.get_material_expression_input_names(target)]
 if pin=='Input' and pin not in pins:pin=pins[0]
 if not L.connect_material_expressions(n,out,target,pin):raise RuntimeError('Cannot connect '+str((n.get_name(),out,L.get_material_expression_output_names(n),target.get_name(),pin,pins)))
def output(n,out,prop):
 if not L.connect_material_property(n,out,prop):raise RuntimeError('Cannot write '+str(prop))
def scalar(mat,value):return node(mat,u.MaterialExpressionConstant,r=value)
def lerp(mat,a,ao,b,bo,alpha):
 n=node(mat,u.MaterialExpressionLinearInterpolate,const_alpha=alpha);link(a,ao,n,'A');link(b,bo,n,'B');return n
def style_for(key,slot):
 low=(key+' '+slot).lower()
 if any(w in low for w in ['glass','reticle','red_dot']) and ('body' not in low):return 'preserve'
 if any(w in low for w in ['recess','index','titaniumtrim']):return 'preserve'
 if 'rubber' in low:return 'rubber'
 if any(w in low for w in ['polymer','magazine','vertical','canted','prism_polymer','angled']):return 'polymer'
 return 'metal'
def harmonize(source,style):
 if style=='preserve':return u.load_asset(source)
 key=source+'|'+style
 if key in cache:return cache[key]
 original=u.load_asset(source)
 if not original:raise RuntimeError('Missing source material: '+source)
 name='M_QBZ191_Unified_'+original.get_name()+'_'+style;path=D+'/Materials/'+name
 if isinstance(original,u.MaterialInstanceConstant):
  base=original.get_base_material();mat=duplicate(base.get_path_name(),path+'_Graph');result=duplicate(source,path)
  # Flatten effective inherited overrides onto the private instance before reparenting.
  values={}
  for kind in ['scalar','vector','texture','static_switch']:
   values[kind]={str(n):getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,n) for n in getattr(L,'get_'+kind+'_parameter_names')(base)}
  L.set_material_instance_parent(result,mat)
  for kind,params in values.items():
   for n,v in params.items():
    if v is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,n,v)
 else:mat=duplicate(source,path);result=mat
 # These assets are built once; rerunning an interrupted import reuses completed graphs.
 if E.get_metadata_tag(mat,'QBZUnifiedSurface')!='20260913':
  bc=L.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
  bc_out=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR)
  if bc:
   target={'metal':(.025,.029,.032),'polymer':(.023,.025,.026),'rubber':(.012,.013,.014)}[style]
   tint=node(mat,u.MaterialExpressionVectorParameter,parameter_name='QBZ_SurfaceTint',default_value=u.LinearColor(*target,1))
   luminance=node(mat,u.MaterialExpressionDesaturation);link(bc,bc_out,luminance,'Input');link(scalar(mat,1.),'',luminance,'Fraction')
   # Keep recessed black surfaces and bright markings; tune the midtone coating.
   low=node(mat,u.MaterialExpressionSmoothStep,const_min=.005,const_max=.024);link(luminance,'',low,'Value')
   high=node(mat,u.MaterialExpressionSmoothStep,const_min=.15,const_max=.40);link(luminance,'',high,'Value')
   inv=node(mat,u.MaterialExpressionOneMinus);link(high,'',inv,'Input')
   mask=node(mat,u.MaterialExpressionMultiply);link(low,'',mask,'A');link(inv,'',mask,'B')
   amount=node(mat,u.MaterialExpressionScalarParameter,parameter_name='QBZ_CoatingBlend',default_value=.32)
   alpha=node(mat,u.MaterialExpressionMultiply);link(mask,'',alpha,'A');link(amount,'',alpha,'B')
   colour=lerp(mat,bc,bc_out,tint,'',.32);link(alpha,'',colour,'Alpha');output(colour,'',u.MaterialProperty.MP_BASE_COLOR)
  rough=L.get_material_property_input_node(mat,u.MaterialProperty.MP_ROUGHNESS);ro=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_ROUGHNESS)
  if not rough:rough=scalar(mat,.5);ro=''
  target=node(mat,u.MaterialExpressionScalarParameter,parameter_name='QBZ_SurfaceRoughness',default_value={'metal':.42,'polymer':.58,'rubber':.80}[style])
  roughness=lerp(mat,rough,ro,target,'',.48 if style!='metal' else .38);output(roughness,'',u.MaterialProperty.MP_ROUGHNESS)
  if style in ['polymer','rubber']:output(scalar(mat,0.),'',u.MaterialProperty.MP_METALLIC)
  L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);E.set_metadata_tag(mat,'QBZUnifiedSurface','20260913');L.recompile_material(mat)
 save(mat)
 if result!=mat:L.update_material_instance(result);save(result)
 cache[key]=result;report['materials'][key]=result.get_path_name();return result

adapter=A.create_asset('M_QBZ191_AdapterMetal',D+'/Materials',u.Material,u.MaterialFactoryNew()) if not E.does_asset_exist(D+'/Materials/M_QBZ191_AdapterMetal') else u.load_asset(D+'/Materials/M_QBZ191_AdapterMetal')
L.delete_all_material_expressions(adapter);output(node(adapter,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.025,.029,.032,1)),'',u.MaterialProperty.MP_BASE_COLOR);output(scalar(adapter,.44),'',u.MaterialProperty.MP_ROUGHNESS);output(scalar(adapter,.75),'',u.MaterialProperty.MP_METALLIC);L.recompile_material(adapter);save(adapter)
def material(key,info):return adapter if info.get('class')=='authored' else harmonize(info['material'],style_for(key,info['slot']))
def import_mesh(name,file,skeletal=False):
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
 opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
 if skeletal:opt.skeleton=reference.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False)
 else:data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 task=u.AssetImportTask();task.filename=file;task.destination_path=D;task.destination_name=name;task.options=opt;task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
 if not mesh:raise RuntimeError('Mesh import failed: '+name)
 return mesh
for key,info in sources.items():
 if key in models['parts']:
  authored=models['parts'][key];mesh=import_mesh(authored['name'],authored['file']);bindings=authored['bindings']
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,material(key,bindings[str(slot.material_slot_name)]))
 else:
  mesh=duplicate(info['source'],D+'/SM_QBZ191_'+key)
  for i,slot in enumerate(info['slots']):mesh.set_material(i,material(key,slot))
 save(mesh);report['meshes'][key]=mesh.get_path_name();(O/'assets_import.json').write_text(json.dumps(report,indent=2));u.log('QBZ_ATTACHMENT_IMPORTED '+key)
bindings={str(m.material_slot_name):m.material_interface for m in reference.materials}
wear={info['material']:harmonize(OLD+'/Materials/'+info['material'],'polymer' if group in ['Polymer','Magazine'] else 'metal') for group,info in json.loads((O.parent/'QBZ191ContactWear20260913/textures.json').read_text()).items()}
mesh=import_mesh('SK_QBZ191_Manny',str(O/'SK_QBZ191_Manny.fbx'),True);slots=mesh.materials
for i,slot in enumerate(slots):
 name=str(slot.material_slot_name);name=models['gun_bindings'].get(name,name)
 # Blender source material names are Wear; previous UE mesh retained Hero slot names.
 if name in wear:mat=wear[name]
 elif name.replace('Hero_','Wear_') in wear:mat=wear[name.replace('Hero_','Wear_')]
 else:mat=bindings[name]
 slot.material_interface=mat;slots[i]=slot
mesh.set_editor_property('materials',slots);save(mesh);report['meshes']['gun']=mesh.get_path_name()
for name in ['SM_QBZ191_RearSight','SM_QBZ191_FrontSight']:
 head=duplicate(OLD+'/'+name,D+'/'+name)
 for i,slot in enumerate(head.static_materials):head.set_material(i,wear['M_QBZ191_Wear_Sights'])
 save(head);report['meshes'][name]=head.get_path_name()
report['status']='Authored and saved, no runtime testing';(O/'assets_import.json').write_text(json.dumps(report,indent=2));u.log('QBZ_ATTACHMENTS_ASSETS_COMPLETE')
