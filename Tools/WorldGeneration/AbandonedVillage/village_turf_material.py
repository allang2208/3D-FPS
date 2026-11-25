"""Blend the packed village turf into both the visible soil and its dry RVT."""
import unreal as u

TAG = 'VillageWalkedTurf'
UPLAND = '/Game/WorldGeneration/TemperateHills/Upland/Textures/T_LitteredGrass_'


def add_turf(mat,plan):
    lib = u.MaterialEditingLibrary
    expressions = list(lib.get_material_expressions(mat))
    if any(e.get_editor_property('desc')==TAG for e in expressions):
        return False
    mat.modify()
    def node(cls):
        e=lib.create_material_expression(mat,cls)
        e.set_editor_property('desc',TAG)
        return e
    def wire(src,channel,dest,pin):
        if not lib.connect_material_expressions(src,channel,dest,pin):
            raise RuntimeError('Village turf input '+str(pin))
    def sources(e):
        return dict(zip(map(str,lib.get_material_expression_input_names(e)),lib.get_inputs_for_material_expression(mat,e)))
    def mix(src,old_pin,channel):
        n=node(u.MaterialExpressionLinearInterpolate)
        wire(src,old_pin,n,'A')
        wire(turf,channel,n,'B')
        wire(turf,'Weight',n,'Alpha')
        return n
    road=next(e for e in expressions if isinstance(e,u.MaterialExpressionCustom) and e.get_editor_property('desc')=='VillageTerrainRoad')
    road_inputs=sources(road)
    inputs={key:(road_inputs[key],channel) for key,channel in (
        ('Position',''),('OriginAndCos',''),('SinYaw','A'),('RoadMask',''))}
    for key,suffix,sampler in [('TurfB','BaseColor','COLOR'),('TurfN','Normal','NORMAL'),('TurfARH','ARH','MASKS')]:
        texture=u.load_asset(UPLAND+suffix)
        if not texture or texture.get_editor_property('virtual_texture_streaming'):
            raise RuntimeError('Expected streamed upland texture '+suffix)
        obj=node(u.MaterialExpressionTextureObject)
        obj.set_editor_property('texture',texture)
        obj.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler))
        inputs[key]=(obj,'')
    wet=next((e for e in expressions if isinstance(e,u.MaterialExpressionScalarParameter)
              and str(e.get_editor_property('parameter_name'))=='Wetness'),None)
    zero=node(u.MaterialExpressionConstant)
    dry=node(u.MaterialExpressionRuntimeVirtualTextureReplace)
    wire(wet or zero,'',dry,'Default')
    wire(zero,'',dry,'VirtualTextureOutput')
    inputs['Wet']=(dry,'')
    ex,ey=plan.get('surface_extent_m',plan['extent_m'])
    turf=node(u.MaterialExpressionCustom)
    code='''
Weight=0.; GrassN=float3(0,0,1); GrassR=.85;
float2 axis=float2(OriginAndCos.z,SinYaw), d=Position.xy-OriginAndCos.xy;
float2 p=float2(dot(d,axis),dot(d,float2(-axis.y,axis.x)));
float2 span=float2(SPAN_X,SPAN_Y), uv=p/span+.5, dx=ddx(p),dy=ddy(p);
[branch] if(dot(axis,axis)<.5 || any(uv<=0.) || any(uv>=1.))return 0.;
// White alpha in older RGB masks means bare soil. Only the protected verge samples turf.
float grass=1.-Texture2DSampleGrad(RoadMask,GetMaterialSharedSampler(RoadMaskSampler,Material.Clamp_WorldGroupSettings),uv,dx/span,dy/span).a;
[branch] if(grass<.008)return 0.;
float2 t=p/142.+float2(.29,.67);
float4 packed=SAMPLE(TurfARH);
float cut=(packed.b-.5)*.64;
Weight=saturate(grass+cut*grass*(1.-grass))*.91;
float3 c=SAMPLE(TurfB).rgb;
float luma=dot(c,float3(.299,.587,.114));
c=lerp(c,luma*float3(.84,1.,.58),.32)*lerp(.91,.70,saturate(Wet));
float3 n=UnpackNormalMap(SAMPLE(TurfN));
GrassN=float3(n.x*axis.x-n.y*axis.y,n.x*axis.y+n.y*axis.x,n.z);
GrassR=lerp(packed.g,max(.40,packed.g*.76),saturate(Wet));
return c;
'''
    for key in ('TurfB','TurfN','TurfARH'):
        code=code.replace('SAMPLE('+key+')',f'Texture2DSampleGrad({key},GetMaterialSharedSampler({key}Sampler,Material.Wrap_WorldGroupSettings),t,dx/142.,dy/142.)')
    turf.set_editor_property('code',code.replace('SPAN_X',str(ex*200.)).replace('SPAN_Y',str(ey*200.)))
    turf.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins=[]
    for key in inputs:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',key)
        pins.append(pin)
    turf.set_editor_property('inputs',pins)
    extra=[]
    for key,size in [('GrassN',3),('GrassR',1),('Weight',1)]:
        pin=u.CustomOutput()
        pin.set_editor_property('output_name',key)
        pin.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
        extra.append(pin)
    turf.set_editor_property('additional_outputs',extra)
    for key,(e,c) in inputs.items():wire(e,c,turf,key)
    for prop,channel in [('BASE_COLOR','return'),('NORMAL','GrassN'),('ROUGHNESS','GrassR')]:
        prop=getattr(u.MaterialProperty,'MP_'+prop)
        n=mix(lib.get_material_property_input_node(mat,prop),lib.get_material_property_input_node_output_name(mat,prop),channel)
        if not lib.connect_material_property(n,'',prop):raise RuntimeError('Village turf material output')
    for writer in (e for e in expressions if isinstance(e,u.MaterialExpressionRuntimeVirtualTextureOutput)):
        rv=sources(writer)
        for key,channel in [('BaseColor','return'),('Normal','GrassN'),('Roughness','GrassR')]:
            target=writer;src=rv.get(key)
            if not src:continue
            if key=='Normal':
                # The cache stores world normals. Blend in tangent space before its transform.
                if not isinstance(src,u.MaterialExpressionTransform):raise RuntimeError('Unexpected RVT normal input')
                target=src
                key,src=next(iter(sources(target).items()))
            n=mix(src,lib.get_input_node_output_name_for_material_expression(target,src),channel)
            wire(n,'',target,key)
    return True
