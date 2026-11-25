"""One metric road-edge policy for the visible decal and the dry-surface RVT."""
import unreal as u

TAG = 'VillageRoadEdge20261115'
EDGE_CODE = '''
// B is signed distance: 0.5 at the authored road boundary, +/-250 cm.
float2 p=(UV-.5)*Span;
float2 q=p/175.; float2 i=floor(q), f=frac(q); f=f*f*(3.-2.*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),
 dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1.,float2(127.1,311.7))))*43758.5453);
float coarse=lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
q=p/31.+17.; i=floor(q); f=frac(q); f=f*f*(3.-2.*f);
h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),
 dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1.,float2(127.1,311.7))))*43758.5453);
float fine=lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
float distance=(M.b-.5)*500.;
float rag=((coarse-.5)*1.6+(fine-.5)*.55+(H-.5)*.32)*Breakup;
float edge=smoothstep(-Width*.85,Width*.25,distance+rag);
// Preserve the original wheel-track density, including the softer centre strip.
float road=edge*max(.67,M.r);
float skirt=smoothstep(.015,.92,M.g)*(.60+.40*H)*lerp(.72,1.,fine);
float2 border=min(UV,1.-UV)*Span;
float bounds=smoothstep(0.,70.,min(border.x,border.y))*all(UV>=0.)*all(UV<=1.);
return float2(road,skirt)*bounds;
'''

def build_weights(material, mask, uv, height, span):
    lib=u.MaterialEditingLibrary
    def node(cls):
        obj=lib.create_material_expression(material,cls)
        obj.set_editor_property('desc',TAG)
        return obj
    def scalar(name,value):
        obj=node(u.MaterialExpressionScalarParameter)
        obj.set_editor_property('parameter_name',name)
        obj.set_editor_property('default_value',value)
        return obj
    extent=node(u.MaterialExpressionConstant2Vector)
    extent.set_editor_property('r',span[0]);extent.set_editor_property('g',span[1])
    obj=node(u.MaterialExpressionCustom)
    obj.set_editor_property('code',EDGE_CODE)
    obj.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT2)
    values={'M':(mask,'RGB'),'UV':(uv,''),'H':(height,'R'),'Span':(extent,''),
            'Width':(scalar('RoadEdgeFadeCm',110.),''),'Breakup':(scalar('RoadEdgeBreakupCm',48.),'')}
    pins=[]
    for name in values:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    obj.set_editor_property('inputs',pins)
    for name,(source,channel) in values.items():
        if not lib.connect_material_expressions(source,channel,obj,name):raise RuntimeError('Road edge '+name)
    return obj
