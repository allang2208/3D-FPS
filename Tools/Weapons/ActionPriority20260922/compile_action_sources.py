"""Compile action-priority sources into isolated outputs while the editor is open."""
from pathlib import Path
import subprocess
import json
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(r'D:\FPS3D\FPSGAME')
OUTPUT = ROOT / 'Tools/Weapons/ActionPriority20260922/Compile'
OUTPUT.mkdir(exist_ok=True)
BUILD = ROOT / 'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME'
TEMPLATE = (BUILD / 'FPSGAMECharacterAmmo.cpp.obj.rsp').read_text(encoding='utf-8-sig')
COMPILER = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe')
SOURCES = [
    'FPSGAMECharacter.cpp', 'FPSGAMECharacterProfile.cpp', 'FPSGAMECharacterActionPriority.cpp',
    'FPSGAMEPlayerController.cpp', 'UI/ColdSteelProfileRuntime.cpp',
    'Weapons/PistolDualWieldComponent.cpp', 'Weapons/PistolDualWieldCombat.cpp',
    'Weapons/RuneSwordComponent.cpp', 'Weapons/RuneOrbBladesComponent.cpp',
    'Skills/FPSFireballComponent.cpp', 'Skills/FPSIceSpikeComponent.cpp',
    'Skills/FPSIceSpikeVolley.cpp', 'Skills/FPSLightningComponent.cpp',
    'Skills/FPSHolyLightComponent.cpp', 'Skills/FPSFireMagicComponent.cpp',
    'Skills/ColdSteelFireballModel.cpp', 'Skills/FPSQuickCombatComponent.cpp',
]
results = []
for source in SOURCES:
    name = Path(source).name
    if len(sys.argv)>1 and name not in sys.argv[1:]:
        continue
    lines = TEMPLATE.splitlines()
    lines[0] = '"' + (ROOT / 'Source/FPSGAME' / source).as_posix() + '"'
    for index, line in enumerate(lines):
        if line.startswith('/Fo'):
            lines[index] = '/Fo"' + (OUTPUT / (name + '.obj')).as_posix() + '"'
        elif line.startswith('/experimental:log'):
            lines[index] = '/experimental:log "' + (OUTPUT / (name + '.sarif')).as_posix() + '"'
        elif line.startswith('/sourceDependencies'):
            lines[index] = '/sourceDependencies "' + (OUTPUT / (name + '.dep.json')).as_posix() + '"'
    response = OUTPUT / (name + '.rsp')
    response.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    result = subprocess.run([str(COMPILER), '@' + str(response)],
        cwd=r'E:\Program Files (x86)\UE_5.8\Engine\Source',
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUTPUT / (name + '.log')).write_bytes(result.stdout)
    results.append({'source': source, 'exit_code': result.returncode})
    print(name, 'exit', result.returncode, flush=True)
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace'), flush=True)
(OUTPUT / 'result.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
raise SystemExit(any(result['exit_code'] for result in results))
