"""Dedicated hot-oil surfaces. UV1 on the film carries arrival seconds and signed edge distance (cm).
UV2 carries normalized downhill direction. CPD 0 is the replicated field age on the local renderer.
The kettle's four most recent real bubble ruptures drive local ring normals."""
from pathlib import Path
import json, sys
import unreal as u

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools/Fluids'))
from furnace_material_graph import node,wire,prop,custom,scalar
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
dest='/Game/WorldGeneration/TemperateHills/HotOil/FlowR2'
E.make_directory(dest)

def vec(m,name,default):
    v=node(m,u.MaterialExpressionVectorParameter)
    v.set_editor_property('parameter_name',name)
    v.set_editor_property('default_value',u.LinearColor(*default))
    return v

def uv(m,i):
    t=node(m,u.MaterialExpressionTextureCoordinate);t.set_editor_property('coordinate_index',i)
    return t

def material(role):
    name='M_Oil'+role
    m=E.load_asset(dest+'/'+name) if E.does_asset_exist(dest+'/'+name) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    translucent=role in ('Film','Stream')
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if translucent else u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided',True)
    if translucent:
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('screen_space_reflections',True)
    if role=='Stream':m.set_editor_property('used_with_spline_meshes',True)
    if role=='Bubble':m.set_editor_property('used_with_instanced_static_meshes',True)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    def surface(key,pin,v):
        prop(m,v,key);wire(v,slab,pin)
    t=node(m,u.MaterialExpressionTime);coords=uv(m,0)
    field_inputs={'UV':coords,'T':t}
    if role=='Body':
        now=scalar(m,'OilClock',0);now.set_editor_property('use_custom_primitive_data',True);now.set_editor_property('primitive_data_index',0)
        field_inputs['T']=now
    noise="""
struct FilmNoise {
 float h(float2 p){float3 q=frac(p.xyx*.1031);q+=dot(q,q.yzx+33.33);return frac((q.x+q.y)*q.z);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3.-2.*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1.),f.x),f.y);}
 float2 ring(float2 p,float3 e,float t){float a=t-e.z;float r=length(p-e.xy);float d=r-.015-.18*a;return a>=0&&a<.72?(p-e.xy)/max(r,.001)*sin(d*188.)*exp(-abs(d)*80.-a*5.):float2(0,0);}
}; FilmNoise oil;
"""
    if role=='Film':
        age=scalar(m,'SpreadAge',0);age.set_editor_property('use_custom_primitive_data',True);age.set_editor_property('primitive_data_index',0)
        life=scalar(m,'FieldLife',10.);life.set_editor_property('use_custom_primitive_data',True);life.set_editor_property('primitive_data_index',1)
        meta=uv(m,1);flow=uv(m,2)
        field_inputs.update(Meta=meta,Dir=flow,Age=age,Layer=uv(m,3))
        code="""
float2 p=(UV-.5)*13.;float age=max(0.,Age-Meta.x);
float2 dir=Dir*2.-1.;float travel=.27*(1.-exp(-min(7.,age)*1.5))+.012*min(age,8.);
float2 q=p-dir*travel+float2(.09*sin(p.y*2.+T*.24),.08*cos(p.x*1.3-T*.21));
float swirl=oil.n(q*1.27+oil.n(q*2.+1.));
float a=oil.n(q*4.3+T*.055),b=oil.n(q.yx*5.2-T*.046);
float front=exp(-age*3.)*.55;
float2 radial=UV-.5;float dist=length(radial);
float2 ripple=radial/max(.012,dist)*sin(136.*dist-11.*Age)*exp(-5.*dist-2.*age)*.09;
float thread=sin(dot(q,float2(-dir.y,dir.x))*7.+swirl*10.)*.045;
return float4(float2(a-.5,b-.5)*(.095+front*.24)+ripple+float2(-dir.y,dir.x)*thread,swirl,(1.-exp(-max(0.,Layer.x)*13.0))*smoothstep(-1.,18.,Meta.y));
"""
        coverage=custom(m,'float L=Life>.5?Life:10.;return smoothstep(0.,.12,Age-Meta.x)*smoothstep(0.,9.,Meta.y)*(1.-smoothstep(L-1.4,L+.45,Age));',{'Age':age,'Life':life,'Meta':meta})
    elif role=='Body':
        for i in range(4):field_inputs['B'+str(i)]=vec(m,'Burst'+str(i),(-3.,-3.,-30.,0.))
        code="""
float2 p=UV*5.;float2 q=p+float2(.43*sin(p.y+T*.29),.36*cos(p.x-T*.23));
float macro=oil.n(q*.92+oil.n(q*1.8+T*.07));
float veins=pow(saturate(1.-abs(oil.n(q*2.+macro*3.)*2.-1.)),7.);
float vein=saturate(.78*macro+.035*veins+.10*oil.n(q*4.));
float x=oil.n(q*3.+float2(T*.17,0))-.5,y=oil.n(q.yx*3.4-float2(0,T*.135))-.5;
float2 wave=oil.ring(UV,B0,T)+oil.ring(UV,B1,T)+oil.ring(UV,B2,T)+oil.ring(UV,B3,T);
float rim=smoothstep(.43,.5,length(UV-.5));
float2 meniscus=(UV-.5)*smoothstep(.465,.499,length(UV-.5))*.45;
return float4(float2(x,y)*.27+wave*.34+meniscus,vein,rim);
"""
    else:
        code="""
float2 q=UV*float2(5,3)+float2(T*.13,-T*1.6);
float a=oil.n(q+oil.n(q*.7));float b=oil.n(q*2.3+.4);
return float4((a-.5)*.15,(b-.5)*.09,a,b);
"""
    field=custom(m,noise+code,field_inputs,4)
    basecode='return lerp(float3(.018,.008,.003),float3(.108,.043,.009),saturate(F.z*.90+F.w*.12));'
    if role=='Body' or role=='Bubble':
        basecode='return lerp(float3(.0032,.0018,.0011),float3(.028,.011,.0042),F.z)+float3(.016,.005,.001)*F.w;'
    if role=='Film':
        basecode='return lerp(float3(.065,.029,.008),float3(.009,.004,.0018),saturate(.20+.56*F.w+.21*F.z));'
    if role=='Stream':basecode='return lerp(float3(.09,.033,.006),float3(.24,.114,.024),F.z);'
    surface('BASE_COLOR','BaseColor',custom(m,basecode,{'F':field},3))
    roughcode='return .052+.085*F.z+.015*F.w;' if role in ('Body','Bubble') else 'return .075+.12*F.z+.025*F.w;'
    surface('ROUGHNESS','Roughness',custom(m,roughcode,{'F':field}))
    surface('SPECULAR','Specular',scalar(m,'DielectricSpecular',.62 if role in ('Body','Bubble') else .47))
    surface('METALLIC','Metallic',scalar(m,'Metallic',0.))
    surface('NORMAL','Normal',custom(m,'return normalize(float3(F.xy,1.));',{'F':field},3))
    if role in ('Body','Bubble'):
        surface('EMISSIVE_COLOR','Emissive Color',custom(m,'return float3(.052,.016,.0025)*saturate(F.z*1.15+F.w*.55);',{'F':field},3))
    if translucent:
        opacity=custom(m,'return Coverage*lerp(.47,.90,saturate(.18+F.w*.68+F.z*.14));',{'Coverage':coverage,'F':field}) if role=='Film' else custom(m,'return .56+.27*F.z;',{'F':field})
        surface('OPACITY','Opacity',opacity)
        if role=='Film':
            emissive_code=noise+"""
float2 p=(UV-.5)*14.0;
float localAge=max(0.,Age-Meta.x);
float flare=exp(-localAge*2.4)*1.35;
float c1=oil.n(p*1.55+float2(T*.45,-T*.92)+F.xy*2.5);
float c2=oil.n(p*3.10+float2(-T*.55,-T*1.38)+c1*1.4);
float flame=pow(saturate(c1*.55+c2*.62),2.1);
float pool=saturate(.28+F.w*.72)*smoothstep(0.,14.,Meta.y);
float L=Life>.5?Life:10.;
float burnOut=1.-smoothstep(L-1.8,L-.1,Age);
float heat=saturate(flame*(.65+.55*F.w)+flare*.55)*pool*Coverage*burnOut;
float3 col=lerp(float3(1.15,.16,.01),float3(5.8,2.15,.22),saturate(flame+flare*.35));
return col*heat*(.55+1.15*heat);
"""
            surface('EMISSIVE_COLOR','Emissive Color',custom(m,emissive_code,{'UV':coords,'T':t,'Meta':meta,'Age':age,'Life':life,'F':field,'Coverage':coverage},3))
        elif role=='Stream':
            surface('EMISSIVE_COLOR','Emissive Color',custom(m,'return float3(.48,.13,.016)*(.45+.55*F.z);',{'F':field},3))
    prop(m,slab,'FRONT_MATERIAL')
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(m,False):raise RuntimeError(name)
    return m.get_path_name()

paths=[material(role) for role in ('Body','Bubble','Film','Stream')]
out=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
(out/'surface-saved.json').write_text(json.dumps(paths,indent=2),encoding='utf-8')
