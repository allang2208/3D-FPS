"""Produce and save the spectral blade packages. No PIE or preview capture."""
import json
from pathlib import Path
import unreal as u

SOURCE=Path('D:/FPS3D/FPSGAME/SourceAssets/RuneSpectralBlade20260927')
DEST='/Game/Weapons/RuneSpectralBlade20260927'
L=u.MaterialEditingLibrary
T=u.AssetToolsHelpers.get_asset_tools()
receipt={'materials':{},'meshes':{},'saved':False,'runtime_tested':False}

def node(m,cls):return L.create_material_expression(m,cls)
def connect(a,out,b,pin):
    # UE math nodes expose their lone connector as an empty name; BSDF labels
    # may contain spaces although the C++ member names do not.
    names=[str(n) for n in L.get_material_expression_input_names(b)]
    normalized=pin.replace(' ','').lower()
    actual=next((n for n in names if n.replace(' ','').lower()==normalized),pin)
    if pin=='Input' and names:actual=names[0]
    if not L.connect_material_expressions(a,out,b,actual):raise RuntimeError('Cannot connect '+pin+'; available '+str(names))
def param(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def mask(m,source,r=False,g=False,b=False,a=False):
    n=node(m,u.MaterialExpressionComponentMask)
    for key,value in [('r',r),('g',g),('b',b),('a',a)]:n.set_editor_property(key,value)
    connect(source,'',n,'Input');return n

common='''
float t = Clock + Phase;
float flow = 0.5 + 0.5 * sin(UV.x * 23.0 - t * 2.3);
float pulse = 0.88 + 0.12 * sin(t * 1.6);
float alpha;
float3 color;
'''
programs={
 'M_SpectralBody':common+'''
float strand = pow(saturate(0.5+0.5*sin(UV.x*37.0+UV.y*44.0-t*1.4)),12.0);
alpha = (0.78 + 0.12*pow(Rim,1.1) + 0.025*strand) * (0.97+0.03*sin(t*1.6));
color = lerp(float3(0.016,0.055,0.55),float3(0.025,0.20,1.08),saturate(Rim+strand*0.15));
color *= 0.85 + flow*0.15;
return float4(color*alpha*Fade,alpha*Fade);
''',
 'M_SpectralEdge':common+'''
alpha = (0.84+0.10*Rim) * (0.97+0.03*sin(t*1.6));
color = float3(0.03,0.27,1.35)*(0.92+0.08*flow);
return float4(color*alpha*Fade,alpha*Fade);
''',
 'M_SpectralRunes':common+'''
float travelling = pow(saturate(0.5+0.5*sin(UV.x*15.0-t*2.8)),5.0);
alpha = 0.78+0.15*travelling;
color = float3(0.10,0.50,1.75)*(0.60+0.55*travelling);
return float4(color*alpha*Fade,alpha*Fade);
''',
 'M_SpectralWake':common+'''
float side = pow(saturate(1.0-abs(UV.y*2.0-1.0)),2.5);
float ends = smoothstep(0.0,0.05,UV.x)*pow(saturate(1.0-UV.x),1.4);
float wisps = 0.65+0.35*sin(UV.x*31.0-t*8.0);
alpha = side*ends*wisps*0.27;
color = float3(0.025,0.25,1.2);
return float4(color*alpha*Fade,alpha*Fade);
''',
 'M_SpectralImpact':common+'''
float2 q = UV*2.0-1.0;
float r2 = dot(q,q);
float r = sqrt(r2);
float age = saturate(1.0-Fade); // Normalized age of this contact's sampled lifetime.
float3 variation = frac(sin((Seed*79.13+Phase)*float3(12.9898,39.346,73.156))*43758.5453);
float angle = atan2(q.y,q.x);
float offset = Seed*47.0+Phase;
float life = lerp(0.80,1.12,variation.z);
float edge = 1.0-smoothstep(0.82,1.0,r);
if (Kind > 2.5) {
    float lobes = 0.60+0.28*sin(angle*(4.0+floor(variation.x*5.0))+r*15.0-age*9.0+offset)
        +0.18*sin(angle*(9.0+floor(variation.y*5.0))-r*21.0+offset*1.7);
    float cloud = exp(-r2*lerp(2.8,4.4,variation.y))*edge*saturate(lobes);
    float envelope = pow(saturate(1.0-age/(0.65*life)),1.6);
    alpha = cloud*0.65*envelope;
    color = float3(0.04,0.95,10.0);
} else if (Kind > 1.5) {
    float contour = 0.67+0.075*sin(angle*(3.0+floor(variation.x*4.0))+offset+age*2.0)
        +0.035*sin(angle*9.0-offset*1.3);
    float arcs = smoothstep(0.02,0.42,0.5+0.5*sin(angle*(2.0+floor(variation.y*4.0))+offset));
    float ring = exp(-pow((r-contour)/lerp(0.032,0.060,variation.y),2.0));
    float halo = exp(-pow((r-contour)/0.12,2.0))*0.24;
    float envelope = pow(saturate(1.0-age/(0.62*life)),0.8);
    alpha = saturate(ring+halo)*edge*envelope*arcs;
    color = float3(0.12,2.6,16.0);
} else if (Kind > 0.5) {
    float core = exp(-r2*lerp(4.8,7.2,variation.x));
    float envelope = pow(saturate(1.0-age/(0.28*life)),1.3);
    alpha = saturate(core+exp(-r2*2.4)*0.28)*edge*envelope;
    color = float3(0.2,2.8,18.0)+core*float3(5.5,8.5,12.0)*(1.0-smoothstep(0.02,0.13,age));
} else {
float disc = exp(-r2*3.3)*(1.0-smoothstep(0.60,1.0,r2));
float core = exp(-r2*19.0);
alpha = saturate(disc*0.95+core*0.12)*pow(saturate(1.0-age/lerp(0.68,1.0,variation.z)),0.75);
color = float3(0.055,1.1,9.0)+core*float3(0.35,1.5,5.0);
}
return float4(color*lerp(0.85,1.18,variation.y)*alpha,alpha);
'''
}

def impact_role(m,custom):
    # Conventional ISM custom data is read in the vertex stage, then interpolated.
    pins=list(custom.get_editor_property('inputs'))
    for index,name in enumerate(('Kind','Seed')):
        if any(str(p.get_editor_property('input_name'))==name for p in pins):continue
        entry=u.CustomInput();entry.set_editor_property('input_name',name);pins.append(entry)
        custom.set_editor_property('inputs',pins)
        role=node(m,u.MaterialExpressionPerInstanceCustomData)
        role.set_editor_property('data_index',index);role.set_editor_property('const_default_value',0.0)
        interpolator=node(m,u.MaterialExpressionVertexInterpolator)
        connect(role,'',interpolator,'Input');connect(interpolator,'',custom,name)

materials={}
for name,code in programs.items():
    if name not in globals().get('SPECTRAL_MATERIAL_NAMES',programs):continue
    m=u.load_asset(DEST+'/'+name) or T.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    # Existing sword materials can already be rooted through a native CDO.
    # Update their analytic shader in place; deleting rooted expressions asserts.
    m.set_editor_property('use_material_attributes',False)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    # Closed sword surfaces are single-sided; only the wake sheets need both sides.
    m.set_editor_property('two_sided',name in ('M_SpectralWake','M_SpectralImpact'))
    # The same wake surface is consumed by the bounded impact ISM component.
    m.set_editor_property('used_with_instanced_static_meshes',name in ('M_SpectralWake','M_SpectralImpact'))
    existing=next((e for e in L.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom)),None)
    if existing:
        if name=='M_SpectralImpact':impact_role(m,existing)
        existing.set_editor_property('code',code)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError(name+' shader compile: '+str(list(errors)))
        materials[name]=m
        receipt['materials'][name]={'path':m.get_path_name(),'compiler_errors':list(errors),'substrate':'UnlitBSDF','textures':0}
        continue
    uv=node(m,u.MaterialExpressionTextureCoordinate);uv.coordinate_index=0
    clock=node(m,u.MaterialExpressionTime)
    fresnel=node(m,u.MaterialExpressionFresnel);fresnel.set_editor_property('exponent',2.4)
    custom=node(m,u.MaterialExpressionCustom)
    custom.set_editor_property('description','Spectral local flow and real transparency')
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=['UV','Clock','Rim','Phase','Fade']
    inputs=[]
    for pin in pins:
        entry=u.CustomInput();entry.set_editor_property('input_name',pin);inputs.append(entry)
    custom.set_editor_property('inputs',inputs)
    custom.set_editor_property('code',code)
    for pin,source in zip(pins,[uv,clock,fresnel,param(m,'SpectralPhase',0),param(m,'SpectralFade',1)]):connect(source,'',custom,pin)
    if name=='M_SpectralImpact':impact_role(m,custom)
    rgb=mask(m,custom,r=True,g=True,b=True)
    opacity=mask(m,custom,a=True)
    transmission=node(m,u.MaterialExpressionOneMinus);connect(opacity,'',transmission,'Input')
    surface=node(m,u.MaterialExpressionSubstrateUnlitBSDF)
    connect(rgb,'',surface,'EmissiveColor');connect(transmission,'',surface,'TransmittanceColor')
    if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Missing Substrate front material')
    # Keep the legacy fields readable to engine tools without relying on them to render.
    L.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    L.layout_material_expressions(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(name+' shader compile: '+str(list(errors)))
    materials[name]=m
    receipt['materials'][name]={'path':m.get_path_name(),'compiler_errors':list(errors),'substrate':'UnlitBSDF','textures':0}

meshes=[]
for name in globals().get('SPECTRAL_MESH_NAMES',('SM_SpectralRuneBlade','SM_SpectralWake','SM_SpectralWisp','SM_SpectralImpactParticle')):
    task=u.AssetImportTask();task.filename=str(SOURCE/(name+'.fbx'))
    task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
    opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.automated_import_should_detect_type=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.generate_lightmap_u_vs=False
    opts.static_mesh_import_data.auto_generate_collision=False;task.options=opts
    T.import_asset_tasks([task])
    mesh=u.load_asset(DEST+'/'+name)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Import failed '+name)
    if mesh.get_num_triangles(0)<=0:
        raise RuntimeError('Import produced an empty mesh: '+name+'; end Play before importing again')
    slots=[]
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unexpected material slot '+key)
        mesh.set_material(i,materials[key]);slots.append(key)
    # Tiny translucent VFX meshes deliberately use the conventional raster path.
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=False;mesh.set_editor_property('nanite_settings',settings)
    meshes.append(mesh)
    receipt['meshes'][name]={'path':mesh.get_path_name(),'slots':slots,'triangles':mesh.get_num_triangles(0),'bounds':str(mesh.get_bounds())}

packages=[asset.get_outer() for asset in list(materials.values())+meshes]
if not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Package save failed')
receipt['saved']=True
(SOURCE/globals().get('SPECTRAL_RECEIPT_NAME','import_receipt.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('SPECTRAL_BLADE_SAVED '+json.dumps(receipt))
