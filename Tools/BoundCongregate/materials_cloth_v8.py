"""Matte, faded donor fabrics with woven normal, worn hems and broken stitching."""
import unreal as u
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
BASE='/Game/Monsters/BoundCongregate';DEST=BASE+'/ClothV8/Materials'
def make(name,tint,binding=False):
    m=u.load_asset(DEST+'/M_'+name+'_V8') or AT.create_asset('M_'+name+'_V8',DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    for prop in ('two_sided','used_with_skeletal_mesh','used_with_clothing'):m.set_editor_property(prop,True)
    def node(cls):return L.create_material_expression(m,cls)
    def wire(a,out,b,pin):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection '+pin)
    def constant(v):
        n=node(u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
    def custom(code,inputs):
        n=node(u.MaterialExpressionCustom);n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n.set_editor_property('inputs',pins);n.set_editor_property('code',code)
        for key,(src,out) in inputs.items():wire(src,out,n,key)
        return n
    uv=node(u.MaterialExpressionTextureCoordinate);vc=node(u.MaterialExpressionVertexColor)
    base=node(u.MaterialExpressionTextureSample);base.set_editor_property('texture',u.load_asset(BASE+'/Textures/T_BC_Fabric_BaseColor'))
    normal=node(u.MaterialExpressionTextureSample);normal.set_editor_property('texture',u.load_asset(BASE+'/Textures/T_BC_Fabric_Normal'));normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    color=custom('''
float edge=EDGE_EXPR;
float hem=HEM_EXPR;
float2 cell=floor(UV*float2(17,29));
float speck=frac(sin(dot(cell,float2(12.9898,78.233)))*43758.5453);
float fade=.96+.045*sin(UV.x*7.3+sin(UV.y*5.1))+.035*sin(UV.y*11.7+UV.x*3.2);
float lum=clamp(dot(Base,float3(.2126,.7152,.0722))/.097,.82,1.16);
float wear=pow(1-edge,3)*(.12+.06*speck);
float seamBand=exp(-pow((edge-.26)*38,2));
float stitch=seamBand*smoothstep(.25,.38,frac(UV.y*96+UV.x*8))*step(.08,speck);
float3 cloth=float3(TINT)*lum*fade;
cloth=lerp(cloth,cloth*float3(.58,.55,.49),hem*.48);
cloth+=float3(.075,.064,.045)*wear+float3(.07,.059,.040)*stitch;
return max(cloth,.002);
'''.replace('TINT',','.join(str(v) for v in tint)).replace('EDGE_EXPR','saturate(min(UV.x,1-UV.x)*12)' if binding else 'saturate(Mask.g)').replace('HEM_EXPR','0' if binding else 'saturate(Mask.b)'),{'UV':(uv,''),'Base':(base,'RGB'),'Mask':(vc,'')})
    n=custom('return normalize(float3(N.xy*.22,N.z));',{'N':(normal,'RGB')})
    slab=node(u.MaterialExpressionSubstrateShadingModels)
    for src,prop,pin in [(color,u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(n,u.MaterialProperty.MP_NORMAL,'Normal'),(constant(.94),u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(constant(.18),u.MaterialProperty.MP_SPECULAR,'Specular'),(constant(0),u.MaterialProperty.MP_METALLIC,'Metallic')]:
        L.connect_material_property(src,'',prop);wire(src,'',slab,pin)
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(m,False):raise RuntimeError('Cloth material save failed')
    return m
def build():
    return {key:make(key,tint,key=='BC_Binding') for key,tint in {
        'BC_RagFabric':(.095,.102,.067),'BC_Lining':(.132,.119,.084),
        'BC_SleeveLeft':(.075,.080,.065),'BC_SleeveRight':(.116,.091,.063),
        'BC_Binding':(.046,.040,.029)}.items()}
