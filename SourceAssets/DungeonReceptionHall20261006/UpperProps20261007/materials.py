"""Reception-scoped PBR metal, painted band and recessed liner."""
import unreal as u
L=u.MaterialEditingLibrary
METAL='/Game/SubstrateMaterials/Textures/03_Metals/T_Metal_Steel_Brushed_'

def author(base,owned,asset,save):
    saved=[]
    for key,col,rough,metal in [('SatinSteel',(.42,.45,.46),.48,.90),('BinPaint',(.034,.065,.053),.68,0),('BinLiner',(.013,.018,.016),.43,0)]:
        path=base+'/Materials/M_RHU_'+key
        m=owned(path)
        if m:
            saved.append(path);continue
        m=u.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
        m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
        def node(kind,**props):
            n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
            for p,v in props.items():n.set_editor_property(p,v)
            return n
        def wire(a,out,b,pin):
            if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection '+key+' '+pin)
        def scalar(v):return node('Constant',r=v)
        def rgb(v):return node('Constant3Vector',constant=u.LinearColor(*v,1))
        def mix(a,ao,b,bo,t,to=''):
            n=node('LinearInterpolate');wire(a,ao,n,'A');wire(b,bo,n,'B');wire(t,to,n,'Alpha');return n
        def mul(a,ao,value):
            n=node('Multiply',const_b=value);wire(a,ao,n,'A');return n
        uv=node('TextureCoordinate');age=node('VertexColor')
        def tex(suffix,kind):
            n=node('TextureSample',texture=asset(METAL+suffix),sampler_type=kind);wire(uv,'',n,'UVs');return n
        bc=tex('BC',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        rt=tex('R',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        nt=tex('N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        # Existing brushed PBR variation, subdued enough for an abandoned hall.
        basecolor=mix(rgb(col),'',bc,'RGB',scalar(.22 if key=='SatinSteel' else .018))
        grime=mul(age,'R',.48 if key=='SatinSteel' else .25)
        basecolor=mix(basecolor,'',rgb(tuple(v*.26 for v in col)),'',grime)
        r=mix(scalar(rough-.05),'',scalar(rough+.14),'',rt,'R')
        r=mix(r,'',scalar(.84),'',age,'R')
        met=mix(scalar(metal),'',scalar(metal*.12),'',grime)
        normal=mix(rgb((0,0,1)),'',nt,'RGB',scalar(.30 if key=='SatinSteel' else .09))
        normal_unit=node('Normalize');wire(normal,'',normal_unit,'VectorInput')
        slab=node('SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for n,prop,pin in [(basecolor,'BASE_COLOR','BaseColor'),(r,'ROUGHNESS','Roughness'),(met,'METALLIC','Metallic'),(normal_unit,'NORMAL','Normal'),(scalar(.30),'SPECULAR','Specular')]:
            if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
            wire(n,'',slab,pin)
        if not L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output')
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Material build '+key+' '+str(errors))
        L.layout_material_expressions(m);save(m);saved.append(path)
    return saved
