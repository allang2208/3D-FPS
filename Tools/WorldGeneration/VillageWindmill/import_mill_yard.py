"""Import only the mill-yard kit. Hard references on the saved site carry it into the village."""
import json
import os
from pathlib import Path

import unreal as ue

from import_windmill_assets import ASSETS, MAT, TOOLS, import_fbx, load, save, setup_geometry

YARD = '/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard'
WORK = Path(os.environ['WINDMILL_ART'])
EXCHANGE = WORK / 'Exchange'
CHANNELS = ('BaseColor', 'Normal', 'ORM')


def import_texture(role, channel):
    name = 'T_Mill' + role + '_' + channel
    task = ue.AssetImportTask()
    task.filename = str(EXCHANGE / role / (channel + '.png'))
    task.destination_path = YARD + '/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    tex = load(task.destination_path + '/' + name)
    tex.srgb = channel == 'BaseColor'
    if channel == 'Normal':
        tex.compression_settings = ue.TextureCompressionSettings.TC_NORMALMAP
    elif channel == 'ORM':
        tex.compression_settings = ue.TextureCompressionSettings.TC_MASKS
    save(tex)
    return tex


def make_master(defaults):
    name = 'M_MillYardScan'
    path = YARD + '/Materials/' + name
    if ASSETS.does_asset_exist(path):
        return load(path)
    mat = TOOLS.create_asset(name, YARD+'/Materials', ue.Material, ue.MaterialFactoryNew())
    MAT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    MAT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_NANITE, True)
    for channel, sampler, outputs in (
        ('BaseColor', ue.MaterialSamplerType.SAMPLERTYPE_COLOR, [('RGB','MP_BASE_COLOR')]),
        ('Normal', ue.MaterialSamplerType.SAMPLERTYPE_NORMAL, [('RGB','MP_NORMAL')]),
        ('ORM', ue.MaterialSamplerType.SAMPLERTYPE_MASKS,
         [('R','MP_AMBIENT_OCCLUSION'),('G','MP_ROUGHNESS'),('B','MP_METALLIC')])):
        node = MAT.create_material_expression(mat, ue.MaterialExpressionTextureSampleParameter2D)
        node.texture = defaults[channel]
        node.set_editor_property('parameter_name',channel)
        node.set_editor_property('sampler_type',sampler)
        for output, prop in outputs:
            if not MAT.connect_material_property(node, output, getattr(ue.MaterialProperty, prop)):
                raise RuntimeError('Cannot bind '+prop)
    MAT.layout_material_expressions(mat)
    MAT.recompile_material(mat)
    save(mat)
    return mat


def author_yard_assets():
    for folder in ('Materials','Meshes','Textures'):
        ASSETS.make_directory(YARD+'/'+folder)
    sources = json.loads((EXCHANGE/'scans.json').read_text(encoding='utf-8'))
    maps = {r['role']: {c: import_texture(r['role'],c) for c in CHANNELS} for r in sources}
    earth = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
    maps['Earth'] = {c:load(earth+suffix) for c,suffix in zip(CHANNELS, ('B','N','ORM'))}
    master = make_master(maps['Hay'])
    finishes = '/Game/WorldGeneration/TemperateHills/VillageWindmill/Materials/'
    materials = {'Rope': load(finishes+'MI_Prop_Rope_All_Windmill'),
                 'Iron': load(finishes+'M_CarpenterIron_Windmill')}
    for role, channels in maps.items():
        name = 'MI_Mill'+role
        path = YARD+'/Materials/'+name
        mat = (load(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(
            name,YARD+'/Materials',ue.MaterialInstanceConstant,ue.MaterialInstanceConstantFactoryNew()))
        MAT.set_material_instance_parent(mat,master)
        for channel, tex in channels.items():
            MAT.set_material_instance_texture_parameter_value(mat,channel,tex)
        MAT.update_material_instance(mat)
        save(mat)
        materials[role] = mat
    meshes = {}
    for src in sorted(EXCHANGE.glob('SM_Mill*.fbx')):
        mesh = import_fbx(src,YARD+'/Meshes')
        slots = {}
        for i, slot in enumerate(mesh.static_materials):
            role = str(slot.get_editor_property('imported_material_slot_name'))
            mesh.set_material(i, materials[role])
            slots[role] = materials[role].get_path_name()
        triangles = mesh.get_num_triangles(0)
        solid = src.stem in ('SM_MillHayA','SM_MillHayB','SM_MillBarrow','SM_MillEarthShoulder')
        nanite = setup_geometry(mesh,solid,triangles)
        save(mesh)
        box = mesh.get_bounding_box()
        meshes[src.stem] = dict(asset=mesh.get_path_name(), slots=slots, triangles=triangles,
            nanite=nanite, bounds_cm=[[p.x,p.y,p.z] for p in (box.min,box.max)])
    (WORK/'yard-assets.json').write_text(json.dumps(dict(meshes=meshes,scans=sources),indent=2),encoding='utf-8')
