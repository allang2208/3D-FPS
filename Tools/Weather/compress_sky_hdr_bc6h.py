"""Build and save the seven PWL sky cubemaps using BC6H, at original resolution.

Run through mcp_call_codex.ps1 when FPSGAME is already open. With the editor
closed, this also supports the PythonScript commandlet. Does not load a map,
start PIE, render, capture performance, or save unrelated packages.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u


ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/PWL_Light_Manager/Textures/HDR/'
NAMES = (
    'T_HDR_Night_00',
    'T_HDR_Sunrise',
    'T_HDR_Sunset',
    'T_HDR_Sunset_02',
    'T_HDR_Sunshine',
    'T_HDR_Sunshine_02',
    'T_HDR_Overcast_High',
)
PROPERTIES = (
    'compression_settings', 'defer_compression',
    'srgb', 'mip_gen_settings', 'max_texture_size', 'lod_bias', 'lod_group',
    'never_stream', 'virtual_texture_streaming', 'lossy_compression_amount',
    'adjust_brightness', 'adjust_brightness_curve', 'adjust_saturation',
)


def settings(texture):
    result = {}
    for name in PROPERTIES:
        value = texture.get_editor_property(name)
        result[name] = value if isinstance(value, (bool, int, float, str)) else str(value)
    return result


def build():
    paths = {BASE + name for name in NAMES}
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = sorted(paths & dirty)
    if conflicts:
        raise RuntimeError('Sky textures have unsaved edits; left untouched: ' + ', '.join(conflicts))

    out = ROOT / 'SourceAssets/HDRSkyBC6H20260924/Runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True, exist_ok=False)
    report_path = out / 'authoring.json'
    report = {
        'status': 'preparing',
        'scope': 'BC6H texture authoring/build/save only; no runtime or visual testing',
        'resolution_policy': 'Preserve existing source, maximum size, LOD and mip settings',
        'assets': [],
    }

    def write_report():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    try:
        # Gather and back up the exact packages before changing any of them.
        textures = []
        for name in NAMES:
            path = BASE + name
            texture = u.load_asset(path)
            if not isinstance(texture, u.TextureCube):
                raise RuntimeError('Expected an existing sky TextureCube: ' + path)
            before = settings(texture)
            if before['srgb']:
                raise RuntimeError('Expected linear HDR sky data: ' + path)
            source = ROOT / 'Content/PWL_Light_Manager/Textures/HDR' / (name + '.uasset')
            backup = out / 'Backup' / source.relative_to(ROOT / 'Content')
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            row = {'asset': path, 'backup': str(backup), 'before': before, 'status': 'prepared'}
            report['assets'].append(row)
            textures.append((texture, row))
        report['status'] = 'building'
        write_report()

        for texture, row in textures:
            row['status'] = 'building'
            write_report()
            # Keep raw source data and the current mip policy. In particular,
            # do not convert HDR to sRGB, downsize, or regenerate its mip chain.
            changes = {}
            for name, value in (
                ('defer_compression', False),
                ('compression_settings', u.TextureCompressionSettings.TC_HDR_COMPRESSED),
            ):
                if texture.get_editor_property(name) != value:
                    changes[name] = value
            if changes:
                texture.set_editor_properties(changes)
                # Finish the encoding before releasing the editor batch lock.
                u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
                if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
                    raise RuntimeError('Cannot save compressed sky texture: ' + row['asset'])
                row['status'] = 'saved'
            else:
                row['status'] = 'already_configured'
            row['after'] = settings(texture)
            write_report()
            u.log('SKY_HDR_BC6H_SAVED ' + row['asset'])

        report['status'] = 'complete'
        write_report()
        u.log('SKY_HDR_BC6H_COMPLETE ' + str(report_path))
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        write_report()
        raise


if __name__ == '__main__':
    build()
