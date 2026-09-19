"""Bind the authored engine instance textures, not the master placeholders.

The engine master intentionally contains black layout/profile defaults and a
default volume texture. Its working cloud textures live on the engine instance.
Only the project shared instance is saved; hills inherits these bindings.
"""
from datetime import datetime
from pathlib import Path
import json
import shutil
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
SOURCE = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst'
TARGET = '/Game/Weather/Materials/MI_FPSLayeredClouds'
TEXTURE_PARAMETERS = (
    'Layout_CloudGlobalPattern',
    'Noise_Texture3D',
    'Layout_CloudHeightProfile',
    'Layout_GlobalCloudMask',
)


def bind_cloud_textures(instance):
    library = u.MaterialEditingLibrary
    source = u.load_asset(SOURCE)
    if source is None:
        raise RuntimeError('Missing authored engine cloud instance: ' + SOURCE)
    textures = {
        name: library.get_material_instance_texture_parameter_value(source, name)
        for name in TEXTURE_PARAMETERS
    }
    if any(texture is None for texture in textures.values()):
        raise RuntimeError('Authored cloud instance is missing a required texture')
    for name, texture in textures.items():
        # UE may return false when adding the first override even though it
        # writes the value; use the resulting binding as the authoring result.
        library.set_material_instance_texture_parameter_value(instance, name, texture)
        if library.get_material_instance_texture_parameter_value(instance, name) != texture:
            raise RuntimeError('Could not bind cloud texture: ' + name)
    return {name: texture.get_path_name() for name, texture in textures.items()}


def build():
    instance = u.load_asset(TARGET)
    if instance is None:
        raise RuntimeError('Missing project cloud instance: ' + TARGET)
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if TARGET in dirty:
        raise RuntimeError('Shared cloud instance has unsaved edits')
    out = ROOT / 'Saved/CloudTextureFix20260919'
    backup = out / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=True)
    source_file = ROOT / 'Content/Weather/Materials/MI_FPSLayeredClouds.uasset'
    shutil.copy2(source_file, backup / source_file.name)
    textures = bind_cloud_textures(instance)
    u.MaterialEditingLibrary.update_material_instance(instance)
    u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
    if not u.EditorLoadingAndSavingUtils.save_packages([instance.get_outermost()], False):
        raise RuntimeError('Could not save cloud texture bindings')
    (out / 'authoring.json').write_text(json.dumps({
        'saved': TARGET, 'source_instance': SOURCE, 'textures': textures,
        'backup': str(backup), 'scope': 'Shared material instance only; no map save',
    }, indent=2), encoding='utf-8')
    u.log('FPS_CLOUD_TEXTURES_BOUND ' + TARGET)


if __name__ == '__main__':
    build()
