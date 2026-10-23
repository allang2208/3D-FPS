"""Produce new material packages in a private commandlet project, then install new files."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
HOST = P/'AuthorHost'
ENGINE = Path('E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
CONTENT = Path('Weapons/RuneboundWarhammer20261022')
INPUTS = [
    CONTENT/'DestructionManaRuneV1/M_RuneboundDestructionRuneSurface',
    CONTENT/'DestructionManaRuneV1/M_RuneboundDestructionMote',
    CONTENT/'Textures/T_RuneboundWarhammer_BaseColor',
    CONTENT/'Textures/T_RuneboundWarhammer_MetallicRoughness',
    CONTENT/'Textures/T_RuneboundWarhammer_Normal',
    CONTENT/'PassiveV1/T_RuneboundNativeRuneMask',
]
OUTPUTS = [CONTENT/'DestructionRedImpactV2'/name for name in ('M_RuneboundDestructionRuneSurface', 'M_RuneboundDestructionMote')]
HOST.mkdir(exist_ok=True)
(HOST/'Config').mkdir(exist_ok=True)
project = HOST/'RuneboundMaterialAuthor.uproject'
project.write_text(json.dumps({
    'FileVersion': 3, 'EngineAssociation': '5.8',
    'Plugins': [{'Name': 'PythonScriptPlugin', 'Enabled': True}, {'Name': 'EditorScriptingUtilities', 'Enabled': True}],
}, indent=2), encoding='utf-8')
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
        raise RuntimeError('Missing authoring dependency '+str(source))
    destination = HOST/'Content'/package.parent
    destination.mkdir(parents=True, exist_ok=True)
    for sidecar in source.parent.glob(source.name+'.*'):
        shutil.copy2(sidecar, destination/sidecar.name)

log = P/'import-isolated-01.log'
with (P/'import-isolated-stdout-01.log').open('w', encoding='utf-8') as output:
    result = subprocess.run([str(ENGINE), str(project), '-run=pythonscript', '-script='+str(P/'install_assets.py'),
        '-unattended', '-nop4', '-nosplash', '-NoSound', '-NoLiveCoding', '-RenderOffscreen', '-stdout',
        '-FullStdOutLogOutput', '-abslog='+str(log)], stdout=output, stderr=subprocess.STDOUT)
if result.returncode:
    raise RuntimeError('Private material authoring exited '+str(result.returncode)+'; see '+str(log))
receipt = json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt.get('complete'):
    raise RuntimeError('Private material authoring did not finish saving')

# Install only new package files. Never overwrite a package held by another editor.
installed = []
for package in OUTPUTS:
    source = HOST/'Content'/package
    if not source.with_suffix('.uasset').is_file():
        raise RuntimeError('Saved output missing '+str(source))
    destination = ROOT/'Content'/package.parent
    destination.mkdir(parents=True, exist_ok=True)
    for sidecar in source.parent.glob(source.name+'.*'):
        target = destination/sidecar.name
        data = sidecar.read_bytes()
        if target.exists():
            if target.read_bytes() != data:
                raise RuntimeError('Preserve existing target '+str(target))
        else:
            with target.open('xb') as output:
                output.write(data)
        installed.append({'file': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest()})
receipt.update(installed_to_main_project=True, installed_files=installed,
               commandlet_exit_code=result.returncode, import_mode='Private commandlet project; new package files only',
               main_project_asset_overwrites=False)
(P/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('RUNEBOUND_RED_MATERIALS_INSTALLED '+json.dumps(installed))
