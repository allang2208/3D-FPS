"""Import and save V9 assets without changing old/shared assets or launching PIE."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
DEST='/Game/Weapons/AzureDragon20261004/CoherentV9'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
receipt=dict(complete=False,revision=9,saved_assets=[],runtime_tested=False,rendered=False)


def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')


def owned(path):
    asset=u.load_asset(path)
    dirty=any(str(p.get_name())==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty and (not asset or E.get_metadata_tag(asset,'AzureDragonPendingRevision')!='9'):
        raise RuntimeError('Preserve unsaved asset '+path)
    if asset and E.get_metadata_tag(asset,'AzureDragonCoherentRevision')!='9':
        raise RuntimeError('Preserve unowned asset '+path)
    return asset


def pending(asset):
    E.set_metadata_tag(asset,'AzureDragonCoherentRevision','9')
    E.set_metadata_tag(asset,'AzureDragonPendingRevision','9')


def save(asset):
    pending(asset)
    E.set_metadata_tag(asset,'AzureDragonPendingRevision','')
    E.set_metadata_tag(asset,'SourceAuthoring','AzureDragon20261004/CoherentV9')
    if not E.save_loaded_asset(asset,False):
        E.set_metadata_tag(asset,'AzureDragonPendingRevision','9')
        raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


def imported(filename,folder,name,options):
    owned(DEST+'/'+folder+'/'+name)
    task=u.AssetImportTask()
    for key,value in dict(filename=str(filename),destination_path=DEST+'/'+folder,destination_name=name,
                          automated=True,replace_existing=True,save=False,options=options).items():
        task.set_editor_property(key,value)
    A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+folder+'/'+name)
    if not asset:
        raise RuntimeError('Import failed '+name)
    pending(asset)
    return asset


if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Stop the current PIE before importing/saving V9; editor preserved.')
record()
materials={}
for kind in ('Column','Crest','Helix','Flame'):
    name='M_AzureDragonEnergy'+kind+'V9'
    mat=owned(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    pending(mat)
    for expression in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat,expression)
    for key,value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT,shading_model=u.MaterialShadingModel.MSM_UNLIT,
                          two_sided=False,disable_depth_test=True,enable_responsive_aa=True,
                          translucency_pass=u.MaterialTranslucencyPass.MTP_AFTER_DOF).items():
        mat.set_editor_property(key,value)
    count=0

    def node(cls,**props):
        global count
        n=L.create_material_expression(mat,cls,-1600+(count%6)*240,(count//6)*250)
        count+=1
        for key,value in props.items():
            n.set_editor_property(key,value)
        return n

    def wire(source,target,pin=0):
        if isinstance(pin,int):
            pin=str(L.get_material_expression_input_names(target)[pin])
        if not L.connect_material_expressions(source,'',target,pin):
            raise RuntimeError('Cannot connect '+str(pin))

    def custom(code,inputs,output):
        n=node(u.MaterialExpressionCustom,code=code,output_type=output)
        pins=[]
        for key in inputs:
            p=u.CustomInput()
            p.set_editor_property('input_name',key)
            pins.append(p)
        n.set_editor_property('inputs',pins)
        for key,expr in inputs.items():
            wire(expr,n,key)
        return n

    inputs={'UV':node(u.MaterialExpressionTextureCoordinate),
            'Normal':node(u.MaterialExpressionPixelNormalWS),'View':node(u.MaterialExpressionCameraVectorWS)}
    for key,value in [('Fill',0.),('Age',0.),('Reveal',1.),('Pulse',0.),('Burst',0.)]:
        inputs[key]=node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value)
    if kind=='Flame':
        inputs['Attr']=node(u.MaterialExpressionVertexColor)
    rgba=custom((ROOT/('Energy'+kind+'.hlsl')).read_text(encoding='utf-8'),inputs,u.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(rgba,rgb)
    wire(rgba,alpha)
    exposure=node(u.MaterialExpressionEyeAdaptationInverse)
    wire(rgb,exposure,0)
    wire(node(u.MaterialExpressionConstant,r=1.),exposure,1)
    L.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
    if kind=='Flame':
        world=node(u.MaterialExpressionWorldPosition)
        local=node(u.MaterialExpressionTransformPosition,
                   transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                   transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(world,local)
        delta=custom((ROOT/'FlameMotion.hlsl').read_text(encoding='utf-8'),
                     {'LocalPosition':local,'Attr':inputs['Attr'],'Age':inputs['Age'],'Fill':inputs['Fill'],'Burst':inputs['Burst']},
                     u.CustomMaterialOutputType.CMOT_FLOAT3)
        offset=node(u.MaterialExpressionTransform,
                    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        wire(delta,offset)
        L.connect_material_property(offset,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    errors=L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed '+str(errors))
    save(mat)
    materials[kind]=mat

flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    options=u.FbxImportUI()
    for key,value in dict(import_mesh=True,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH,
                          automated_import_should_detect_type=False,import_materials=False,import_textures=False).items():
        options.set_editor_property(key,value)
    data=options.get_editor_property('static_mesh_import_data')
    for key,value in dict(combine_meshes=True,auto_generate_collision=False,import_uniform_scale=1.,
                          convert_scene=True,convert_scene_unit=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,
                          normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
        data.set_editor_property(key,value)
    for entry in json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8')):
        mesh=imported(entry['fbx'],'Meshes',entry['name'],options)
        mesh.set_material(0,materials[entry['kind']])
        save(mesh)

    rig=json.loads((ROOT/'Export/rig.json').read_text(encoding='utf-8'))
    owned(DEST+'/Meshes/SK_AzureDragonClaw_RakeV9_Skeleton')
    options=u.FbxImportUI()
    for key,value in dict(import_mesh=True,import_as_skeletal=True,import_animations=False,
                          mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH,automated_import_should_detect_type=False,
                          create_physics_asset=False,import_materials=False,import_textures=False).items():
        options.set_editor_property(key,value)
    data=options.get_editor_property('skeletal_mesh_import_data')
    for key,value in dict(convert_scene=True,convert_scene_unit=False,import_uniform_scale=1.,
                          normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                          use_t0_as_ref_pose=False,update_skeleton_reference_pose=False).items():
        data.set_editor_property(key,value)
    mesh=imported(rig['mesh'],'Meshes','SK_AzureDragonClaw_RakeV9',options)
    material=u.load_asset('/Game/Weapons/AzureDragon20261004/Materials/M_AzureDragonClaw')
    if not material:
        raise RuntimeError('Shared claw material missing; do not reset VisibilityV5.')
    slots=mesh.get_editor_property('materials')
    for slot in slots:
        slot.material_interface=material
    mesh.set_editor_property('materials',slots)
    E.set_metadata_tag(mesh,'SourceListing','https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a')
    skeleton=mesh.get_editor_property('skeleton')
    save(mesh)
    save(skeleton)
    options=u.FbxImportUI()
    for key,value in dict(import_mesh=False,import_as_skeletal=True,import_animations=True,
                          mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION,original_import_type=u.FBXImportType.FBXIT_ANIMATION,
                          automated_import_should_detect_type=False,skeleton=skeleton,import_materials=False,import_textures=False).items():
        options.set_editor_property(key,value)
    data=options.get_editor_property('anim_sequence_import_data')
    for key,value in dict(convert_scene=True,convert_scene_unit=False,
                          animation_length=u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,import_bone_tracks=True,
                          remove_redundant_keys=False,use_default_sample_rate=False,custom_sample_rate=60).items():
        data.set_editor_property(key,value)
    animation=imported(rig['animation'],'Animations','A_AzureDragonClaw_RakeV9',options)
    animation.set_editor_property('enable_root_motion',False)
    save(animation)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt['complete']=True
record()
print('AZURE_DRAGON_COHERENT_V9_SAVED assets='+str(len(receipt['saved_assets']))+' runtime_tested=false rendered=false')
