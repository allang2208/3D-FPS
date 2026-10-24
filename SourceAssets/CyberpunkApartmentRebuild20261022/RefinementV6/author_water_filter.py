"""Pixel-footprint filtering for the accepted spectrum; shared water is untouched."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent;project=root.parents[2]
waves=json.loads((project/'SourceAssets/ClearwaterWater20260926/waves.json').read_text())['waves']
code=['// Pixel shader only: remove waves smaller than the visible pixel footprint.',
 'float2 p=Position.xy*.01; float2 px=ddx(p), py=ddy(p);',
 'float2 slope=0;']
for w in waves:
 if w['amplitude']<=0:continue
 kx=w['k']*w['dir'][0];ky=w['k']*w['dir'][1]
 code.extend(['{',f' float2 k=float2({kx:.10f},{ky:.10f});',
  ' float footprint=max(abs(dot(k,px)),abs(dot(k,py)));',
  ' float resolved=1.0-smoothstep(.65,2.4,footprint);',
  f' float ph=dot(k,p)+({w["phase"]:.10f})-{w["omega"]:.10f}*Clock;',
  f' slope+=float2({w["amplitude"]*kx:.10f},{w["amplitude"]*ky:.10f})*cos(ph)*resolved;', '}'])
code.append('return float3(0,slope)*WaveHeightScale;')
(root/'BayPixelWave.hlsl').write_text('\n'.join(code)+'\n',encoding='utf8')
print('APARTMENT_V6_PIXEL_WAVE_AUTHORED',len(waves))
