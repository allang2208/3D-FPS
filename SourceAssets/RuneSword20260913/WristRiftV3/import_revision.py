"""Install V3 arm animation and the locally sourced refraction crescent."""
import json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).parent;D='/Game/Weapons/AzureRunesword20260913';FX=D+'/WristRiftV3'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
content=P.parents[2]/'Content/Weapons/AzureRunesword20260913';backup=P/'Before';backup.mkdir(exist_ok=True)
clips=['Idle','Walk','Slash1','Slash2','Equip','Sprint']
for name in ['SK_AzureRunesword_Manny_Skeleton']+['A_RuneSword_'+n for n in clips]:
    source=content/(name+'.uasset');target=backup/source.name
    if not target.exists():shutil.copy2(source,target)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
receipt={'revision':'WristRiftV3','assets':[]}

def task(file,name,options,destination=D):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=destination;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=True;t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(destination+'/'+name)
    if not t.imported_object_paths or not obj:raise RuntimeError('Import did not complete: '+name)
    receipt['assets'].append({'source':str(file),'asset':obj.get_path_name()})
    return obj

sk=u.load_asset(D+'/SK_AzureRunesword_Manny');compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for name in clips:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True
    opt.import_materials=False;opt.import_textures=False;opt.skeleton=sk.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    seq=task(P/('Export/A_RuneSword_'+name+'.fbx'),'A_RuneSword_'+name,opt)
    if compression:seq.set_editor_property('bone_compression_settings',compression)
    u.EditorAssetLibrary.save_loaded_asset(seq)

mat=u.load_asset(FX+'/M_RuneRift') or A.create_asset('M_RuneRift',FX,u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(mat)
for name,value in [('blend_mode',u.BlendMode.BLEND_TRANSLUCENT),('shading_model',u.MaterialShadingModel.MSM_UNLIT),
                   ('two_sided',True),('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION),
                   ('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF),('refraction_depth_bias',.5)]:
    mat.set_editor_property(name,value)

def node(cls,**values):
    n=E.create_material_expression(mat,cls)
    for name,value in values.items():n.set_editor_property(name,value)
    return n

def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n=node(u.MaterialExpressionCustom,code=code,output_type=kind,inputs=pins)
    for name,(source,output) in inputs.items():E.connect_material_expressions(source,output,n,name)
    return n

uv=node(u.MaterialExpressionTextureCoordinate)
time=node(u.MaterialExpressionTime)
fade=node(u.MaterialExpressionScalarParameter,parameter_name='RiftFade',default_value=1.)
progress=node(u.MaterialExpressionScalarParameter,parameter_name='SweepProgress',default_value=1.06)
strength=node(u.MaterialExpressionScalarParameter,parameter_name='RiftStrength',default_value=.085)
mask=custom('float edge=pow(saturate(sin(UV.y*3.14159265)),1.35); '
            'float ends=smoothstep(0.0,0.045,UV.x)*(1.0-smoothstep(0.94,1.0,UV.x)); '
            'float reveal=1.0-smoothstep(Progress-0.04,Progress,UV.x); '
            'return edge*ends*reveal*Fade;',{'UV':(uv,''),'Progress':(progress,''),'Fade':(fade,'')})
noise_uv=custom('return UV*float2(3.0,1.4)+float2(Time*0.65,-Time*0.25);',
                {'UV':(uv,''),'Time':(time,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
# Existing local VFX pack supplies the animated optical disturbance normal.
noise_path='/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A'
noise=u.load_asset(noise_path)
if not noise:raise RuntimeError('Missing existing distortion normal: '+noise_path)
sample=node(u.MaterialExpressionTextureSample,texture=noise,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
E.connect_material_expressions(noise_uv,'',sample,'UVs')
normal=custom('return normalize(float3(N.xy*0.75,max(0.2,N.z)));',{'N':(sample,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
ior=custom('return 1.0+Mask*Strength;',{'Mask':(mask,''),'Strength':(strength,'')})
opacity=custom('return Mask*0.13;',{'Mask':(mask,'')})
color=custom('float ridge=exp(-pow((UV.y-0.78)*24.0,2.0)); '
             'return float3(0.08,0.48,1.0)*(ridge*2.2+0.07)*Mask;',
             {'UV':(uv,''),'Mask':(mask,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
for n,prop in [(normal,u.MaterialProperty.MP_NORMAL),(ior,u.MaterialProperty.MP_REFRACTION),
               (opacity,u.MaterialProperty.MP_OPACITY),(color,u.MaterialProperty.MP_EMISSIVE_COLOR)]:
    E.connect_material_property(n,'',prop)
E.layout_material_expressions(mat);E.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
receipt['refraction']={'material':mat.get_path_name(),'existing_noise':noise.get_path_name(),
    'reference_material':'/Game/RPGEnvironmentVFX/Essentials/Materials/M_HeatDistortion',
    'method':'IndexOfRefraction','depth_test':True,'translucency_pass':'BeforeDOF'}
for name in ['Slash1','Slash2']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    sm=task(P/('Export/SM_RuneRift_'+name+'.fbx'),'SM_RuneRift_'+name,opt,FX)
    sm.set_material(0,mat);u.EditorAssetLibrary.save_loaded_asset(sm)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));u.log('RUNESWORD_V3_IMPORT_COMPLETE')
