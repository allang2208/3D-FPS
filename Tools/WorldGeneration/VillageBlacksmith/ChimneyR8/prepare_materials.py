import unreal as u
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
dest='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR8/Materials'
name='M_ChimneyFlueSoot';path=dest+'/'+name
m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
m.modify();L.delete_all_material_expressions(m);m.set_editor_property('used_with_instanced_static_meshes',True)
def node(c):return L.create_material_expression(m,getattr(u,'MaterialExpression'+c))
def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material input connection failed: '+str(pin))
def prop(a,out,name):
    if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Material output connection failed: '+name)
def tex(suffix,kind):
    n=node('TextureSample');n.texture=u.load_asset('/Game/UnrealNormandy/Textures/T_LC_BasaltCliff_00A_'+suffix)
    if not n.texture:raise RuntimeError(suffix)
    n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind);return n
c=tex('Albedo','COLOR');n=tex('Normal','NORMAL');p=tex('RHAOM','MASKS')
d=node('Desaturation');fraction=node('Constant');fraction.r=.8
desaturation_inputs=L.get_material_expression_input_names(d)
link(fraction,'',d,desaturation_inputs[1]);link(c,'RGB',d,desaturation_inputs[0])
t=node('Multiply');dark=node('Constant');dark.r=.085
link(dark,'',t,'B');link(d,'',t,'A');prop(t,'','BASE_COLOR')
prop(n,'RGB','NORMAL');prop(p,'B','AMBIENT_OCCLUSION')
r=node('Constant');r.r=.96;prop(r,'','ROUGHNESS')
L.recompile_material(m)
if not E.save_loaded_asset(m,False):raise RuntimeError('Save flue soot')
u.log('SMITH_CHIMNEY_R8_SOOT_SAVED inputs='+str(desaturation_inputs))
