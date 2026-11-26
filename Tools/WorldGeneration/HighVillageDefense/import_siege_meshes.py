"""Import the village siege art into its own /Game package folder."""
import json
import os
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
import import_kit as kit

run=Path(os.environ['VILLAGE_SIEGE_RUN'])
dest=kit.PACK+'/SiegeEngines'
kit.E.make_directory(dest)
src=run/'Authored'
mat_name='M_Ballista'
mat=kit.existing(dest+'/'+mat_name) or kit.A.create_asset(mat_name,dest,u.Material,u.MaterialFactoryNew())
kit.L.delete_all_material_expressions(mat)
for kind in ('Base','Normal','ORM'):
    name='T_Ballista'+kind
    job=u.AssetImportTask()
    job.filename=str(src/(name+'.png'))
    job.destination_name=name
    job.destination_path=dest
    job.replace_existing=True
    job.automated=True
    job.save=False
    kit.A.import_asset_tasks([job])
    tex=kit.require(dest+'/'+name)
    tex.srgb=kind=='Base'
    tex.compression_settings={'Base':u.TextureCompressionSettings.TC_DEFAULT,'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'ORM':u.TextureCompressionSettings.TC_MASKS}[kind]
    kit.save(tex)
    node=kit.L.create_material_expression(mat,u.MaterialExpressionTextureSample)
    node.texture=tex
    node.sampler_type={'Base':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
    props={'Base':[('',u.MaterialProperty.MP_BASE_COLOR)],'Normal':[('',u.MaterialProperty.MP_NORMAL)],
        'ORM':[('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]}
    for channel,prop in props[kind]:
        if not kit.L.connect_material_property(node,channel,prop):raise RuntimeError(name)
kit.L.recompile_material(mat)
kit.save(mat)
materials={'Ballista':mat,
    'Oak':kit.require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
    'Leather':kit.require('/Game/Building/GunWorkbenchMedieval20260928/Materials/M_GWLeather'),
    'Iron':kit.require('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'),
    'Stone':kit.require('/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFooting')}
receipt={'saved':{}}
for metadata in sorted(src.glob('SM_*.json')):
    name=metadata.stem
    spec=json.loads(metadata.read_text(encoding='utf8'))
    opts=u.FbxImportUI()
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_as_skeletal=False;opts.import_mesh=True
    opts.import_materials=False;opts.import_textures=False
    settings=opts.static_mesh_import_data
    settings.convert_scene=False
    settings.convert_scene_unit=False
    settings.combine_meshes=True
    settings.auto_generate_collision=False
    settings.generate_lightmap_u_vs=False
    settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask()
    task.filename=str(src/(name+'.fbx'))
    task.destination_name=name;task.destination_path=dest
    task.options=opts;task.factory=u.FbxFactory()
    task.automated=True;task.replace_existing=True;task.save=False
    kit.A.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('FBX import failed '+name)
    mesh=kit.require(dest+'/'+name)
    for index,slot in enumerate(mesh.static_materials):
        mesh.set_material(index,materials[str(slot.material_slot_name)])
    body=mesh.get_editor_property('body_setup')
    ag=body.get_editor_property('agg_geom')
    boxes=[]
    for box in spec['boxes']:
        elem=u.KBoxElem()
        elem.set_editor_property('center',u.Vector(*box['center']))
        for key,length in zip(('x','y','z'),box['size']):elem.set_editor_property(key,length)
        boxes.append(elem)
    ag.set_editor_property('box_elems',boxes)
    body.set_editor_property('agg_geom',ag)
    kit.save(mesh)
    receipt['saved'][name]={'path':mesh.get_path_name(),'triangles':spec['faces'],'materials':spec['materials'],'collision_boxes':len(boxes)}
    u.log('SIEGE_SAVED '+name)
(Path(os.environ['VILLAGE_SIEGE_STAGE'])/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
