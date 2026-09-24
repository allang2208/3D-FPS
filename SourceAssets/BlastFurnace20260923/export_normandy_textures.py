"""Export the UnrealNormandy texture sets to PNG so they can be previewed.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

Writes to ``Saved/BlastFurnace20260923/NormandyPNG`` only; nothing in the
project is touched. ``unreal.TextureExporter`` is not exposed in this build but
``TextureExporterPNG`` is, so that is what is used.
"""
import json
from pathlib import Path

import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923')
PNG = OUT / 'NormandyPNG'
PNG.mkdir(parents=True, exist_ok=True)

# family -> which maps to pull
WANTED = {
    'T_HB_Wall4x4_00A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_HB_Wall4x4_01A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_Mortar_00A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_StoneSurface_00A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_StoneSurface_01A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_StoneSurface_02A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_StoneSurface_03A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_StoneSurface_DetailNormal_00A': ('Normal',),
    'T_MetalRust_00A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_LC_GroundSoilExcavated_00A': ('Albedo', 'Normal', 'RHAOM'),
    'T_SoilSurface_02A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_LC_MossyGravel_00A': ('Albedo', 'Normal', 'RHAOM'),
    'T_LC_BasaltCliff_00A': ('Albedo', 'Normal', 'RHAOM'),
    'T_LC_BasaltCliffCracked_00A': ('Albedo', 'Normal', 'RHAOM'),
    'T_LC_RockBasaltLichen_00A': ('Albedo', 'Normal', 'RHAOM'),
    'T_CliffSurface_02A': ('BaseColor', 'Normal', 'RHAOM'),
    'T_CliffSurface_03A': ('BaseColor', 'Normal', 'RHAOM'),
}

report = {'exported': [], 'missing': [], 'failed': []}
for family, suffixes in WANTED.items():
    for suffix in suffixes:
        asset_path = '/Game/UnrealNormandy/Textures/%s_%s' % (family, suffix)
        texture = u.load_asset(asset_path)
        if texture is None:
            report['missing'].append(asset_path)
            continue
        target = PNG / ('%s_%s.png' % (family, suffix))
        if target.exists() and target.stat().st_size > 0:
            report['exported'].append(str(target))
            continue
        try:
            task = u.AssetExportTask()
            task.set_editor_property('object', texture)
            task.set_editor_property('filename', str(target))
            task.set_editor_property('automated', True)
            task.set_editor_property('prompt', False)
            task.set_editor_property('replace_identical', True)
            task.set_editor_property('exporter', u.TextureExporterPNG())
            if u.Exporter.run_asset_export_task(task) and target.exists():
                report['exported'].append(str(target))
            else:
                report['failed'].append(asset_path)
        except Exception as error:  # noqa: BLE001 - report, do not abort the batch
            report['failed'].append('%s: %s' % (asset_path, error))

(OUT / 'normandy_export.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str),
                                          encoding='utf-8')
print('NORMANDY_EXPORT ' + json.dumps({
    'exported': len(report['exported']), 'missing': report['missing'][:4],
    'failed': report['failed'][:4]}, ensure_ascii=False), flush=True)
