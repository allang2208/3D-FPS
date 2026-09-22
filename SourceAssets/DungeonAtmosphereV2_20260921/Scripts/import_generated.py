"""Import Blender-refined local generator assets, preserving physical channels."""
from pathlib import Path
import json
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
CFG=json.loads((ROOT/'assets.json').read_text(encoding='utf-8'))
OUT='/Game/Dungeons/AtmosphereV2/Generated'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
record={}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())

for prop in CFG['props']:
    source=ROOT/'Generated'/prop['id']/'Game/asset-manifest.json'
    if not source.exists():
        print('WAITING_REFINED',prop['id']);continue
    data=json.loads(source.read_text(encoding='utf-8'));folder=OUT+'/'+prop['id'];materials={}
    for matname,channels in data['materials'].items():
        path=folder+'/Materials/'+matname;m=u.load_asset(path)
        if not m:
            m=A.create_asset(matname,folder+'/Materials',u.Material,u.MaterialFactoryNew())
            for channel,info in channels.items():
                filename=Path(info['filename']);texpath=folder+'/Textures/'+filename.stem;t=u.load_asset(texpath)
                if not t:
                    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder+'/Textures';task.destination_name=filename.stem
                    task.automated=True;task.save=False;task.replace_existing=False;A.import_asset_tasks([task]);t=u.load_asset(texpath)
                    if not t:raise RuntimeError('Texture import failed '+str(filename))
                    t.srgb=channel=='BaseColor'
                    if channel=='Normal':
                        t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.flip_green_channel=True
                    elif channel!='BaseColor':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
                    save(t)
                sampler=L.create_material_expression(m,u.MaterialExpressionTextureSample);sampler.texture=t
                sampler.sampler_type=(u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else
                    u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
                pin={'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Roughness':u.MaterialProperty.MP_ROUGHNESS,'Metallic':u.MaterialProperty.MP_METALLIC,'Normal':u.MaterialProperty.MP_NORMAL}[channel]
                if not L.connect_material_property(sampler,info['channel'],pin):raise RuntimeError('PBR channel not connected '+channel)
            L.recompile_material(m);save(m)
        materials[matname]=m
    path=folder+'/'+data['name'];mesh=u.load_asset(path)
    if not mesh:
        task=u.AssetImportTask();task.filename=data['fbx'];task.destination_path=folder;task.destination_name=data['name']
        task.automated=True;task.replace_existing=False;task.save=False
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
        options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        imp=options.static_mesh_import_data;imp.combine_meshes=True;imp.convert_scene=True;imp.convert_scene_unit=True
        imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Refined mesh import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.get_editor_property('material_slot_name'))
        if name not in materials:raise RuntimeError('Generated material slot changed '+name)
        mesh.set_material(i,materials[name])
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);b=mesh.get_bounds()
    record[prop['id']]={'path':path,'origin':list(b.origin.to_tuple()),'extent':list(b.box_extent.to_tuple()),'source':data['source']}
    print('LOCAL_GENERATED_IMPORTED',prop['id'])
(ROOT/'Receipts/generated-import.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
