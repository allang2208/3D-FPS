"""Author a local damp-streak decal shader from our own concrete noise texture."""
import unreal as u
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
path='/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak'
m=u.load_asset(path)
if not m:
    m=u.AssetToolsHelpers.get_asset_tools().create_asset('M_LocalDampStreak',path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
if m:
    L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    def node(cls):return L.create_material_expression(m,cls)
    def wire(a,b,pin,out=''):
        if not L.connect_material_expressions(a,out,b,'' if pin=='Input' else pin):raise RuntimeError('Cannot author decal input '+pin)
    def val(v):
        n=node(u.MaterialExpressionConstant);n.r=v;return n
    def op(cls,a,b):
        n=node(cls);wire(a,n,'A');wire(b,n,'B');return n
    def output(n,prop,pin=''):
        if not L.connect_material_property(n,pin,prop):raise RuntimeError('Cannot author decal output')
    uv=node(u.MaterialExpressionTextureCoordinate)
    xy=[]
    for axis in ('r','g'):
        mask=node(u.MaterialExpressionComponentMask);mask.set_editor_property('r',axis=='r');mask.set_editor_property('g',axis=='g')
        mask.set_editor_property('b',False);mask.set_editor_property('a',False)
        wire(uv,mask,'Input')
        centered=op(u.MaterialExpressionSubtract,mask,val(.5))
        doubled=op(u.MaterialExpressionMultiply,centered,val(2))
        xy.append(op(u.MaterialExpressionMultiply,doubled,doubled))
    radial=op(u.MaterialExpressionAdd,*xy)
    inverse=op(u.MaterialExpressionSubtract,val(1),radial)
    edge=node(u.MaterialExpressionSaturate);wire(op(u.MaterialExpressionMultiply,inverse,val(3.5)),edge,'Input')
    stretched=node(u.MaterialExpressionTextureCoordinate);stretched.u_tiling=4.5;stretched.v_tiling=.32
    noise=node(u.MaterialExpressionTextureSample);noise.texture=u.load_asset('/Game/Dungeons/AtmosphereV2/Textures/T_Concrete_Roughness')
    noise.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS;wire(stretched,noise,'UVs')
    grain=node(u.MaterialExpressionComponentMask);grain.set_editor_property('r',True);grain.set_editor_property('g',False)
    grain.set_editor_property('b',False);grain.set_editor_property('a',False);wire(noise,grain,'Input','RGB')
    contrasted=op(u.MaterialExpressionMultiply,op(u.MaterialExpressionSubtract,grain,val(.72)),val(8.0))
    clipped=node(u.MaterialExpressionSaturate);wire(contrasted,clipped,'Input')
    alpha=op(u.MaterialExpressionMultiply,op(u.MaterialExpressionMultiply,edge,clipped),val(.68))
    color=node(u.MaterialExpressionConstant3Vector);color.constant=u.LinearColor(.018,.029,.018,1)
    output(color,u.MaterialProperty.MP_BASE_COLOR);output(alpha,u.MaterialProperty.MP_OPACITY)
    output(val(.40),u.MaterialProperty.MP_ROUGHNESS)
    L.layout_material_expressions(m);L.recompile_material(m)
    if not E.save_loaded_asset(m,False):raise RuntimeError('Decal material save failed')
print('V2_LOCAL_DAMP_MATERIAL_SAVED')
