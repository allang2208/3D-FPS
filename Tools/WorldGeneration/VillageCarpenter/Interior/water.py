"""Shallow workshop water. Read the project's shared impact slots in world centimetres."""
import unreal as u


def create_water(folder):
    name='M_CarpenterWashWater'
    path=folder+'/'+name
    lib=u.EditorAssetLibrary
    edit=u.MaterialEditingLibrary
    material=(lib.load_asset(path) if lib.does_asset_exist(path)
              else u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew()))
    edit.delete_all_material_expressions(material)
    material.set_editor_property('used_with_instanced_static_meshes',True)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    material.set_editor_property('tangent_space_normal',False)

    def node(kind):return edit.create_material_expression(material,getattr(u,'MaterialExpression'+kind))
    def link(src,dst,pin,output=''):
        if not edit.connect_material_expressions(src,output,dst,pin):raise RuntimeError('Water input '+pin)
    def prop(src,key):
        if not edit.connect_material_property(src,'',getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Water output '+key)
    def scalar(value):
        result=node('Constant')
        result.r=value
        return result
    normal=node('Custom')
    normal.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs={'P':node('WorldPosition'),'T':node('Time')}
    for i in range(8):
        key='WaterHit'+str(i)
        hit=node('VectorParameter')
        hit.set_editor_property('parameter_name',key)
        hit.set_editor_property('default_value',u.LinearColor(0,0,-10000,0))
        rgba=node('AppendVector')
        link(hit,rgba,'A','RGB')
        link(hit,rgba,'B','A')
        inputs['H'+str(i)]=rgba
    pins=[]
    for k in inputs:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',k)
        pins.append(pin)
    normal.set_editor_property('inputs',pins)
    for k,v in inputs.items():link(v,normal,k)
    normal.set_editor_property('code','''
float2 slope=.003*float2(sin(dot(P.xy,float2(.13,.08))+T*.75),cos(dot(P.xy,float2(-.07,.12))-T*.61));
float4 hits[8]={H0,H1,H2,H3,H4,H5,H6,H7};
[unroll] for(int i=0;i<8;++i){
    float age=T-hits[i].z;
    if(hits[i].w>0 && age>=0 && age<1.8){
        float2 d=P.xy-hits[i].xy;
        float r=max(.01,length(d)),front=r-54*age;
        float envelope=exp(-.012*front*front-2.1*age);
        slope+=d/r*cos(.81*front)*envelope*min(.24,hits[i].w*.74);
    }
}
return normalize(float3(-slope,1));
''')
    tint=node('Constant3Vector')
    tint.constant=u.LinearColor(.056,.083,.069,1)
    prop(tint,'BASE_COLOR')
    prop(normal,'NORMAL')
    prop(scalar(.23),'ROUGHNESS')
    prop(scalar(.28),'SPECULAR')
    opacity=node('LinearInterpolate')
    link(scalar(.35),opacity,'A')
    link(scalar(.71),opacity,'B')
    link(node('Fresnel'),opacity,'Alpha')
    prop(opacity,'OPACITY')
    edit.recompile_material(material)
    if not lib.save_loaded_asset(material,False):raise RuntimeError('Could not save bucket water')
    return material
