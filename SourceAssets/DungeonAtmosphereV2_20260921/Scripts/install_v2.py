"""One project-bridge batch for the final owned imports and map write."""
from pathlib import Path
import json
import runpy
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
ROOMS=ROOT.parent/'DungeonRoomInteriors20260921'
for prop in json.loads((ROOT/'assets.json').read_text())['props']:
    source=ROOT/'Generated'/prop['id']/'Game/asset-manifest.json'
    if not source.exists():raise RuntimeError('Required asset still being made: '+prop['id'])
if (ROOMS/'Authored/room-manifest.json').exists():
    for prop in json.loads((ROOMS/'assets.json').read_text())['props']:
        if not (ROOMS/'Generated'/prop['id']/'Game/asset-manifest.json').exists():
            raise RuntimeError('Required room asset still being made: '+prop['id'])
for name in ('import_generated.py','create_grime.py','assemble_v2.py'):
    print('V2_INSTALL_STAGE '+name)
    runpy.run_path(str(ROOT/'Scripts'/name),run_name='__main__')
if (ROOT/'Authored/TilePolish/geometry-manifest.json').exists():
    print('V2_INSTALL_STAGE import_tile_polish.py')
    runpy.run_path(str(ROOT/'Scripts/import_tile_polish.py'),run_name='__main__')
if (ROOT/'Authored/NaturalPass/geometry-manifest.json').exists():
    print('V2_INSTALL_STAGE import_natural_segment.py')
    runpy.run_path(str(ROOT/'Scripts/import_natural_segment.py'),run_name='__main__')
if (ROOMS/'Authored/room-manifest.json').exists():
    for name in ('import_room_assets.py','import_generated_phase.py','install_rooms.py'):
        print('V2_ROOM_STAGE '+name)
        runpy.run_path(str(ROOMS/'Scripts'/name),run_name='__main__')
EARTHWORK=ROOT.parent/'DungeonRuinEarthwork20260921'
if (EARTHWORK/'Authored/manifest.json').exists():
    for name in ('import_earthwork.py','install_earthwork.py'):
        print('V2_EARTHWORK_STAGE '+name)
        runpy.run_path(str(EARTHWORK/'Scripts'/name),run_name='__main__')
KIT=ROOT.parent/'DungeonWorkbenchKit20260921'
if (KIT/'Config/surroundings.json').exists() and (KIT/'Receipts/blueprints.json').exists():
    print('V2_WORKSHOP_CURRENT_DEFINITION_STAGE')
    runpy.run_path(str(KIT/'Scripts/restore_current_workshop.py'),run_name='__main__')
else:
    # Compatibility for an older checkout that has not built the final workbench kit yet.
    stages=[
        ('DungeonWorkshopDetail20260921',('import_workshop.py','install_workshop.py')),
        ('DungeonWorkshopTools20260921',('import_tools.py','install_tools.py')),
        ('DungeonWorkshopSculpt20260921',('import_components.py','install_components.py')),
        ('DungeonWorkshopSurface20260921',('read_inputs.py','import_finish.py','install_finish.py')),
        ('DungeonWorkshopFabTools20260921',('import_tools.py','install_tools.py')),
        ('DungeonWorkshopBenchPolish20260921',('import_and_install.py',))]
    for folder,scripts in stages:
        stage=ROOT.parent/folder;manifest=stage/'Authored/manifest.json'
        if not manifest.exists():continue
        if folder=='DungeonWorkshopFabTools20260921' and not json.loads(manifest.read_text()).get('textures_ready'):continue
        for name in scripts:
            print('V2_LEGACY_WORKSHOP_STAGE '+folder+'/'+name)
            runpy.run_path(str(stage/'Scripts'/name),run_name='__main__')
