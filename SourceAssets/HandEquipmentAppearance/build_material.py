"""Build the accepted 3 cm glove parent; assignment is a separate explicit step."""
import json
import time
from pathlib import Path
import unreal as u

OUT=Path(__file__).parent
DEST='/Game/Characters/ArmsGloveCuff3cmCandidate'
OLD='/Game/Characters/ArmsLeatherCandidate'
SOURCE='/Game/Weapons/M4InfimaV3'
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
skin_tint=u.LinearColor(.36,.235,.185,1)
profile=u.load_asset('/Game/Characters/ArmsSkinSleeveCandidate/SSP_ForearmSkin');assert profile
task=u.AssetImportTask();task.filename=str(OUT/'T_Manny_Cuff3cmField.png')
task.destination_path=DEST;task.destination_name='T_Manny_Cuff3cmField'
task.automated=True;task.replace_existing=True;task.save=True
A.import_asset_tasks([task])
cuff_field=u.load_asset(DEST+'/T_Manny_Cuff3cmField');assert cuff_field
cuff_field.set_editor_property('srgb',False)
cuff_field.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
assert E.save_loaded_asset(cuff_field,False)
task=u.AssetImportTask();task.filename=str(OUT/'T_Manny_Cuff3cmRollNormal.png')
task.destination_path=DEST;task.destination_name='T_Manny_Cuff3cmRollNormal'
task.automated=True;task.replace_existing=True;task.save=True
A.import_asset_tasks([task])
roll_normal=u.load_asset(DEST+'/T_Manny_Cuff3cmRollNormal');assert roll_normal
roll_normal.set_editor_property('srgb',False)
roll_normal.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
roll_normal.set_editor_property('flip_green_channel',False)
assert E.save_loaded_asset(roll_normal,False)
report={'scope':'Brown leather glove cuff extended 3 cm behind each wrist with a thin rolled hem, with existing skin and sleeves',
        'skin_source':'Locally authored procedural shader; no human scan or new skin texture download',
        'mesh_modified':False,'materials':[]}
for idx in (2,):
    name='M_Manny_RolledCuff3cm_02'
    mat=u.load_asset(DEST+'/'+name)
    if not mat:mat=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    def node(cls,**props):
        n=L.create_material_expression(mat,cls)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,name,output=''):
        assert L.connect_material_expressions(a,output,b,name),(name,output)
    def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    def sample(name,path,kind,uv=None):
        tex=u.load_asset(path);assert tex,path
        n=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name=name,texture=tex,sampler_type=kind)
        if uv:wire(uv,n,'UVs')
        return n
    uv=node(u.MaterialExpressionTextureCoordinate)
    tile=node(u.MaterialExpressionMultiply)
    wire(uv,tile,'A');wire(scalar('LeatherTileRepeat',4.311859426240176),tile,'B')
    color_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR
    normal_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL
    mask_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
    source_normal=sample('NormalMap',SOURCE+f'/T_Manny_0{idx}_N',normal_type)
    glove=sample('LeatherRegions',OLD+'/Textures/T_Manny_LeatherRegions',mask_type) if idx==2 else node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1))
    forearm=sample('ForearmRegions','/Game/Characters/ArmsSkinSleeveCandidate/T_Manny_ForearmRegions',mask_type) if idx==2 else node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1))
    inputs={
        'UV':uv,'RollNormal':sample('RollNormal',DEST+'/T_Manny_Cuff3cmRollNormal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'CuffField':sample('CuffField',DEST+'/T_Manny_Cuff3cmField',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE),'SourceNormal':source_normal,'Glove':glove,'Forearm':forearm,
        'Leather':sample('LeatherBaseColor',OLD+'/Textures/T_Fab_Leather_BaseColor',color_type,tile),
        'Grain':sample('LeatherNormal',OLD+'/Textures/T_Fab_Leather_Normal',normal_type,tile),
        'LeatherRough':sample('LeatherRoughness',OLD+'/Textures/T_Fab_Leather_Roughness',mask_type,tile),
        'Thread':sample('StitchNormal',OLD+'/Textures/T_Manny_StitchNormal',normal_type),
        'SkinTint':node(u.MaterialExpressionVectorParameter,parameter_name='SkinTint',default_value=skin_tint),
        'SleeveTint':node(u.MaterialExpressionVectorParameter,parameter_name='SleeveTint',default_value=u.LinearColor(.02,.024,.027,1)),
        'SkinDetailStrength':scalar('SkinDetailStrength',.012),
        'GloveCuffStart':scalar('GloveCuffStart',0.8899122968),
        'SkinScatterStrength':scalar('SkinScatterStrength',.18),
        'LeatherNormalStrength':scalar('LeatherNormalStrength',.55)}
    code=node(u.MaterialExpressionCustom,code=(OUT/'rolled_cuff.hlsl').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_inputs=[]
    for input_name in list(inputs)+['Cuff']:
        i=u.CustomInput();i.set_editor_property('input_name',input_name);custom_inputs.append(i)
    code.set_editor_property('inputs',custom_inputs)
    extra=[]
    for output_name,kind in [('OutNormal',3),('OutRoughness',1),('OutScatter',1)]:
        item=u.CustomOutput();item.set_editor_property('output_name',output_name)
        item.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(kind)))
        extra.append(item)
    code.set_editor_property('additional_outputs',extra)
    for input_name,n in inputs.items():wire(n,code,input_name,'R' if input_name=='CuffField' else '')
    if idx==2:wire(forearm,code,'Cuff','A')
    else:wire(node(u.MaterialExpressionConstant,r=0),code,'Cuff')
    for output_name,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('OutNormal',u.MaterialProperty.MP_NORMAL),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS)]:
        assert L.connect_material_property(code,output_name,prop),output_name
    assert L.connect_material_property(scalar('GloveSpecular',.35),'',u.MaterialProperty.MP_SPECULAR)
    if idx==2:
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
        mat.set_editor_property('subsurface_profile',profile)
        assert L.connect_material_property(code,'OutScatter',u.MaterialProperty.MP_OPACITY)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.layout_material_expressions(mat);L.recompile_material(mat)
    saved=False
    for attempt in range(10):
        if E.save_loaded_asset(mat,False):
            saved=True
            break
        u.log_warning(f'Glove cuff material occupied by a concurrent runtime capture: attempt {attempt+1}/10')
        time.sleep(1)
    assert saved

    report['materials'].append({'instance':SOURCE+f'/MI_Manny_0{idx}',
        'role':'accepted 3 cm rolled glove cuff',
        'candidate_parent':mat.get_path_name()})
(OUT/'build_report.json').write_text(json.dumps(report,indent=2))
u.log('GLOVE_CUFF3CM_BUILD_PASS')
