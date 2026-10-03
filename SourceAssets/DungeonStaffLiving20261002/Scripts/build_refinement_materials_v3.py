"""Create owned materials from accepted carpet and installed Hospital Bed linen."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'RefinementV3';BASE='/Game/Dungeons/StaffLiving20261002/RefinementV3'
L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Required source asset missing: '+p)
    return a
def save(a):
    if not a.get_path_name().startswith(BASE+'/'):raise RuntimeError('Save outside refinement')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
    report['saved_material_assets'].append(a.get_path_name());record()

def build_materials(report_arg,record_arg):
    global report,record
    report=report_arg;record=record_arg
    report.setdefault('saved_material_assets',[])
    source='/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceNavyCarpet'
    path=BASE+'/Materials/M_Staff_NavyCarpet_V3';carpet=u.load_asset(path)
    if not carpet:
        carpet=A.duplicate_asset(path.rsplit('/',1)[1],BASE+'/Materials',load(source))
        if not carpet:raise RuntimeError('Cannot duplicate accepted carpet')
        carpet.set_editor_property('used_with_nanite',True);carpet.set_editor_property('used_with_instanced_static_meshes',True)
        for node in L.get_material_expressions(carpet):
            if isinstance(node,u.MaterialExpressionCustom):
                code=node.get_editor_property('code')
                if 'float mask=smoothstep(8,16,Position.z)' in code:
                    code=code.replace('float mask=smoothstep(8,16,Position.z)*smoothstep(.75,.95,n.z);','float mask=smoothstep(.75,.95,n.z);')
                    code=code.replace('(Position.xy-float2(-2400,-1300))','Position.xy')
                    node.set_editor_property('code',code)
                elif 'float2 p=P.xy-float2(-2400,-1300)' in code:
                    node.set_editor_property('code','return float2(0,0);')
        errors=list(L.recompile_material(carpet))
        if errors:raise RuntimeError('Carpet compile failed: '+str(errors))
        save(carpet)
    mipath=BASE+'/Materials/MI_Staff_NavyCarpet_V3';mi=u.load_asset(mipath)
    if not mi:
        mi=A.create_asset('MI_Staff_NavyCarpet_V3',BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mi,carpet)
        L.set_material_instance_scalar_parameter_value(mi,'PileTileCm',90.)
        L.set_material_instance_scalar_parameter_value(mi,'PileReliefDepthCm',.38)
        L.set_material_instance_scalar_parameter_value(mi,'FineNormalStrength',.65)
        L.update_material_instance(mi);save(mi)
    report['carpet']=dict(source=source,material=mipath,physical_tile_cm=90,height_cm=.38,
        near_pom_steps=8,refinements=2,height_mask_removed=True,library_assets_modified=False)

    # These already-installed maps stay in their original packages. Patch UVs
    # select a clean patterned linen island from the real bed atlas, rather than
    # stretching the complete atlas (including its black seams) over a new quilt.
    linen='/Game/Props/HospitalBed20260929/Textures/'
    plain='/Game/SubstrateMaterials/Textures/02_Upholstery/Textiles/'
    textures={k:load(p) for k,p in {
        'ColorTex':linen+'T_HospitalBed_LinenBaseColor','NormalTex':linen+'T_HospitalBed_LinenNormal',
        'MRTex':linen+'T_HospitalBed_LinenMR','FineTex':plain+'T_TextilePlain_N'}.items()}
    cloth_path=BASE+'/Materials/M_Staff_Linen_V3';mat=u.load_asset(cloth_path)
    if not mat:
        mat=A.create_asset('M_Staff_Linen_V3',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)
        mat.set_editor_property('use_material_attributes',True)
        mat.set_editor_property('two_sided',False)
        mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('used_with_instanced_static_meshes',True)
        def node(cls):return L.create_material_expression(mat,cls)
        def wire(a,b,pin,output=''):
            if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)
        def scalar(name,value):
            a=node(u.MaterialExpressionScalarParameter);a.set_editor_property('parameter_name',name);a.set_editor_property('default_value',value);return a
        def vector(name,value):
            a=node(u.MaterialExpressionVectorParameter);a.set_editor_property('parameter_name',name);a.set_editor_property('default_value',u.LinearColor(*value));return a
        uv=node(u.MaterialExpressionTextureCoordinate)
        pos=node(u.MaterialExpressionWorldPosition);camera=node(u.MaterialExpressionCameraPositionWS)
        inputs={'UV':uv,'P':pos,'Camera':camera,'Tint':vector('LinenTint',(.66,.63,.53,1)),
            'PatternPatch':vector('PatternPatch',(.095,.655,.195,.195)),
            'NormalStrength':scalar('LinenNormalStrength',.32),'FineStrength':scalar('FiberStrength',.65),
            'FineScale':scalar('FiberScale',4.3),'FuzzAmount':scalar('FuzzAmount',.28)}
        for key,texture in textures.items():
            n=node(u.MaterialExpressionTextureObjectParameter);n.set_editor_property('parameter_name',key)
            n.set_editor_property('texture',texture)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key in ('NormalTex','FineTex') else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MRTex' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            inputs[key]=n
        shader=node(u.MaterialExpressionCustom);shader.set_editor_property('description','Reused bed linen patch, physical weave UV, RNM detail and bounded distance fade')
        shader.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
        pins=[]
        for name in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
        shader.set_editor_property('inputs',pins)
        for name,n in inputs.items():wire(n,shader,name)
        outputs=[]
        for name,width in [('NormalTangent',3),('AO',1),('Fuzz',1)]:
            p=u.CustomOutput();p.set_editor_property('output_name',name)
            p.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));outputs.append(p)
        shader.set_editor_property('additional_outputs',outputs)
        shader.set_editor_property('code',r'''
float2 mirrorUV=abs(frac(UV*.5)*2-1);
float2 q=PatternPatch.xy+mirrorUV*PatternPatch.z;
float2 gx=ddx(q),gy=ddy(q);
float3 color=Texture2DSampleGrad(ColorTex,ColorTexSampler,q,gx,gy).rgb;
float3 mr=Texture2DSampleGrad(MRTex,MRTexSampler,q,gx,gy).rgb;
float2 xy=Texture2DSampleGrad(NormalTex,NormalTexSampler,q,gx,gy).rg*2-1;
float2 mirrorSign=2*step(0,frac(UV*.5)*2-1)-1;
xy*=mirrorSign*NormalStrength;
float3 normal=normalize(float3(xy,sqrt(max(1-dot(xy,xy),.01))));
float2 fUV=UV*FineScale,fx=ddx(fUV),fy=ddy(fUV);
float screenMip=log2(max(max(length(fx),length(fy))*2048,1));
float fade=(1-smoothstep(160,480,length(P-Camera)))*(1-smoothstep(1.2,3.2,screenMip));
[branch] if(fade>.001){
 float2 d=Texture2DSampleGrad(FineTex,FineTexSampler,fUV,fx,fy).rg*2-1;
 d*=FineStrength*fade;
 float3 dn=normalize(float3(d,sqrt(max(1-dot(d,d),.01))));
 float3 t=normal+float3(0,0,1),r=dn*float3(-1,-1,1);
 normal=normalize(t*dot(t,r)/max(t.z,.001)-r);
}
NormalTangent=normal;AO=lerp(.95,1,saturate(mr.r));Fuzz=FuzzAmount;
return float4(Tint.rgb*lerp(.66,1.05,color),clamp(.74+mr.g*.15,.74,.93));
''')
        attr=node(u.MaterialExpressionMakeMaterialAttributes)
        L.connect_material_property(attr,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        rgb=node(u.MaterialExpressionComponentMask)
        for k,v in [('r',True),('g',True),('b',True),('a',False)]:rgb.set_editor_property(k,v)
        wire(shader,rgb,'');wire(rgb,attr,'BaseColor')
        rough=node(u.MaterialExpressionComponentMask)
        for k,v in [('r',False),('g',False),('b',False),('a',True)]:rough.set_editor_property(k,v)
        wire(shader,rough,'');wire(rough,attr,'Roughness')
        wire(shader,attr,'Normal','NormalTangent');wire(shader,attr,'AmbientOcclusion','AO');wire(shader,attr,'ClearCoat','Fuzz')
        wire(vector('FuzzColor',(.29,.28,.23,1)),attr,'SubsurfaceColor')
        wire(scalar('Metallic',0),attr,'Metallic');wire(scalar('Specular',.25),attr,'Specular')
        errors=list(L.recompile_material(mat))
        if errors:raise RuntimeError('Linen compile failed: '+str(errors))
        save(mat)
    for name,tint,fuzz,strength in [('M_Staff_Terry_V3',(.61,.63,.53,1),.48,.85),('M_Staff_Hem_V3',(.39,.41,.32,1),.25,.55)]:
        path=BASE+'/Materials/'+name;m=u.load_asset(path)
        if not m:
            m=A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
            L.set_material_instance_parent(m,mat)
            L.set_material_instance_vector_parameter_value(m,'LinenTint',u.LinearColor(*tint))
            L.set_material_instance_scalar_parameter_value(m,'FuzzAmount',fuzz)
            L.set_material_instance_scalar_parameter_value(m,'FiberStrength',strength)
            L.update_material_instance(m);save(m)
    report['linen']=dict(source='Hospital Bed by loxfear, CC-BY-4.0',textures=[t.get_path_name() for t in textures.values()],
        atlas_patch=[.095,.655,.195,.195],metallic=0,runtime_cloth=False)

    texture_path=BASE+'/Textures/T_Staff_Notices_V3_BaseColor';tex=u.load_asset(texture_path)
    if not tex:
        task=u.AssetImportTask();task.filename=str(OUT/'Authored/T_Staff_Notices_V3_BaseColor.png')
        task.destination_path=BASE+'/Textures';task.destination_name='T_Staff_Notices_V3_BaseColor'
        task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=load(texture_path)
        tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('max_texture_size',4096);tex.set_editor_property('never_stream',False)
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        save(tex)
    path=BASE+'/Materials/M_Staff_Notices_V3';mat=u.load_asset(path)
    if not mat:
        mat=A.create_asset('M_Staff_Notices_V3',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('used_with_instanced_static_meshes',True)
        slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
        slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        col=L.create_material_expression(mat,u.MaterialExpressionTextureSample);col.set_editor_property('texture',tex)
        col.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        rough=L.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.84)
        L.connect_material_expressions(col,'RGB',slab,'BaseColor');L.connect_material_expressions(rough,'',slab,'Roughness')
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=list(L.recompile_material(mat))
        if errors:raise RuntimeError('Notice compile failed '+str(errors))
        save(mat)
    report['notices']=dict(texture=texture_path,dimensions=[4096,2048],streaming=True,real_content=True)
    record()
