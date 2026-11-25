"""Worn lime from the existing Quixel scan, with wear placed in the actual kitchen's coordinates."""
import unreal as u

DEST='/Game/WorldGeneration/VillageTavern/Inn'
SCAN='/Game/Dungeons/TunnelStyleIncinerator20261111/Quixel/CrackedPaintedPlaster_d91bfe39/Textures/T_CrackedPaintedPlaster_d91bfe39_'
CODE="""
struct GrainNoise
{
    float hash(float2 p) {
        float3 p3=frac(float3(p.x,p.y,p.x)*.1031);
        p3+=dot(p3,p3.yzx+33.33);
        return frac((p3.x+p3.y)*p3.z);
    }
    float value(float2 p) {
        float2 i=floor(p), f=frac(p);
        f=f*f*(3.-2.*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1.),f.x),f.y);
    }
};
GrainNoise noise;
float variation=dot(Scan,float3(.31,.56,.13));
float2 plane=UV*142.;
float cloud=noise.value(plane*.044+float2(.27,9.2));
float pock=noise.value(plane*.213+float2(25.1,4.7));
float scratch=noise.value(plane*float2(.47,.081)+pock);
float stipple=saturate((variation-.23)*2.);
float shiftedZ=P.z+(cloud-.5)*29.+(pock-.5)*12.;
float toe=1.-smoothstep(5.,56.,shiftedZ);
float chimney=exp(-pow(abs(P.x-588.)/125.,2.)-pow(abs(P.y+42.)/146.,2.))*smoothstep(63.,264.,shiftedZ);
float splash=exp(-pow(abs(P.y-291.)/81.,2.)-pow(abs(P.x-315.)/52.,2.)-pow(abs(shiftedZ-73.)/48.,2.));
float ledge=exp(-pow(abs(P.x-225.)/102.,4.)-pow(abs(P.y-338.)/26.,2.)-pow(abs(shiftedZ-85.)/32.,2.));
float side=exp(-pow(abs(P.y-101.)/108.,4.)-pow(abs(P.x-321.)/25.,2.)-pow(abs(shiftedZ-91.)/31.,2.));
float hand=exp(-pow(abs(P.y-489.)/26.,2.)-pow(abs(P.x-94.)/22.,2.)-pow(abs(shiftedZ-120.)/42.,2.));
float worn=saturate(.31*cloud+.32*pock+.24*scratch+.13*stipple);
float field=smoothstep(.22,.79,worn);
float mineral=saturate(.5+.41*(cloud-.5)+.28*(pock-.5)+.38*(stipple-.5));
float3 lime=lerp(float3(.218,.201,.167),float3(.352,.331,.282),mineral);
float wornZone=saturate(toe*.68+chimney*.53+splash*.31+ledge*.38+side*.32+hand*.30);
lime*=1.+(field-.5)*(.105+.32*wornZone);
lime=lerp(lime,float3(.124,.098,.071),toe*(.37+.39*field));
lime=lerp(lime,float3(.074,.062,.049),chimney*(.56+.33*pock));
float marks=saturate(splash*.63+ledge*.82+side*.64+hand*.71);
lime=lerp(lime,float3(.143,.093,.057),marks*(.32+.67*smoothstep(.33,.72,.65*scratch+.35*pock)));
return lime;
"""
def finishes():
    ed=u.EditorAssetLibrary;graph=u.MaterialEditingLibrary
    name='M_InnWorkingLime_JoineryR4';path=DEST+'/'+name
    mat=ed.load_asset(path) if ed.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    graph.delete_all_material_expressions(mat);mat.set_editor_property('used_with_instanced_static_meshes',True)
    def expr(cls,x,y):return graph.create_material_expression(mat,getattr(u,'MaterialExpression'+cls),x,y)
    def link(a,key,b,pin):
        if not graph.connect_material_expressions(a,key,b,pin):raise RuntimeError(pin)
    def output(a,key,prop):
        if not graph.connect_material_property(a,key,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
    def sample(role,sampler,y):
        node=expr('TextureSample',-690,y);texture=ed.load_asset(SCAN+role)
        if not texture:raise RuntimeError(role)
        node.texture=texture
        sampler={u.TextureCompressionSettings.TC_NORMALMAP:'NORMAL',u.TextureCompressionSettings.TC_MASKS:'MASKS',
                 u.TextureCompressionSettings.TC_GRAYSCALE:'GRAYSCALE' if texture.srgb else 'LINEAR_GRAYSCALE',
                 u.TextureCompressionSettings.TC_ALPHA:'ALPHA'}.get(texture.compression_settings,'COLOR' if texture.srgb else 'LINEAR_COLOR')
        node.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+('VIRTUAL_' if texture.virtual_texture_streaming else '')+sampler)
        return node
    custom=expr('Custom',-205,-140);custom.set_editor_property('code',CODE)
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs=[]
    for name in ['P','Scan','UV']:
        n=u.CustomInput();n.set_editor_property('input_name',name);inputs.append(n)
    custom.set_editor_property('inputs',inputs)
    link(expr('TextureCoordinate',-700,-550),'',custom,'UV')
    coords=expr('VertexInterpolator',-470,-410)
    link(expr('PreSkinnedPosition',-720,-410),'',coords,'')
    link(coords,'',custom,'P')
    link(sample('BaseColor','COLOR',-130),'RGB',custom,'Scan');output(custom,'','BASE_COLOR')
    output(sample('Normal','NORMAL',130),'RGB','NORMAL')
    output(sample('Roughness','MASKS',350),'R','ROUGHNESS')
    output(sample('AO','MASKS',570),'R','AMBIENT_OCCLUSION')
    graph.recompile_material(mat)
    if not ed.save_loaded_asset(mat,False):raise RuntimeError(path)
    donor=ed.load_asset('/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_Mirror')
    glass,=[slot.material_interface for slot in donor.static_materials if str(slot.material_slot_name)=='RS_Mirror']
    return {'Lime':mat,'Mirror':glass,'Brass':ed.load_asset('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBrass'),
            'Oak':ed.load_asset('/Game/WorldGeneration/VillageTavern/Furniture/M_TavernOiledOak')}
