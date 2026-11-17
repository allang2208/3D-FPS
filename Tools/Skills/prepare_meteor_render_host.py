"""Build a bounded read-only capture snapshot, reusing the compiled author module."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHOR = ROOT / 'SourceAssets/DragonBreath20261013/AuthorHost'
HOST = ROOT / 'SourceAssets/MeteorVisualReview20261114/RenderHost'
HOST.mkdir(parents=True, exist_ok=True)
shutil.copy2(AUTHOR / 'DragonBreathAuthor.uproject', HOST / 'DragonBreathAuthor.uproject')
(HOST / 'Config').mkdir(exist_ok=True)
(HOST / 'Config/DefaultEngine.ini').write_text('''[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
-D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6
[/Script/Engine.RendererSettings]
r.HeterogeneousVolumes=1
r.GenerateMeshDistanceFields=True
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
''', encoding='utf8')
binary = HOST / 'Binaries/Win64'
binary.mkdir(parents=True, exist_ok=True)
for name in ['UnrealEditor-DragonBreathAuthor.dll', 'UnrealEditor.modules']:
    shutil.copy2(AUTHOR / 'Binaries/Win64' / name, binary / name)
pending = ['/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/NS_MeteorPressureV7']
seen, copied, missing = set(), [], []
while pending:
    package = pending.pop()
    if package in seen:
        continue
    seen.add(package)
    if len(seen) > 256:
        raise RuntimeError('Unexpectedly broad meteor dependency graph')
    relative = Path(package.removeprefix('/Game/') + '.uasset')
    source = ROOT / 'Content' / relative
    if not source.is_file():
        missing.append(package)
        continue
    target = HOST / 'Content' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    for suffix in ['.uexp', '.ubulk', '.uptnl']:
        if source.with_suffix(suffix).is_file():
            shutil.copy2(source.with_suffix(suffix), target.with_suffix(suffix))
    copied.append(package)
    data = source.read_bytes()
    pending.extend(m.decode('ascii') for m in re.findall(rb'/Game/[A-Za-z0-9_/-]+', data))
manifest = dict(project=str(HOST / 'DragonBreathAuthor.uproject'), packages=copied,
                unresolved_package_strings=sorted(missing), read_only_snapshot=True)
(HOST / 'snapshot.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
print(json.dumps(dict(project=manifest['project'], copied=len(copied), unresolved=missing), indent=2))
