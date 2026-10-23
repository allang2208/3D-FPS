"""Author a new HUD package privately and install only its new package files."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
HOST = P/'AuthorHost'
ENGINE = Path('E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
INPUTS = [Path('Weapons/RuneboundWarhammer20261022/HudMotesV2/M_RuneboundEnergyHud')]
INPUTS += [Path('Weapons/AzureDragon20261004/HudV10/Textures')/('T_AzureDragonHud'+name)
           for name in ('Empty', 'Full', 'Mask', 'Noise', 'Glyphs')]
OUTPUT = Path('Weapons/RuneboundWarhammer20261022/HudSymmetricCapsV3/M_RuneboundEnergyHud')
HOST.mkdir(exist_ok=True)
(HOST/'Config').mkdir(exist_ok=True)
project = HOST/'RuneboundHudAuthor.uproject'
project.write_text(json.dumps({'FileVersion': 3, 'EngineAssociation': '5.8', 'Plugins': [
    {'Name': 'PythonScriptPlugin', 'Enabled': True}, {'Name': 'EditorScriptingUtilities', 'Enabled': True},
]}, indent=2), encoding='utf-8')
(HOST/'Config/DefaultEngine.ini').write_text('''[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
-D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6
''', encoding='utf-8')
for package in INPUTS:
    source = ROOT/'Content'/package
    if not source.with_suffix('.uasset').is_file():
        raise RuntimeError('Missing HUD donor dependency '+str(source))
    destination = HOST/'Content'/package.parent
    destination.mkdir(parents=True, exist_ok=True)
    for file in source.parent.glob(source.name+'.*'):
        shutil.copy2(file, destination/file.name)

log = P/'import-isolated-01.log'
with (P/'import-isolated-stdout-01.log').open('w', encoding='utf-8') as output:
    result = subprocess.run([str(ENGINE), str(project), '-run=pythonscript', '-script='+str(P/'install_assets.py'),
        '-unattended', '-nop4', '-nosplash', '-NoSound', '-NoLiveCoding', '-RenderOffscreen', '-stdout',
        '-FullStdOutLogOutput', '-abslog='+str(log)], stdout=output, stderr=subprocess.STDOUT)
if result.returncode:
    raise RuntimeError('HUD authoring failed: '+str(result.returncode)+'; see '+str(log))
receipt = json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt.get('complete'):
    raise RuntimeError('HUD authoring did not finish saving')
source = HOST/'Content'/OUTPUT
if not source.with_suffix('.uasset').is_file():
    raise RuntimeError('Saved HUD package missing')
destination = ROOT/'Content'/OUTPUT.parent
destination.mkdir(parents=True, exist_ok=True)
installed = []
for file in source.parent.glob(source.name+'.*'):
    target = destination/file.name
    data = file.read_bytes()
    if target.exists():
        if target.read_bytes() != data:
            raise RuntimeError('Preserve existing HUD target '+str(target))
    else:
        with target.open('xb') as output:
            output.write(data)
    installed.append({'file': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest()})
receipt.update(installed_to_main_project=True, installed_files=installed, commandlet_exit_code=result.returncode,
               editor_ui_started=False, main_project_asset_overwrites=False)
(P/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('RUNEBOUND_HUD_MOTES_INSTALLED '+json.dumps(installed))
