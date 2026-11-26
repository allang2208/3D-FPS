"""Save the nun's native-bound head, black robe, trim and separate simulated groom."""
import json,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/ProductionR1';O=R/'Authored'
DEST='/Game/Characters/ChapelNun20261115'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
meta=read(R/'Inputs/native_recipe.json')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
receipt_path=R/'saved_assets.json';receipt=read(receipt_path) if receipt_path.exists() else {'completed':False,'assets':{},'runtime_tested':False}
def record():receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(obj):
 if not obj or not obj.get_path_name().startswith(DEST+'/'):raise RuntimeError('Unowned output')
 if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
 return obj
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing '+path)
 return obj
def new(name,folder,cls,factory):
 return u.load_asset(DEST+'/'+folder+'/'+name) or A.create_asset(name,DEST+'/'+folder,cls,factory)
def node(mat,cls,**props):
 n=L.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Shader connection '+pin)
def pin(name):
 p=u.CustomInput();p.set_editor_property('input_name',name);return p
def prop(a,output,p):
 if not L.connect_material_property(a,output,p):raise RuntimeError('Shader output '+str(p))
def constant(mat,v):return node(mat,u.MaterialExpressionConstant,r=v)
def color(mat,v):return node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
def simple(name,rgb,rough,metal=0):
 mat=new(name,'Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
 L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 prop(color(mat,rgb),'',u.MaterialProperty.MP_BASE_COLOR);prop(constant(mat,rough),'',u.MaterialProperty.MP_ROUGHNESS);prop(constant(mat,metal),'',u.MaterialProperty.MP_METALLIC)
 L.recompile_material(mat);return save(mat)
def cloth(name,ivory=False,skirt=False,lining=False):
 mat=new(name,'Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
 mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH);mat.set_editor_property('use_material_attributes',True)
 mat.set_editor_property('two_sided',skirt);mat.set_editor_property('max_world_position_offset_displacement',.30)
 L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_CLOTHING)
 uv=node(mat,u.MaterialExpressionTextureCoordinate)
 cu=node(mat,u.MaterialExpressionCustom,code='return float2(UV.x*lerp(90.,205.,saturate(UV.y))/4.,(1-UV.y)*85.38/4.);' if skirt else 'return UV*6.25;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT2)
 cu.set_editor_property('inputs',[pin('UV')]);wire(uv,cu,'UV')
 normal_tex=load('/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/Textures/T_BlueMageFabric_Normal')
 orm_tex=load('/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/Textures/T_BlueMageFabric_ORM')
 norm=node(mat,u.MaterialExpressionTextureSample,texture=normal_tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 orm=node(mat,u.MaterialExpressionTextureSample,texture=orm_tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 wire(cu,norm,'UVs');wire(cu,orm,'UVs')
 attrs=node(mat,u.MaterialExpressionMakeMaterialAttributes)
 tint=color(mat,(.66,.63,.56) if ivory else (.011,.0105,.010) if lining else (.018,.017,.016))
 variation=node(mat,u.MaterialExpressionMultiply,const_b=.26);wire(orm,variation,'A','R')
 lift=node(mat,u.MaterialExpressionAdd,const_b=.74);wire(variation,lift,'A')
 base=node(mat,u.MaterialExpressionMultiply);wire(tint,base,'A');wire(lift,base,'B')
 wire(base,attrs,'BaseColor');wire(norm,attrs,'Normal','RGB');wire(orm,attrs,'AmbientOcclusion','R')
 wire(constant(mat,.90 if lining else .84),attrs,'Roughness');wire(constant(mat,0),attrs,'Metallic');wire(constant(mat,.22),attrs,'Specular')
 wire(constant(mat,.16 if ivory else .26),attrs,'ClearCoat');wire(tint,attrs,'SubsurfaceColor')
 if not skirt:
  # Matched outer/inner cuff lag from the established two-hand spring.
  position=node(mat,u.MaterialExpressionPreSkinnedPosition)
  bones={x['name']:x for x in read(R/'Inputs/native_robe.json')['bones']}
  def field(previous):
   inputs={'P':position}
   for side in ['Left','Right']:
    inputs[side]=node(mat,u.MaterialExpressionVectorParameter,parameter_name='CuffLag'+('Previous' if previous else '')+side,default_value=u.LinearColor(0,0,0,0))
   left=bones['hand_l']['position'];right=bones['hand_r']['position']
   code='float wl=1-smoothstep(2.5,16.,distance(P,float3(%s)));float wr=1-smoothstep(2.5,16.,distance(P,float3(%s)));return Left*wl+Right*wr;'%(','.join(str(v) for v in left),','.join(str(v) for v in right))
   c=node(mat,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
   c.set_editor_property('inputs',[pin(k) for k in inputs])
   for k,v in inputs.items():wire(v,c,k,'RGB' if k!='P' else '')
   return c
  switch=node(mat,u.MaterialExpressionPreviousFrameSwitch);wire(field(False),switch,'Current Frame');wire(field(True),switch,'Previous Frame');wire(switch,attrs,'WorldPositionOffset')
 prop(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES);L.recompile_material(mat);return save(mat)
def texture(channel):
 name='T_NunHead_'+channel;path=DEST+'/Textures/'+name
 obj=u.load_asset(path)
 if obj:return obj
 task=u.AssetImportTask();task.filename=str(P/'SourceAssets/ChapelNun20261115/MeshyHeadR1/Source'/('NunHead_R1_M00_'+channel+'.png'))
 task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.save=False
 A.import_asset_tasks([task]);obj=load(path);obj.set_editor_property('srgb',channel=='base_color')
 obj.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='normal' else u.TextureCompressionSettings.TC_DEFAULT if channel=='base_color' else u.TextureCompressionSettings.TC_MASKS)
 if channel=='normal':obj.set_editor_property('flip_green_channel',True)
 return save(obj)
def skin():
 mat=new('M_NunSkin','Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
 L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
 for channel,p in [('base_color',u.MaterialProperty.MP_BASE_COLOR),('normal',u.MaterialProperty.MP_NORMAL),('roughness',u.MaterialProperty.MP_ROUGHNESS)]:
  tex=texture(channel);n=node(mat,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='base_color' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  prop(n,'RGB' if channel!='roughness' else 'R',p)
 prop(constant(mat,0),'',u.MaterialProperty.MP_METALLIC);prop(constant(mat,.28),'',u.MaterialProperty.MP_SPECULAR)
 prop(color(mat,(.33,.13,.09)),'',u.MaterialProperty.MP_SUBSURFACE_COLOR);prop(constant(mat,.12),'',u.MaterialProperty.MP_OPACITY)
 L.recompile_material(mat);return save(mat)
def skeletal(file,name,mats):
 path=DEST+'/Meshes/'+name
 if name in receipt['assets']:return load(receipt['assets'][name])
 d=read(O/file);source=load(d['binding_source'])
 ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Binding source unavailable')
 ps=[];ns=[];uvs=[];ws=[];faces=[];lookup={}
 for fi,t in enumerate(d['triangles']):
  tri=[]
  for ci,vi in enumerate(t):
   n=d['normals'][fi][ci];uv=d['uv'][fi][ci];key=(vi,*[round(v,6) for v in n+uv])
   if key not in lookup:
    lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*n));uvs.append(u.Vector2D(*uv));ws.append(d['weights'][vi])
   tri.append(lookup[key])
  faces.append(u.IntVector(*tri))
 dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uvs,triangles=faces),0,True)
 B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
 for i,weights in enumerate(ws):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=int(b),weight=float(w)) for b,w in weights])
 for i,mi in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,mi,True)
 opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions();opts.use_mesh_bone_proportions=True;opts.enable_recompute_normals=False;opts.enable_recompute_tangents=True
 opts.materials={slot:mat for slot,mat in zip(d['material_slots'],mats)}
 obj,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,source.skeleton,path,opts)
 if status!=u.GeometryScriptOutcomePins.SUCCESS or not obj:raise RuntimeError('Cannot save skinned '+name)
 # Preserve full authored LOD0. Use the established distant outfit LOD policy.
 u.FPSModularOutfitComponent.configure_outfit_lods(obj)
 ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);ss.regenerate_lod(obj,3,True,False)
 obj.set_editor_property('physics_asset',source.physics_asset)
 save(obj);receipt['assets'][name]=obj.get_path_name();record();print('NUN_SKELETAL_SAVED',name,flush=True)
 return obj
def duplicate(source,name):
 if name in receipt['assets']:return load(receipt['assets'][name])
 obj=u.load_asset(DEST+'/Meshes/'+name) or A.duplicate_asset(name,DEST+'/Meshes',load(source))
 save(obj);receipt['assets'][name]=obj.get_path_name();record();return obj
def groom(name,head,simulate,hair_mat):
 if name in receipt['assets']:return load(receipt['assets'][name]),load(receipt['assets'][name+'_Binding'])
 path=DEST+'/Grooms/'+name
 asset=u.load_asset(path)
 if not asset or name not in receipt['assets']:
  task=u.AssetImportTask();task.filename=str(O/(name+'.abc'));task.destination_path=DEST+'/Grooms';task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.factory=u.HairStrandsFactory()
  options=u.GroomImportOptions();conversion=options.get_editor_property('conversion_settings');conversion.set_editor_property('rotation',u.Vector(-90,0,0));conversion.set_editor_property('scale',u.Vector(1,1,1));options.set_editor_property('conversion_settings',conversion)
  task.options=options;A.import_asset_tasks([task]);asset=load(path)
 reference=load(meta['hair_reference'])
 physical=reference.get_editor_property('hair_groups_physics')[0]
 solver=physical.get_editor_property('solver_settings');solver.set_editor_property('enable_simulation',simulate);solver.set_editor_property('sub_steps',6);solver.set_editor_property('iteration_count',8);physical.set_editor_property('solver_settings',solver)
 forces=physical.get_editor_property('external_forces');forces.set_editor_property('air_drag',.65);physical.set_editor_property('external_forces',forces)
 constraints=physical.get_editor_property('material_constraints');collision=constraints.get_editor_property('collision_constraint');collision.set_editor_property('collision_radius',.18);constraints.set_editor_property('collision_constraint',collision)
 bend=constraints.get_editor_property('bend_constraint');bend.set_editor_property('bend_stiffness',.22);bend.set_editor_property('bend_damping',.12);constraints.set_editor_property('bend_constraint',bend);physical.set_editor_property('material_constraints',constraints)
 asset.set_editor_property('hair_groups_physics',[physical])
 render=reference.get_editor_property('hair_groups_rendering')[0];geom=render.get_editor_property('geometry_settings');geom.set_editor_property('hair_width',.009 if simulate else .0105);geom.set_editor_property('hair_tip_scale',.20);render.set_editor_property('geometry_settings',geom)
 hair_slots=list(reference.get_editor_property('hair_groups_materials'))
 for hair_slot in hair_slots:hair_slot.set_editor_property('material',hair_mat)
 asset.set_editor_property('hair_groups_materials',hair_slots)
 asset.set_editor_property('hair_groups_rendering',[render])
 groups=asset.get_editor_property('hair_groups_lod');lodgroup=groups[0]
 lodgroup.import_text('(LODs=((ScreenSize=1.0,GeometryType=Strands),(CurveDecimation=0.50,VertexDecimation=0.65,ScreenSize=0.18,GeometryType=Strands),(CurveDecimation=0.18,VertexDecimation=0.40,ScreenSize=0.06,GeometryType=Strands,Simulation=Disable)))')
 asset.set_editor_property('hair_groups_lod',[lodgroup]);save(asset)
 binding=u.GroomLibrary.create_new_groom_binding_asset_with_path(DEST+'/Grooms/'+name+'_Binding',asset,head,100,None,0)
 save(binding);receipt['assets'][name]=asset.get_path_name();receipt['assets'][name+'_Binding']=binding.get_path_name();record();print('NUN_GROOM_SAVED',name,simulate,flush=True)
 return asset,binding
E.make_directory(DEST)
black=cloth('M_Nun_BlackWool');lining=cloth('M_Nun_Lining',lining=True);skirt=cloth('M_Nun_Skirt',skirt=True);ivory=cloth('M_Nun_IvoryLinen',ivory=True)
iron=simple('M_Nun_WornIron',(.11,.10,.085),.48,.8);button=simple('M_Nun_HornButton',(.012,.010,.008),.62)
robe=duplicate(meta['robe'],'SK_Nun_BlackRobe')
slots=list(robe.materials)
for slot in slots:
 label=str(slot.material_slot_name);slot.material_interface=skirt if label=='RobeSkirt' else lining if label in ('SleeveLining','TorsoLining','RobeSimulationProxy') else iron if label=='RobeSilver' else button if label=='RobeGem' else black
robe.set_editor_property('materials',slots);save(robe)
receipt['cloth']={'source':meta['robe'],'assets':len(robe.mesh_clothing_assets),'female_collision_preserved':True,'cuff_inertia_material':True};record()
body=duplicate(meta['body'],'SK_Nun_Body')
boots_source=next(v for k,v in meta['underlayers'].items() if 'SK_Kaitlin_ue_leather_boots_b715b16a.' in k)
boots=duplicate(boots_source,'SK_Nun_Boots')
head=skeletal('head.json','SK_Nun_Head',[skin(),load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/Materials/MI_Face_Skin_Baked_LOD1')])
head.set_editor_property('positive_bounds_extension',u.Vector(3,12,3))
head.set_editor_property('negative_bounds_extension',u.Vector(3,3,7))
save(head)
trim=skeletal('trim.json','SK_Nun_CollarCross',[ivory,black,iron])
hair_source=load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/MI_WI_Hair_L_Straight_Hair')
hair_mat=u.load_asset(DEST+'/Materials/MI_Nun_Hair') or A.duplicate_asset('MI_Nun_Hair',DEST+'/Materials',hair_source)
for key,value in {'hairMelanin':.90,'hairRedness':0.0,'HairRoughness':.46,'Roughness':.46}.items():
 L.set_material_instance_scalar_parameter_value(hair_mat,key,value)
L.set_material_instance_vector_parameter_value(hair_mat,'hairDye',u.LinearColor(.025,.025,.025,1))
save(hair_mat)
groom('Nun_LowBun_Core',head,False,hair_mat)
groom('Nun_LowBun_Loose',head,True,hair_mat)
receipt['idle']=meta['idle'];receipt['covers']=meta['covers'];receipt['completed']=True;record();print('NUN_ASSETS_SAVED',flush=True)
