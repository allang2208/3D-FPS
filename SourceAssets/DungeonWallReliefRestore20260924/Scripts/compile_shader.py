"""Compile the exact custom-node body with SDK DXC; no UE/game/render launch."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Receipts'
OUT.mkdir(parents=True, exist_ok=True)
source = (ROOT / 'Scripts/wall_surface.ush').read_text(encoding='utf-8')
textures = ['HeightTex', 'ReliefNormal', 'ReliefSurface', 'ScanColor', 'ScanNormal', 'ScanORM']
scalars = ['DistanceCm', 'DepthCm', 'FadeStart', 'FadeEnd', 'Steps', 'RefineSteps',
           'TileSize', 'NormalStrength', 'ReliefStrength', 'Brightness', 'RoughnessScale', 'Variation']
stub = '#define Texture2DSampleGrad(T,S,U,X,Y) T.SampleGrad(S,U,X,Y)\n'
stub += '\n'.join('Texture2D<float4> '+t+'; SamplerState '+t+'Sampler;' for t in textures)
stub += '\ncbuffer MaterialInputs { float3 View; float3 Position; float3 Tint; '
stub += ' '.join('float '+name+';' for name in scalars) + ' };\n'
stub += 'float4 WallSurface(float2 UV, out float3 NormalTangent, out float AO) {\n' + source + '\n}\n'
stub += 'float4 main(float4 p:SV_Position,float2 uv:TEXCOORD0):SV_Target0 { float3 n;float ao;'
stub += 'float4 s=WallSurface(uv,n,ao);return float4(s.rgb*.7+n*.1,s.a*ao);}\n'
path = OUT / 'wall_surface.sm6.hlsl'
path.write_text(stub, encoding='utf-8')
dxc = Path('C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64/dxc.exe')
result = subprocess.run([str(dxc), '-T', 'ps_6_0', '-E', 'main', '-Fo', str(OUT/'wall_surface.dxil'),
                         str(path)], capture_output=True, text=True)
report = dict(compiler=str(dxc), target='ps_6_0', exit_code=result.returncode,
              source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              output=result.stdout+result.stderr,
              scope='Exact Custom HLSL body; not an Unreal material permutation or runtime visual test')
(OUT/'shader-compile.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
raise SystemExit(result.returncode)
