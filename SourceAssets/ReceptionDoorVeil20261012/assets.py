"""Create opaque unlit black/charcoal surfaces and the two cheap door meshes."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/ReceptionDoorVeil20261012'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
OWNER='ReceptionDoorVeil20261012'

def load_owned(path):
    asset=u.load_asset(path) if E.does_asset_exist(path) else None
    if asset and E.get_metadata_tag(asset,'DoorVeil.Owner')!=OWNER:raise RuntimeError('Preserve existing asset '+path)
    return asset

def save(asset):
    E.set_metadata_tag(asset,'DoorVeil.Owner',OWNER)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())

def node(material,kind,**props):
    expr=L.create_material_expression(material,getattr(u,'MaterialExpression'+kind))
    for key,value in props.items():expr.set_editor_property(key,value)
    return expr

def wire(a,b,pin='',out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed '+pin)

def install():
    texture_path=BASE+'/Textures/T_ReceptionDoor_FogNoise'
    tex=load_owned(texture_path)
    if not tex:
        task=u.AssetImportTask();task.filename=str(ROOT/'Authored/T_ReceptionDoor_FogNoise.png')
        task.destination_path,task.destination_name=texture_path.rsplit('/',1);task.automated=True;task.save=False;task.factory=u.TextureFactory()
        A.import_asset_tasks([task]);tex=u.load_asset(texture_path)
        if not tex:raise RuntimeError('Fog texture import failed')
        for key,value in dict(srgb=False,never_stream=False,max_texture_size=256,
            compression_settings=u.TextureCompressionSettings.TC_BC7,lod_group=u.TextureGroup.TEXTUREGROUP_EFFECTS,
            address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP).items():tex.set_editor_property(key,value)
        save(tex)
    saved=[texture_path]
    for name in ('M_ReceptionDoor_Black','M_ReceptionDoor_Fog'):
        path=BASE+'/Materials/'+name
        mat=load_owned(path)
        if not mat:
            mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
            mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
            mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
            mat.set_editor_property('two_sided',True)
            mat.set_editor_property('used_with_instanced_static_meshes',True)
            slab=node(mat,'SubstrateUnlitBSDF')
            L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
            black=node(mat,'Constant3Vector',constant=u.LinearColor(0,0,0,1))
            wire(black,slab,'TransmittanceColor')
            emission=black
            if name.endswith('_Fog'):
                emission=node(mat,'Custom',code=(ROOT/'Fog.hlsl').read_text('utf8'),
                    output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,desc='Opaque charcoal billows: 2 samples, no light, no raymarch')
                inputs=dict(UV=node(mat,'TextureCoordinate'),Clock=node(mat,'Time'),
                    Exposure=node(mat,'EyeAdaptation'),Density=node(mat,'TextureObject',texture=tex))
                pins=[]
                for key in inputs:
                    pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
                emission.set_editor_property('inputs',pins)
                for key,value in inputs.items():wire(value,emission,key)
            wire(emission,slab,'EmissiveColor')
            L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            L.layout_material_expressions(mat)
            errors=L.recompile_material(mat)
            if errors:raise RuntimeError('Material compile failed: '+str(errors))
            save(mat)
        saved.append(path)
    sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    try:
        for item in json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']:
            mesh=load_owned(item['mesh'])
            if not mesh:
                task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path,task.destination_name=item['mesh'].rsplit('/',1)
                task.automated=True;task.save=False;task.factory=u.FbxFactory()
                opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
                opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
                data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
                data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
                data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
                task.options=opts;A.import_asset_tasks([task]);mesh=u.load_asset(item['mesh'])
                if not mesh:raise RuntimeError('Mesh import failed '+item['mesh'])
                mesh.set_material(0,u.load_asset(item['material']))
                settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=False;mesh.set_editor_property('nanite_settings',settings)
                build=sub.get_lod_build_settings(mesh,0);build.distance_field_resolution_scale=0.
                sub.set_lod_build_settings(mesh,0,build)
                save(mesh)
            saved.append(item['mesh'])
    finally:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX '+str(previous))
    return saved
