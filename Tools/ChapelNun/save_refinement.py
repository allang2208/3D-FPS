"""Import R4 surfaces, native-donor grooms and bindings without changing shared assets."""
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_assets.py').read_text(encoding='utf-8-sig')
exec(compile(base.split('E.make_directory(DEST)')[0],'<nun asset helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/RefinementR4';O=R/'Authored';DEST='/Game/Characters/ChapelNun20261115/RefinementR4'
receipt_path=R/'saved_assets.json';receipt=read(receipt_path) if receipt_path.exists() else {'assets':{},'completed':False,'runtime_tested':False}
E.make_directory(DEST);ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def import_texture(channel):
 name='T_Nun_Neck_'+channel;path=DEST+'/Textures/'+name;obj=u.load_asset(path)
 task=u.AssetImportTask();task.filename=str(O/'Textures'/('Neck_'+channel+'.png'));task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;A.import_asset_tasks([task]);obj=load(path)
 obj.set_editor_property('srgb',channel=='base_color');obj.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if channel=='base_color' else u.TextureCompressionSettings.TC_MASKS)
 obj.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER);return save(obj)
neck=new('M_Nun_MatchedNeck','Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(neck)
L.set_material_usage(neck,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);neck.set_editor_property('two_sided',True)
for ch in ('base_color','metallic_roughness'):
 sample=node(neck,u.MaterialExpressionTextureSample,texture=import_texture(ch),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='base_color' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 if ch=='base_color':prop(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR)
 else:prop(sample,'G',u.MaterialProperty.MP_ROUGHNESS);prop(sample,'B',u.MaterialProperty.MP_METALLIC)
prop(constant(neck,.5),'',u.MaterialProperty.MP_SPECULAR);L.recompile_material(neck);save(neck)
original=load('/Game/Characters/ChapelNun20261115/OriginalMeshyFaceR3/Materials/M_Nun_OriginalMeshy')
head=skeletal('head.json','SK_Nun_OriginalMeshyFace_Final',[original,neck,original])
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
policy=u.load_asset(DEST+'/Meshes/DA_NunFaceLOD') or A.create_asset('DA_NunFaceLOD',DEST+'/Meshes',u.SkeletalMeshLODSettings,factory)
groups=[]
for ratio,screen in ((1.,1.),(.70,.18),(.42,.065)):
 group=u.SkeletalMeshLODGroupSettings();red=group.get_editor_property('reduction_settings')
 for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():red.set_editor_property(key,value)
 group.set_editor_property('reduction_settings',red);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
policy.set_editor_property('lod_groups',groups);head.set_editor_property('lod_settings',policy)
models=list(head.get_editor_property('source_models'))
for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
head.set_editor_property('source_models',models);save(policy);ss.regenerate_lod(head,3,True,False)
head.set_editor_property('positive_bounds_extension',u.Vector(3,12,3));head.set_editor_property('negative_bounds_extension',u.Vector(3,3,7))
shadow=[]
for lod in range(ss.get_lod_count(head)):
 for section in range(ss.get_num_sections(head,lod)):
  if ss.get_lod_material_slot(head,lod,section)==2:
   if not ss.set_section_cast_shadow(head,lod,section,False):raise RuntimeError('Fine surface shadow policy failed')
   shadow.append([lod,section])
save(head);receipt['fine_surface_shadow_exclusions']=shadow;record()

trim=skeletal('trim.json','SK_Nun_CollarCross_Final',[load('/Game/Characters/ChapelNun20261115/Materials/M_Nun_IvoryLinen'),load('/Game/Characters/ChapelNun20261115/Materials/M_Nun_BlackWool'),load('/Game/Characters/ChapelNun20261115/Materials/M_Nun_WornIron')])
stock=new('M_Nun_BlackStockings','Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(stock);L.set_material_usage(stock,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
stock.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH);stock.set_editor_property('use_material_attributes',True)
attrs=node(stock,u.MaterialExpressionMakeMaterialAttributes)
wire(color(stock,(.013,.014,.016)),attrs,'BaseColor');wire(constant(stock,.86),attrs,'Roughness')
wire(color(stock,(.013,.014,.016)),attrs,'SubsurfaceColor');wire(constant(stock,.15),attrs,'ClearCoat')
norm=node(stock,u.MaterialExpressionTextureSample,texture=load('/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/Textures/T_BlueMageFabric_Normal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
wire(norm,attrs,'Normal','RGB');prop(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES);L.recompile_material(stock);save(stock)
boot_src=read(R/'Inputs/current_boots.json')
boots=skeletal('boots.json','SK_Nun_Boots',[load(m['asset']) for m in boot_src['materials']]+[stock])

hair_source=load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/MI_WI_Hair_L_Straight_Hair')
hair_mat=u.load_asset(DEST+'/Materials/MI_Nun_Hair') or A.duplicate_asset('MI_Nun_Hair',DEST+'/Materials',hair_source)
# Preserve native dual-lobe highlights and fine/rough strand variation; neutral black pigment.
for key,value in {'hairMelanin':.76,'hairRedness':.025,'MelaninVariationFine':.45,'MelaninVariationRough':.20}.items():L.set_material_instance_scalar_parameter_value(hair_mat,key,value)
L.set_material_instance_vector_parameter_value(hair_mat,'hairDye',u.LinearColor(.42,.44,.46,1));L.update_material_instance(hair_mat);save(hair_mat)
reference=load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/Hair_L_Straight')
grooms=[]
for name,simulate in [('Nun_LowBun_Core_R4',False),('Nun_LowBun_Loose_R4',True)]:
 asset,binding=groom(name,head,simulate,hair_mat)
 render=reference.get_editor_property('hair_groups_rendering')[0]
 geom=render.get_editor_property('geometry_settings');geom.set_editor_property('hair_width',.0075 if not simulate else .0055);geom.set_editor_property('hair_tip_scale',.18);render.set_editor_property('geometry_settings',geom)
 asset.set_editor_property('hair_groups_rendering',[render])
 lod=asset.get_editor_property('hair_groups_lod')[0];lod.import_text('(LODs=((ScreenSize=1.0,GeometryType=Strands),(CurveDecimation=0.65,VertexDecimation=0.75,ScreenSize=0.15,ThicknessScale=1.15,GeometryType=Strands),(CurveDecimation=0.30,VertexDecimation=0.55,ScreenSize=0.045,ThicknessScale=1.45,GeometryType=Strands,Simulation=Disable)))');asset.set_editor_property('hair_groups_lod',[lod]);save(asset);grooms.append(asset)
if not u.ChapelNunQualityCommandlet.apply_refined_root_uv():raise RuntimeError('Native root UV restoration failed')
for part,asset in zip(('Core','Loose'),grooms):
 save(asset);name='Nun_LowBun_'+part+'_Final_Binding';binding=u.load_asset(DEST+'/Grooms/'+name)
 if not binding:binding=u.GroomLibrary.create_new_groom_binding_asset_with_path(DEST+'/Grooms/'+name,asset,head,100,None,0)
 save(binding);receipt['assets'][name]=binding.get_path_name();record()
receipt.update(completed=True,materials=[original.get_path_name(),neck.get_path_name(),hair_mat.get_path_name()],native_groom_effect_source=reference.get_path_name(),original_face_geometry_preserved=True,original_face_textures_preserved=True)
record();print('NUN_REFINEMENT_ASSETS_SAVED',flush=True)
import runpy
runpy.run_path(str(P/'Tools/ChapelNun/save_final_head.py'))
runpy.run_path(str(P/'Tools/ChapelNun/save_final_collar.py'))
runpy.run_path(str(P/'Tools/ChapelNun/save_final_boots.py'))
