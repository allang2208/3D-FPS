"""Finish layers for chapel-local stone and furniture, on top of their scanned surfaces."""
import unreal as u

L = u.MaterialEditingLibrary
TEXTURES = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/'
PLASTER = '/Game/Dungeons/TunnelStyleIncinerator20261111/Quixel/CrackedPaintedPlaster_d91bfe39/Textures/T_CrackedPaintedPlaster_d91bfe39_'

COORDINATES = """
float3 d=(P.xyz-Origin.xyz)/max(Scale,1.);
float sn,cs; sincos(Heading,sn,cs);
return float3(dot(d.xy,float2(cs,sn)),dot(d.xy,float2(-sn,cs)),d.z);
"""

def heading(mat, graph):
    n=graph['node'](mat,'ScalarParameter')
    n.set_editor_property('parameter_name','ChapelHeadingRadians')
    n.set_editor_property('use_custom_primitive_data',True)
    n.set_editor_property('primitive_data_index',4)
    n.set_editor_property('default_value',0.)
    return n

def site_coords(mat, graph):
    site = graph['node'](mat, 'VectorParameter')
    site.set_editor_property('parameter_name', 'ChapelFloor')
    site.set_editor_property('use_custom_primitive_data', True)
    site.set_editor_property('primitive_data_index', 0)
    pos = graph['node'](mat, 'WorldPosition')
    pos.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    return graph['shader'](mat, 'ChapelCoordinates', COORDINATES,
                           {'P':pos, 'Origin':site, 'Scale':(site,'A'),'Heading':heading(mat,graph)}, 3)

def finish_surface(mat, slot, graph, color, normal, rough, ao):
    shader = graph['shader']
    place = site_coords(mat,graph)
    if slot in ('Wall','Limewash','Buttress','Lancet'):
        inside = slot=='Limewash'
        mask = shader(mat,'StoneExposure', '''
float side=smoothstep(315.,348.,abs(Q.y));
float rainAxis=min(min(abs(Q.x+200.),abs(Q.x-200.)),abs(Q.x-575.));
float run=abs(rainAxis-22.)+3.*sin(Q.z*.082+Q.x*.06);
float sill=(1.-smoothstep(2.,9.,run))*smoothstep(30.,95.,Q.z)*(1.-smoothstep(140.,156.,Q.z))*side;
float rough=.48+.21*sin(Q.x*.021+Q.y*.009+Q.z*.012)+.17*sin(Q.y*.027+Q.z*.039)+.13*cos(Q.x*.081-Q.z*.057);
float seep=(1.-smoothstep(4.,60.,Q.z+rough*17.))*(.33+.42*rough+.18*smoothstep(-200.,180.,Q.y));
float plaster=smoothstep(.52,.62,rough+(H-.57)*.43)*smoothstep(8.,54.,Q.z);
float chips=smoothstep(.50,.79,H)*smoothstep(.46,.72,rough);
return float3(saturate(seep+sill*.51),plaster,chips);
''', {'Q':place,'H':ao},3)
        if inside:
            uv=graph['node'](mat,'TextureCoordinate')
            plaster = graph['texture'](mat,PLASTER+'BaseColor',uv)
            plaster_n = graph['texture'](mat,PLASTER+'Normal',uv)
            color=shader(mat,'RemnantLime', '''
float chalk=dot(Plaster.rgb,float3(.30,.59,.11));
float3 wash=clamp(chalk*.65+.15,.16,.62)*float3(.95,.87,.70);
return lerp(Base*(1.-.25*M.r),wash,M.g*.85);
''',{'Base':color,'Plaster':plaster,'M':mask},3)
            normal=shader(mat,'FlakedLimeNormal','return normalize(lerp(N,PN,M.g*.78));',
                          {'N':normal,'PN':plaster_n,'M':mask},3)
            rough=shader(mat,'LimeRoughness','return lerp(R,.90,M.g);',{'R':rough,'M':mask},1)
        else:
            reveal=1. if slot=='Lancet' else 0.
            multiplier=graph['constant_value'](mat,reveal)
            color=shader(mat,'ExposedStone', '''
float3 stone=Base*lerp(float3(.88,.88,.86),float3(.63,.67,.54),M.r);
float3 mineral=lerp(stone,dot(stone,float3(.30,.59,.11))*float3(1.11,1.08,.91)+.025,M.b*.38);
return mineral*lerp(1.,.79,Reveal);
''',{'Base':color,'M':mask,'Reveal':multiplier},3)
            rough=shader(mat,'MoistStone','return lerp(max(.62,R),.63,M.r*.7);',{'R':rough,'M':mask},1)
    elif slot=='Flagstone':
        wear=shader(mat,'FootTraffic', '''
float aisle=(1.-smoothstep(53.,107.,abs(Q.y)+4.*sin(Q.x*.042)))*smoothstep(-778.,-690.,Q.x)*(1.-smoothstep(330.,455.,Q.x));
return aisle*smoothstep(.43,.88,AO);
''',{'Q':place,'AO':ao},1)
        rough=shader(mat,'WalkPolish','return lerp(R,max(.48,R-.20),W);',{'R':rough,'W':wear},1)
        color=shader(mat,'WornFlags','return Base*lerp(1.,.89,W);',{'Base':color,'W':wear},3)
    elif slot=='Slate':
        local=graph['node'](mat,'LocalPosition')
        masks=shader(mat,'SlateCourses', '''
float row=floor(max(abs(P.y)-.3,0.)/22.4);
float col=floor((P.x+200.+16.*fmod(row,2.))/32.);
float bay=floor((Q.x+800.)/400.);
float hash=frac(sin(dot(float3(col,row,bay+step(0.,Q.y)*13.),float3(17.17,53.31,11.73)))*4375.91);
float fragments=smoothstep(.53,.76,.48+.23*sin(Q.x*.14+Q.y*.09)+.20*cos(Q.x*.057-Q.y*.23)+.15*sin(Q.x*.37));
float ridge=(1.-smoothstep(8.,70.,abs(Q.y)))*smoothstep(.1,.65,.5+.5*cos(Q.x*.027));
return float3(hash,step(.942,hash),fragments*ridge);
''',{'P':local,'Q':place},3)
        color=shader(mat,'SlateRepairs', '''
float3 slate=Base*lerp(.80,1.10,M.r);
slate=lerp(slate,slate*float3(.76,.87,1.04),M.g);
return lerp(slate,float3(.102,.091,.048),.43*M.b);
''',{'Base':color,'M':masks},3)
        rough=shader(mat,'SlateRoughness','return clamp(R-.12*M.g+.07*M.b,.54,.96);',{'R':rough,'M':masks},1)
    return color,normal,rough,ao

def original_texture(mat, role, channel, sampler):
    texture=u.EditorAssetLibrary.load_asset(TEXTURES+'T_Chapel'+role+'_'+channel)
    n=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
    n.set_editor_property('parameter_name',channel)
    n.set_editor_property('texture',texture)
    n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler))
    return n

def artifact_finish(role, instance, create, save, graph):
    mat=create('M_Chapel'+role+'Finish')
    c=original_texture(mat,role,'base_color','COLOR')
    n=original_texture(mat,role,'normal','NORMAL')
    m=original_texture(mat,role,'metallic','MASKS')
    r=original_texture(mat,role,'roughness','MASKS')
    shader=graph['shader']
    metal=(m,'R')
    rough=(r,'R')
    ao=graph['constant_value'](mat,1.)
    if role in ('Buttress','Lancet'):
        c,n,rough,_=finish_surface(mat,role,graph,c,n,rough,(r,'R'))
    else:
        local=graph['node'](mat,'LocalPosition')
        if role=='Door':
            # Existing relief puts the iron proud of the boards on the western face.
            wear=shader(mat,'StrapsAndLatch', '''
float iron=saturate(max(M,smoothstep(1.85,2.80,-P.x)));
float touch=1.-smoothstep(.28,1.,length((P.yz-float2(51.,124.))/float2(24.,28.)));
return float3(iron,touch,smoothstep(2.8,3.55,-P.x)*iron);
''',{'P':local,'M':metal},3)
            c=shader(mat,'OakAndWroughtIron', '''
float3 oak=Base*lerp(float3(.55,.48,.39),float3(.77,.66,.50),W.g);
return lerp(oak,lerp(Base*.30+float3(.020,.020,.019),Base*.63+.055,W.b),W.r);
''',{'Base':c,'W':wear},3)
            metal=shader(mat,'ExposedIron','return max(M,W.r*.76);',{'M':metal,'W':wear},1)
            rough=shader(mat,'HandContact','return lerp(lerp(R,max(.42,R-.24),W.g),lerp(.76,.48,W.b),W.r);',{'R':rough,'W':wear},1)
        else:
            site=site_coords(mat,graph)
            wear=shader(mat,'PewContact', '''
float hand=smoothstep(.70,1.,saturate((P.z-55.)/28.));
float end=smoothstep(59.,94.,abs(P.y))*(1.-smoothstep(130.,195.,abs(Q.y)));
float seat=(1.-smoothstep(2.,10.,abs(P.z-44.)))*(.18+.22*end);
float row=.75+.22*sin(Q.x*.015);
return saturate(row*(hand*(.23+.66*end)+seat));
''',{'P':local,'Q':site},1)
            c=shader(mat,'PolishedOak','return Base*lerp(float3(.77,.70,.61),float3(1.02,.90,.72),W);',{'Base':c,'W':wear},3)
            rough=shader(mat,'WornOakRoughness','return lerp(R,max(.38,R-.29),W);',{'R':rough,'W':wear},1)
    for prop,val in [('BASE_COLOR',c),('NORMAL',n),('ROUGHNESS',rough),('METALLIC',metal)]:
        expr,pin=val if isinstance(val,tuple) else (val,'')
        if not L.connect_material_property(expr,pin,getattr(u.MaterialProperty,'MP_'+prop)):
            raise RuntimeError(role+' finish '+prop)
    for usage in ('INSTANCED_STATIC_MESHES','NANITE'):
        L.set_base_material_usage(mat,getattr(u.MaterialUsage,'MATUSAGE_'+usage),True)
    L.recompile_material(mat)
    save(mat)
    L.set_material_instance_parent(instance,mat)
    L.update_material_instance(instance)
    save(instance)
