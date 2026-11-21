"""Use the village's oak fascia and iron hardware with the apothecary's painted atlas."""
from pathlib import Path

import unreal as u

from author_shop import pose


DEST = '/Game/WorldGeneration/TemperateHills/VillageHerbalist/Sign'
MAT = 'M_HerbalistSign'
FASCIA = '/Game/WorldGeneration/VillageTavern/Sign/SM_TavernSign'


def ensure_sign_material():
    lib = u.EditorAssetLibrary
    if lib.does_asset_exist(DEST+'/'+MAT):
        return
    folder = Path(__file__).resolve().parents[3]/'SourceAssets/HillsVillageHerbalist/Sign'
    api = u.AssetToolsHelpers.get_asset_tools()
    editing = u.MaterialEditingLibrary
    textures = {}
    for channel in ('Color','Normal','ORM'):
        name = 'T_HerbalistSign_'+channel
        task = u.AssetImportTask()
        task.filename = str(folder/(name+'.png'))
        task.destination_path,task.destination_name = DEST,name
        task.automated,task.replace_existing = True,True
        api.import_asset_tasks([task])
        tex = lib.load_asset(DEST+'/'+name)
        if not tex:
            raise RuntimeError('Unable to import '+name)
        tex.srgb = channel=='Color'
        if channel=='Normal':
            tex.compression_settings = u.TextureCompressionSettings.TC_NORMALMAP
        elif channel=='ORM':
            tex.compression_settings = u.TextureCompressionSettings.TC_MASKS
        if not lib.save_loaded_asset(tex,False):
            raise RuntimeError('Unable to save '+name)
        textures[channel] = tex

    material = api.create_asset(MAT,DEST,u.Material,u.MaterialFactoryNew())
    material.set_editor_property('used_with_instanced_static_meshes',True)
    for row,(channel,sampler,outputs) in enumerate((
        ('Color','COLOR',[('RGB','BASE_COLOR')]),
        ('Normal','NORMAL',[('RGB','NORMAL')]),
        ('ORM','MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')]),
    )):
        sample = editing.create_material_expression(material,u.MaterialExpressionTextureSample,-400,row*240)
        sample.texture = textures[channel]
        sample.sampler_type = getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler)
        for pin,prop in outputs:
            if not editing.connect_material_property(sample,pin,getattr(u.MaterialProperty,'MP_'+prop)):
                raise RuntimeError('Unable to connect '+prop)
    editing.recompile_material(material)
    if not lib.save_loaded_asset(material,False):
        raise RuntimeError('Unable to save '+MAT)


def add_sign(house,add):
    ensure_sign_material()
    # Both surviving mounting grounds fit in the original masonry over the street door.
    anchor = pose(house,-178,-370,300,-90,1.12)
    materials = (DEST+'/'+MAT,)
    add('Repaired',FASCIA,anchor,materials,profile='NoCollision')
    add('Ruined',FASCIA+'Ruined',anchor,materials,profile='NoCollision')
