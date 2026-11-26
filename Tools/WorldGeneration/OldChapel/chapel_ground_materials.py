"""The chapel plinth and the local worn-earth blend on the streamed hills terrain."""
import unreal as u

L = u.MaterialEditingLibrary
CHAPEL = '/Game/WorldGeneration/TemperateHills/OldChapel/Materials/'
MUD_SOURCE = '/Game/MilitaryTrench/Assets/Surfaces/Mt_Slope_Ground_Mud_Soil_01/Textures/T_Mt_Slope_Ground_Mud_Soil_01_'
MUD = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
LITTER = '/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Textures/T_ForestFloor_'
GRASS = '/Game/WorldGeneration/TemperateHills/WetForest/Textures/T_LivingGrass_'
GRIT = '/Game/WorldGeneration/TemperateHills/Upland/Textures/T_RockySteppe_'
STONE = '/Game/UnrealNormandy/Textures/T_StoneSurface_02A_'

def earth_textures():
    # The hills shader uses explicit texture gradients and the terrain mip lease.
    # Supply ordinary streamed textures without modifying the source pack's virtual textures.
    e=u.EditorAssetLibrary
    for channel in ('B','H','N','ORM'):
        path=MUD+channel
        asset=e.load_asset(path) if e.does_asset_exist(path) else e.duplicate_asset(MUD_SOURCE+channel,path)
        if not asset:raise RuntimeError('Could not create chapel earth texture '+channel)
        if asset.get_editor_property('virtual_texture_streaming') or asset.get_editor_property('max_texture_size')!=2048:
            asset.set_editor_property('virtual_texture_streaming',False)
            asset.set_editor_property('max_texture_size',2048)
            if not e.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+path)

def node(mat, kind):
    return L.create_material_expression(mat, getattr(u, 'MaterialExpression' + kind))

def wire(source, target, pin):
    expr, output = source if isinstance(source, tuple) else (source, '')
    if not L.connect_material_expressions(expr, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '.' + pin)

def shader(mat, label, code, inputs, size):
    expr = node(mat, 'Custom')
    expr.set_editor_property('desc', 'OldChapel.' + label)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for key in inputs:
        item = u.CustomInput()
        item.set_editor_property('input_name', key)
        pins.append(item)
    expr.set_editor_property('inputs', pins)
    for key, value in inputs.items():
        wire(value, expr, key)
    return expr

def texture(mat, path, uv=None):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing surface texture ' + path)
    expr = node(mat, 'TextureSample' if uv else 'TextureObject')
    expr.set_editor_property('texture', asset)
    compression = asset.get_editor_property('compression_settings')
    sampler = {
        u.TextureCompressionSettings.TC_NORMALMAP: 'NORMAL',
        u.TextureCompressionSettings.TC_MASKS: 'MASKS',
        u.TextureCompressionSettings.TC_GRAYSCALE: 'GRAYSCALE' if asset.srgb else 'LINEAR_GRAYSCALE',
        u.TextureCompressionSettings.TC_ALPHA: 'ALPHA'
    }.get(compression, 'COLOR' if asset.srgb else 'LINEAR_COLOR')
    if asset.get_editor_property('virtual_texture_streaming'):
        sampler='VIRTUAL_'+sampler
    expr.set_editor_property('sampler_type', getattr(u.MaterialSamplerType, 'SAMPLERTYPE_' + sampler))
    if uv:
        expr.set_editor_property('sampler_source', u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        wire(uv, expr, 'UVs')
    return expr

def footing(create, save):
    earth_textures()
    mat = create('M_ChapelFooting')
    uv = node(mat, 'TextureCoordinate')
    profile = node(mat, 'TextureCoordinate')
    profile.coordinate_index = 1
    height = texture(mat, STONE + 'Height', uv)
    bump = node(mat, 'BumpOffset')
    bump.set_editor_property('height_ratio', .006)
    bump.set_editor_property('reference_plane', .69)
    wire(uv, bump, 'Coordinate')
    wire((height, 'R'), bump, 'Height')
    stone = texture(mat, STONE + 'BaseColor', bump)
    normal = texture(mat, STONE + 'Normal', bump)
    packed = texture(mat, STONE + 'RHAOM', bump)
    earth = texture(mat, MUD + 'B', uv)
    contact = shader(mat, 'SoilLine', '''
float irregular=.042*sin(U.x*16.+U.y*4.)+.024*cos(U.y*26.-U.x*13.)+.045*(H-.68);
return (1.-smoothstep(.003,.145,Profile.x-irregular))*.77;
''', {'Profile': profile, 'U': uv, 'H': (height,'R')}, 1)
    color = shader(mat, 'WeatheredStone', '''
float3 dirt=lerp(Earth.rgb,dot(Earth.rgb,float3(.299,.587,.114))*float3(1.06,.91,.74),.45);
return lerp(Stone.rgb*float3(.91,.87,.81),dirt*.85,Contact);
''', {'Stone': stone, 'Earth': earth, 'Contact': contact}, 3)
    rough = shader(mat, 'FootingRoughness', 'return lerp(clamp(R,.59,.95),.86,W);',
                   {'R':(packed,'R'), 'W':contact}, 1)
    for pin, value in {'BASE_COLOR':(color,''), 'ROUGHNESS':(rough,''), 'NORMAL':(normal,'RGB'),
                       'AMBIENT_OCCLUSION':(packed,'B')}.items():
        if not L.connect_material_property(*value, getattr(u.MaterialProperty,'MP_'+pin)):
            raise RuntimeError('Footing output '+pin)
    L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat

def yard_stone(create, save, slot):
    # The split faces, packing slates and caps each use their own scanned stone.
    scan,tint={'YardField':('02A',(.78,.77,.70)), 'YardSlate':('03A',(.62,.67,.68)),
               'YardCap':('01A',(.81,.80,.72))}[slot]
    stone='/Game/UnrealNormandy/Textures/T_StoneSurface_'+scan+'_'
    moss='/Game/WorldGeneration/TemperateHills/WetForest/Textures/T_RainforestMoss_'
    mat=create('M_Chapel'+slot)
    uv=node(mat,'TextureCoordinate')
    band=node(mat,'TextureCoordinate')
    band.coordinate_index=1
    pos=node(mat,'WorldPosition')
    pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    h=texture(mat,stone+'Height',uv)
    bump=node(mat,'BumpOffset')
    bump.set_editor_property('height_ratio',.010)
    bump.set_editor_property('reference_plane',.55)
    wire(uv,bump,'Coordinate')
    wire((h,'R'),bump,'Height')
    base=texture(mat,stone+'BaseColor',bump)
    normal=texture(mat,stone+'Normal',bump)
    packed=texture(mat,stone+'RHAOM',bump)
    moss_color=texture(mat,moss+'BaseColor',uv)
    moss_normal=texture(mat,moss+'Normal',uv)
    moss_pack=texture(mat,moss+'ARH',uv)
    mask=shader(mat,'DampPockets','''
float patch=.5+.21*sin(P.x*.039+P.z*.056)+.17*cos(P.y*.062-P.z*.043)+.12*sin((P.x+P.y)*.013);
float low=1.-smoothstep(.025,.35,Profile.x);
float cap=Cap*smoothstep(.61,.83,Profile.x);
return saturate(smoothstep(.36,.74,patch+.12*(1.-H))*
       (.68*low+.32*cap+.14)*( .58+.42*smoothstep(.29,.65,M)));
''',{'P':pos,'Profile':band,'H':(h,'R'),'Cap':constant_value(mat,float(slot=='YardCap')),'M':(moss_pack,'B')},1)
    color=shader(mat,'Fieldstone','''
float patina=.95+.08*sin(P.x*.019+P.y*.022+P.z*.047);
float3 lichen=lerp(Moss.rgb,dot(Moss.rgb,float3(.30,.59,.11))*float3(.91,.98,.70),.63);
return lerp(Stone.rgb*float3(%s)*patina,lichen*.81,W);
'''%(','.join(str(x) for x in tint)),{'P':pos,'Stone':base,'Moss':moss_color,'W':mask},3)
    n=shader(mat,'StoneMossNormal','return normalize(lerp(A,B,W));',{'A':normal,'B':moss_normal,'W':mask},3)
    r=shader(mat,'WeatherRoughness','return lerp(clamp(R,.55,.96),MR,W);',{'R':(packed,'R'),'MR':(moss_pack,'G'),'W':mask},1)
    for prop,expr,pin in [('BASE_COLOR',color,''),('NORMAL',n,''),('AMBIENT_OCCLUSION',packed,'B'),('ROUGHNESS',r,'')]:
        if not L.connect_material_property(expr,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(slot+' '+prop)
    for usage in ('INSTANCED_STATIC_MESHES','NANITE'):
        L.set_base_material_usage(mat,getattr(u.MaterialUsage,'MATUSAGE_'+usage),True)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)
    return mat

def constant_value(mat,value):
    n=node(mat,'Constant')
    n.r=value
    return n

PATH_AND_FOOTINGS = '''
float2 toChurch=Site.xy-float2(Site.z,TrailY);
if(dot(toChurch,toChurch)<1.)return float4(0,0,0,0);
float2 axis=normalize(toChurch), sideAxis=float2(-axis.y,axis.x), delta=P.xy-Site.xy;
float2 local=float2(dot(delta,axis),dot(delta,sideAxis))/Scale;
float2 start=float2(-length(toChurch)/Scale,0.);
float2 courtMin=float2(-2240.,-1680.)/Scale,courtMax=float2(2000.,1680.)/Scale;
if(dot(start,start)<1 || any(local<min(start,courtMin)-155.) ||
   any(local>max(start,courtMax)+155.))return float4(0,0,0,0);
float2 control=float2(start.x,0),apron=float2(-2650./Scale,0),end=float2(-916,0),a=start;
float shortest=1e12,along=0.;
[unroll] for(int i=1;i<=8;i++){
    float t=i*.125;
    float u=min(t/.625,1.);
    float2 b=t<.625?lerp(lerp(start,control,u),lerp(control,apron,u),u):lerp(apron,end,(t-.625)/.375);
    float2 v=b-a;
    float f=saturate(dot(local-a,v)/max(1.,dot(v,v)));
    float2 delta=local-(a+v*f);
    float d=dot(delta,delta);
    if(d<shortest){shortest=d;along=(i-1+f)*.125;}
    a=b;
}
float dist=sqrt(shortest);
// Soil around a travelled line varies in patches in ground space. All four
// material outputs use these same two scales, including in shadow or rain.
struct FChapelSod {
  float Hash(float2 c) {
    float3 q=frac(c.xyx*float3(.1031,.1030,.0973));
    q+=dot(q,q.yzx+33.33);
    return frac((q.x+q.y)*q.z);
  }
  float Patch(float2 p) {
    float2 c=floor(p), f=frac(p);
    f=f*f*(3.-2.*f);
    float4 h=float4(Hash(c),Hash(c+float2(1,0)),Hash(c+float2(0,1)),Hash(c+1.));
    return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
  }
};
FChapelSod field;
float bank=field.Patch(local/218.+float2(23.7,14.1));
float fleck=field.Patch(float2(.86*local.x-.50*local.y,.50*local.x+.86*local.y)/52.+9.);
float ripple=(bank-.50)*1.65+(fleck-.50)*.82;
float halfWidth=51.+20.*bank+10.*ripple+31.*smoothstep(.82,1.,along);
float trail=(1.-smoothstep(halfWidth-15.,halfWidth+22.+24.*bank,dist))*smoothstep(0.,.045,along);
float centre=1.-smoothstep(.27,.91,dist/max(1.,halfWidth));
float4 segments[4]={G1,G2,G3,G4};
float graveDist=1e6;
[unroll] for(int j=0;j<4;j++){
    float2 q=segments[j].xy, v=segments[j].zw-q;
    float u=saturate(dot(local-q,v)/max(dot(v,v),1.));
    graveDist=min(graveDist,length(local-(q+v*u)));
}
float grave=(1.-smoothstep(12.,38.+22.*bank+8.*ripple,graveDist))*(.39+.18*bank);
float2 boxCentre=(courtMax+courtMin)*.5;
float2 bounds=abs(local-boxCentre)-(courtMax-courtMin)*.5;
float courtEdge=length(max(bounds,0.))+min(max(bounds.x,bounds.y),0.);
float gateGap=local.x<courtMin.x+105. ? smoothstep(139.,162.,abs(local.y)) : 1.;
float windrow=(1.-smoothstep(3.,29.+52.*bank,abs(courtEdge)))*gateGap*smoothstep(.25,.82,bank+.21*fleck);

float2 corner=abs(local)-float2(817,420);
float rim=length(max(0.,corner))+min(0.,max(corner.x,corner.y));
float pierX=min(min(abs(abs(local.x)-754.),abs(abs(local.x)-400.)),abs(local.x));
float2 pad=float2(pierX-47.,abs(abs(local.y)-452.)-52.);
float toe=length(max(pad,0.))+min(0.,max(pad.x,pad.y));
float baseEdge=min(rim,toe);
float skirt=(1.-smoothstep(2.,26.+40.*bank,baseEdge))*(.52+.32*fleck);
float sheltered=max(1.-smoothstep(43.,240.+145.*bank,abs(courtEdge)),
                    1.-smoothstep(37.,189.+105.*bank,max(baseEdge,0.)));
float sod=(1.-smoothstep(-14.,90.,courtEdge))*saturate(.16+.53*bank+.20*fleck+.31*sheltered);
float wear=max(max(trail,grave),max(skirt,windrow*.55));
float shoulder=saturate(.14+.64*(1.-centre)+.34*windrow+.10*ripple);
float verge=saturate(sod)*(1.-wear)*(1.-smoothstep(-15.,30.,-rim));
return float4(wear,shoulder,centre*trail,verge);
'''

def road_layer(mat, base):
    earth_textures()
    before=set(L.get_material_expressions(mat))
    site = node(mat,'VectorParameter')
    site.set_editor_property('parameter_name','ChapelGroundAndTrail')
    site.set_editor_property('default_value',u.LinearColor(0,0,0,0))
    scale=node(mat,'ScalarParameter')
    scale.set_editor_property('parameter_name','ChapelAssemblyScale')
    scale.set_editor_property('default_value',1.)
    pos = node(mat,'WorldPosition')
    pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    path_inputs={'Site':site,'TrailY':(site,'A'),'P':pos,'Scale':scale}
    for i in range(1,5):
        segment=node(mat,'VectorParameter')
        segment.set_editor_property('parameter_name','ChapelGraveSegment'+str(i))
        xyzw=node(mat,'AppendVector')
        wire(segment,xyzw,'A')
        wire((segment,'A'),xyzw,'B')
        path_inputs['G'+str(i)]=xyzw
    mask = shader(mat,'PathAndFootings',PATH_AND_FOOTINGS,path_inputs,4)
    wet=node(mat,'ScalarParameter')
    wet.set_editor_property('parameter_name','Wetness')
    wet.set_editor_property('default_value',0.)
    # Gradients precede the early-out. Cells away from the building do not fetch chapel textures.
    sample='Texture2DSampleGrad({tex},GetMaterialSharedSampler({tex}Sampler,Material.Wrap_WorldGroupSettings),{uv},dx*{scale},dy*{scale})'
    pre='''
float2 uv=P.xy*.0062,dx=ddx(uv),dy=ddy(uv);
[branch] if(max(M.x,M.w)<=0.)return Base;
float2 warp=float2(sin(P.y*.0031+P.x*.0016),cos(P.x*.0037-P.y*.0015))*.13;
float2 q=uv+warp, leafUV=uv*.81+float2(.24,.63);
float2 gritUV=uv*2.4+float2(.13,.37);
'''
    # The fine mineral soil dominates the worn strip; the cached Quixel broadleaf scan
    # contributes leaf fragments and height-broken patches at the shoulders and wall toes.
    channels=[
        ('BASE_COLOR','B','BaseColor',3,'''
float3 tone=lerp(dirt.rgb,dot(dirt.rgb,float3(.299,.587,.114))*float3(1.12,.95,.76),.38);
float3 soil=lerp(tone*lerp(.80,.98,M.z),litter.rgb,leaf)*lerp(.96,.68,saturate(Wet));
float gray=dot(turf.rgb,float3(.299,.587,.114));
float3 blades=lerp(turf.rgb,gray*float3(1.05,.98,.77),.52);
return lerp(lerp(Base,blades,sod),soil,coverage);'''),
        ('NORMAL','N','Normal',3,'''
float3 relief=normalize(lerp(UnpackNormalMap(dirt).xyz,UnpackNormalMap(litter).xyz,leaf));
relief=normalize(lerp(relief,float3(0,0,1),.25*M.z));
return normalize(lerp(normalize(lerp(Base,UnpackNormalMap(turf).xyz,sod)),relief,coverage));'''),
        ('ROUGHNESS','ORM','ARH',1,'''
float rough=lerp(dirt.g,litter.g,leaf);
rough=lerp(rough,max(.51,rough-.12),M.z);
return lerp(lerp(Base,turf.g,sod),lerp(clamp(rough,.51,.96),clamp(rough*.70,.36,.69),saturate(Wet)),coverage);'''),
        ('AMBIENT_OCCLUSION','ORM','ARH',1,'''
return lerp(lerp(Base,turf.r,sod),lerp(dirt.r,litter.r,leaf),coverage);''')]
    textures={}
    def obj(path):
        if path not in textures:textures[path]=texture(mat,path)
        return textures[path]
    result=dict(base)
    # Restrict grit to the scan's exposed high points in broken patches along the worn centre.
    for prop,mud,litter,size,finish in channels:
        code=pre+'float h='+sample.format(tex='HeightMap',uv='q',scale='1.')+'.r;\n'
        code+='float leaf=saturate((M.y-.24+(h-.50)*.60)*.84);\n'
        code+='float coverage=saturate(M.x+(h-.5)*1.15*M.x*(1.-M.x));\n'
        code+='float4 dirt='+sample.format(tex='Mud',uv='q',scale='1.')+';\n'
        code+='float4 litter='+sample.format(tex='Leaves',uv='leafUV',scale='.81')+';\n'
        code+='float4 turf='+sample.format(tex='Turf',uv='uv*.75+float2(.31,.17)',scale='.75')+';\n'
        code+='float sod=saturate(M.w*1.24+(h-.5)*M.w*.46);\n'
        grit_fetch=sample.format(tex='GritMap',uv='gritUV',scale='2.4')
        code+='float4 gritPacked='+sample.format(tex='GritHeight',uv='gritUV',scale='2.4')+';\n'
        code+='float patch=.52+.19*sin(P.x*.012+P.y*.009)+.17*cos(P.y*.041-P.x*.024);\n'
        code+='float gritWeight=M.z*patch*smoothstep(.49,.75,gritPacked.b);\n'
        # Normal-map blending is in decoded tangent space.
        if prop=='NORMAL':
            finish=finish.replace('UnpackNormalMap(dirt).xyz','normalize(lerp(UnpackNormalMap(dirt).xyz,UnpackNormalMap('+grit_fetch+').xyz,gritWeight))')
        else:
            code+='dirt=lerp(dirt,'+(grit_fetch if prop=='BASE_COLOR' else ('gritPacked.gggg' if prop=='ROUGHNESS' else 'gritPacked'))+',gritWeight);\n'
        inputs={'P':pos,'M':mask,'Base':base[prop],'Wet':wet,'HeightMap':obj(MUD+'H'),
                'Mud':obj(MUD+mud),'Leaves':obj(LITTER+litter),'GritHeight':obj(GRIT+'ARH'),'Turf':obj(GRASS+litter)}
        if prop in ('BASE_COLOR','NORMAL'):inputs['GritMap']=obj(GRIT+litter)
        result[prop]=shader(mat,prop,code+finish,inputs,size)
    for expr in set(L.get_material_expressions(mat))-before:
        if not str(expr.get_editor_property('desc')).startswith('OldChapel.'):
            expr.set_editor_property('desc','OldChapel.'+expr.get_name())
    for expr in before:
        if str(expr.get_editor_property('desc')).startswith('OldChapel.'):
            L.delete_material_expression(mat,expr)
    return result
