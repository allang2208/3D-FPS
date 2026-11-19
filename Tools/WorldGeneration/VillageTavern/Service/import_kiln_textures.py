from pathlib import Path

import unreal as u


def import_kiln_textures():
    source = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/Service'
    folder = '/Game/WorldGeneration/VillageTavern/Service'
    tools = u.AssetToolsHelpers.get_asset_tools()
    textures = {}
    for suffix in ('Albedo', 'Masks', 'Normal'):
        name = 'T_Kiln'+suffix
        task = u.AssetImportTask()
        task.filename = str(source/(name+'.png'))
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        tools.import_asset_tasks([task])
        if not task.get_objects():
            raise RuntimeError('Could not import '+name)
        texture = u.load_asset(folder+'/'+name)
        texture.set_editor_property('srgb', suffix == 'Albedo')
        compression = {'Albedo': 'TC_DEFAULT', 'Masks': 'TC_MASKS', 'Normal': 'TC_NORMALMAP'}
        texture.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, compression[suffix]))
        if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
            raise RuntimeError('Unable to save '+name)
        textures[suffix] = texture
    return textures


if __name__ == '__main__':
    import_kiln_textures()
    u.log('TAVERN_KILN_SURFACES_SAVED')
