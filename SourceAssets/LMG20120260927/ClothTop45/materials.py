"""Preserve lower cloth atlas; new upper panels use independently scaled fabric."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/ClothTop45';L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();report={}
def node(m,cls,**kw):
    n=L.create_material_expression(m,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,b,pin):
    n,out=a if isinstance(a,tuple) else (a,'')
    if not L.connect_material_expressions(n,out,b,pin):raise RuntimeError('Material pin '+pin)
def custom(m,code,names,out):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=out);pins=[]
    for name in names:i=u.CustomInput();i.set_editor_property('input_name',name);pins.append(i)
    n.set_editor_property('inputs',pins);return n
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def vector(m,name,value):return node(m,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))
for role in ['Cloth','Mount']:
    name='M_LMG201_C45_'+role;path=P+'/Materials/'+name;m=u.load_asset(path) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    m.set_editor_property('used_with_skeletal_mesh',True);m.set_editor_property('automatically_set_usage_in_editor',False);m.set_editor_property('two_sided',False);m.set_editor_property('use_material_attributes',True);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH if role=='Cloth' else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    attrs=node(m,u.MaterialExpressionMakeMaterialAttributes);L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    wet=scalar(m,'WeaponWetness',0.)
    if role=='Cloth':
        uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0);region=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=2);physical=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=3)
        textures={}
        for label in ['BaseColor','Normal','ORM','Relief']:
            tex=u.load_asset('/Game/Weapons/LMG201/Install30/Textures/T_201_R29_AmmoBag_'+label)
            sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if label=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
            textures[label]=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler,const_coordinate=0)
        # Filter high-frequency weave with screen derivatives; no world-space
        # texture swimming and no displacement of the silhouette.
        weave_code='''struct FabricField {
 float thread(float2 uv) {float2 p=uv-float2(.005,-.13215);float2 q=abs(p)-float2(.0585,.03065);float d=length(max(q,0))+min(max(q.x,q.y),0)-.004;float a=atan2(p.y/.03465,p.x/.0625);return exp(-pow(d/.00035,2))*smoothstep(.05,.50,sin(a*72));}
}; FabricField f;float2 p=UV/.00065;float aa=saturate(1-max(fwidth(p.x),fwidth(p.y)));float x=6.2831853*p.x,y=6.2831853*p.y;float thread=f.thread(UV);float h=(sin(x)*.55+sin(y)*.45)*aa;float e=.000035;float dx=(f.thread(UV+float2(e,0))-f.thread(UV-float2(e,0)))*.000028/(2*e);float dy=(f.thread(UV+float2(0,e))-f.thread(UV-float2(0,e)))*.000028/(2*e);return float3(h+thread*.35,.065*cos(x)*aa-dx,.052*cos(y)*aa-dy);'''
        weave=custom(m,weave_code,['UV'],u.CustomMaterialOutputType.CMOT_FLOAT3);link(physical,weave,'UV')
        tint=vector(m,'UpperFabricTint',(.0865,.1144,.0578))
        base=custom(m,'float a=saturate(R.x);float3 fresh=Tint*(1+D.x*.028);return lerp(Base,fresh,a)*(1-.31*saturate(Wet));',['Base','R','D','Tint','Wet'],u.CustomMaterialOutputType.CMOT_FLOAT3)
        for source,pin in [((textures['BaseColor'],'RGB'),'Base'),(region,'R'),(weave,'D'),(tint,'Tint'),(wet,'Wet')]:link(source,base,pin)
        normal=custom(m,'return normalize(lerp(N,normalize(float3(D.yz,1)),saturate(R.x)));',['N','D','R'],u.CustomMaterialOutputType.CMOT_FLOAT3)
        for source,pin in [((textures['Normal'],'RGB'),'N'),(weave,'D'),(region,'R')]:link(source,normal,pin)
        rough=custom(m,'float r=lerp(Old,.79+.018*D.x,saturate(R.x));return r*(1-.30*saturate(Wet));',['Old','D','R','Wet'],u.CustomMaterialOutputType.CMOT_FLOAT1)
        for source,pin in [((textures['ORM'],'G'),'Old'),(weave,'D'),(region,'R'),(wet,'Wet')]:link(source,rough,pin)
        ao=custom(m,'return lerp(AO,1,saturate(R.x));',['AO','R'],u.CustomMaterialOutputType.CMOT_FLOAT1);link((textures['ORM'],'R'),ao,'AO');link(region,ao,'R')
        fuzz=custom(m,'return lerp(Old*.17,.11,saturate(R.x));',['Old','R'],u.CustomMaterialOutputType.CMOT_FLOAT1);link((textures['Relief'],'G'),fuzz,'Old');link(region,fuzz,'R')
        link(fuzz,attrs,'ClearCoat');link(vector(m,'FabricFuzzTint',(.032,.038,.024)),attrs,'SubsurfaceColor');link(normal,attrs,'Normal');link(ao,attrs,'AmbientOcclusion')
        link(scalar(m,'FabricMetallic',0.),attrs,'Metallic');link(scalar(m,'Specular',.35),attrs,'Specular')
    else:
        tint=vector(m,'MountTint',(.023,.028,.026));base=custom(m,'return Tint*(1-.15*saturate(Wet));',['Tint','Wet'],u.CustomMaterialOutputType.CMOT_FLOAT3);link(tint,base,'Tint');link(wet,base,'Wet');rough=custom(m,'return lerp(.49,.34,saturate(Wet));',['Wet'],u.CustomMaterialOutputType.CMOT_FLOAT1);link(wet,rough,'Wet');link(scalar(m,'MountMetallic',.15),attrs,'Metallic');link(scalar(m,'Specular',.42),attrs,'Specular')
    link(base,attrs,'BaseColor');link(rough,attrs,'Roughness')
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compile '+str(errors))
    E.set_metadata_tag(m,'201ClothTopRevision','ClothTop45: retained lower atlas, explicit UV2 transition, UV3 fabric metres, skeletal box usage')
    if not E.save_loaded_asset(m,False):raise RuntimeError('Save '+path)
    report[role]=m.get_path_name()
(O/'materials.json').write_text(json.dumps(report,indent=2));print('C45_MATERIALS_SAVED',len(report),flush=True)
