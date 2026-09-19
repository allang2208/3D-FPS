"""AKM-only material built from the acquired Fab Quixel Dirty Metal scan."""
import unreal as u,json
from pathlib import Path
dest='/Game/Weapons/AKMIntegration/SourceMatched'
lib=u.MaterialEditingLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
tex=u.load_asset('/Game/ColdSteelUI/Warehouse20260909/DirtyMetal/T_DirtyMetal_MR_4K')
assert tex
mat=u.load_asset(dest+'/M_AKM_FabGunsteel')
if not mat: mat=assets.create_asset('M_AKM_FabGunsteel',dest,u.Material,u.MaterialFactoryNew())
lib.delete_all_material_expressions(mat)
lib.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
def node(cls,**props):
 n=lib.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,o,b,p):assert lib.connect_material_expressions(a,o,b,p)
uv=node(u.MaterialExpressionTextureCoordinate,u_tiling=3.0,v_tiling=3.0)
t=node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
wire(uv,'',t,'UVs')
rough=node(u.MaterialExpressionMultiply,const_b=.20);wire(t,'G',rough,'A')
roughadd=node(u.MaterialExpressionAdd,const_b=.28);wire(rough,'',roughadd,'A')
tint=node(u.MaterialExpressionVectorParameter,parameter_name='GunsteelTint',default_value=u.LinearColor(.075,.085,.10,1))
dirt=node(u.MaterialExpressionMultiply,const_b=.18);wire(t,'R',dirt,'A')
clean=node(u.MaterialExpressionOneMinus);wire(dirt,'',clean,'')
color=node(u.MaterialExpressionMultiply);wire(tint,'',color,'A');wire(clean,'',color,'B')
metal=node(u.MaterialExpressionConstant,r=.95)
for n,p in [(color,u.MaterialProperty.MP_BASE_COLOR),(roughadd,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)]:assert lib.connect_material_property(n,'',p)
lib.recompile_material(mat)
assert u.EditorAssetLibrary.save_loaded_asset(mat,False)
mesh=u.load_asset(dest+'/SK_AKM_MannyNative')
current=u.load_asset('/Game/Weapons/AKMIntegration/Materials/SK_AKM_MannyNative')
slots=mesh.get_editor_property('materials');old=current.get_editor_property('materials')
assert len(slots)==len(old)
for i,s in enumerate(slots):
 s.material_interface=mat if i in [0,3,4] else old[i].material_interface
 slots[i]=s
mesh.set_editor_property('materials',slots)
assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
report={'source':'https://www.fab.com/listings/17d58a5d-f1a8-4417-9e6f-f21ed6fc7031','category':'Quixel imperfection scan, not a complete steel basecolor set','texture':tex.get_path_name(),'material':mat.get_path_name(),'roughness':'0.28 + G * 0.20','dirt':'R * 0.18','metallic':.95,'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]}
(Path(__file__).parent/'SourceMatched/fab_material.json').write_text(json.dumps(report,indent=2))
u.log('AKM_FAB_GUNSTEEL_PASS')
