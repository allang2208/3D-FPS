import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/WalnutFab';lib=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
runtime='/Game/Weapons/AKMIntegration/SourceMatched/SK_AKM_MannyNative'
old=u.load_asset(runtime);assert old
bindings={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('materials')}
if not u.EditorAssetLibrary.does_asset_exist(P+'/SK_AKM_BeforeWalnut'):assert u.EditorAssetLibrary.duplicate_asset(runtime,P+'/SK_AKM_BeforeWalnut')
textures={}
for kind,srgb,comp in [('BaseColor',True,u.TextureCompressionSettings.TC_DEFAULT),('Normal',False,u.TextureCompressionSettings.TC_NORMALMAP),('Roughness',False,u.TextureCompressionSettings.TC_GRAYSCALE)]:
 t=u.AssetImportTask();t.filename=str(O/'Source/walnut_veneer_tfdoebqc_4_extracted'/f'Walnut_Veneer_tfdoebqc_4K_{kind}.jpg');t.destination_path=P+'/Textures';t.destination_name='T_AKM_Walnut_'+kind;t.automated=True;t.save=True;t.replace_existing=True
 assets.import_asset_tasks([t]);tex=u.load_asset(t.imported_object_paths[0]);tex.set_editor_property('srgb',srgb);tex.set_editor_property('compression_settings',comp);u.EditorAssetLibrary.save_loaded_asset(tex,False);textures[kind]=tex
m=u.load_asset(P+'/M_AKM_SatinWalnut') if u.EditorAssetLibrary.does_asset_exist(P+'/M_AKM_SatinWalnut') else assets.create_asset('M_AKM_SatinWalnut',P,u.Material,u.MaterialFactoryNew())
lib.delete_all_material_expressions(m);lib.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
def node(cls,**props):
 n=lib.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,out,b,pin):assert lib.connect_material_expressions(a,out,b,pin)
samples={}
for kind,tex in textures.items():
 n=node(u.MaterialExpressionTextureSample,texture=tex)
 if kind=='Normal':n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 elif kind=='Roughness':n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
 samples[kind]=n
tint=node(u.MaterialExpressionVectorParameter,parameter_name='RedBrownTint',default_value=u.LinearColor(1.25,.75,.55,1))
color=node(u.MaterialExpressionMultiply);wire(samples['BaseColor'],'RGB',color,'A');wire(tint,'',color,'B')
rough=node(u.MaterialExpressionMultiply,const_b=.12);wire(samples['Roughness'],'R',rough,'A');add=node(u.MaterialExpressionAdd,const_b=.30);wire(rough,'',add,'A')
normal=node(u.MaterialExpressionLinearInterpolate,const_alpha=.06);flat=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1));wire(flat,'',normal,'A');wire(samples['Normal'],'RGB',normal,'B')
coat=node(u.MaterialExpressionConstant,r=.18);coatrough=node(u.MaterialExpressionConstant,r=.30)
for n,p in [(color,u.MaterialProperty.MP_BASE_COLOR),(add,u.MaterialProperty.MP_ROUGHNESS),(normal,u.MaterialProperty.MP_NORMAL)]:assert lib.connect_material_property(n,'',p)
lib.layout_material_expressions(m);lib.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m,False)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=old.skeleton
t=u.AssetImportTask();t.filename=str(O/'SK_AKM_MannyNative.fbx');t.destination_path=P;t.destination_name='SK_AKM_MannyNative';t.automated=True;t.replace_existing=True;t.save=True;t.options=opt;assets.import_asset_tasks([t])
mesh=u.load_asset(P+'/SK_AKM_MannyNative');assert mesh and mesh.skeleton==old.skeleton
slots=mesh.get_editor_property('materials');assert len(slots)==len(bindings)
for i,s in enumerate(slots):
 name=str(s.material_slot_name);assert name in bindings,name;s.material_interface=m if name=='M_AKMR_Walnut' else bindings[name];slots[i]=s
mesh.set_editor_property('materials',slots);assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
# Runtime now selects this isolated WalnutFab mesh while retaining SourceMatched animations.
report={'mesh':mesh.get_path_name(),'source':'https://www.fab.com/listings/67d7d60c-e92a-4fd9-8994-787f121aeaf9','materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in slots],'tint':[1.25,.75,.55],'roughness':'0.30+R*0.12','normal_strength':.06,'finish':'Default Lit satin dielectric','source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (O/'Source/walnut_veneer_tfdoebqc_4_extracted').glob('*.jpg')}}
(O/'applied.json').write_text(json.dumps(report,indent=2));u.log('AKM_WALNUT_FAB_PASS')

