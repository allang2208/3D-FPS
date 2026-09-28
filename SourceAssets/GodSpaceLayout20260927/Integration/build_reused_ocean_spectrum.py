"""Derive backdrop waves from the SAME Clearwater spectrum used by the fountain.

Preserves source directions, phase, dispersion and analytic slopes. Spatial and
temporal scale change for a view 1.5 km above water; no CPU water simulation.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
SOURCE=PROJECT/'SourceAssets/ClearwaterWater20260926/waves.json'
SPACE_SCALE=100.
HEIGHT_GAIN=2.2
TIME_GAIN=1.35
CELL_M=8000/256

def build():
    data=json.loads(SOURCE.read_text(encoding='utf8'))
    indexed=sorted(enumerate(data['waves']),key=lambda item:item[1]['amplitude'],reverse=True)[:16]
    lines=['// Generated from the active fountain native-water spectrum. Do not hand-edit.',
           '// Same phase / sincos / slope evaluation as ClearwaterNative WaveField.hlsl.',
           'float2 p=(P.xy-float2(-2400,-1300))*.01;',
           'float height=0; float2 slope=0; float crest=0;']
    bound=0.
    amplitude_sum=sum(w['amplitude'] for _,w in indexed)
    for index,w in indexed:
        wavelength=w['wavelength']*SPACE_SCALE
        kx=w['k']*w['dir'][0]/SPACE_SCALE
        ky=w['k']*w['dir'][1]/SPACE_SCALE
        amplitude=w['amplitude']*SPACE_SCALE*HEIGHT_GAIN
        # The fountain's native evaluator similarly removes unresolved short
        # waves from geometry while retaining their analytic shading normal.
        t=max(0.,min(1.,(wavelength-4*CELL_M)/(4*CELL_M)))
        geometry=t*t*(3-2*t)
        bound+=amplitude*geometry
        omega=w['omega']/math.sqrt(SPACE_SCALE)*TIME_GAIN
        lines.extend([
            '{ // original spectrum term '+str(index),
            f' float ph=dot(p,float2({kx:.12f},{ky:.12f}))+({w["phase"]:.12f})-Clock*{omega:.12f};',
            ' float s,c; sincos(ph,s,c);',
            f' height+={amplitude*geometry*100:.12f}*s;',
            f' slope+=float2({amplitude*kx:.12f},{amplitude*ky:.12f})*c;',
            f' crest+=smoothstep(.68,1,s)*{w["amplitude"]/amplitude_sum:.12f};',
            '}'])
    lines.append('return float4(height,slope,crest);')
    (ROOT/'OceanSwell.hlsl').write_text('\n'.join(lines)+'\n',encoding='utf8')
    report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'fountain_evaluator':'Tools/Fluids/native_water_surface.py; SourceAssets/ClearwaterNative20260926/WaveField.hlsl',
            'source_terms':len(data['waves']),'selected_terms':[i for i,_ in indexed],
            'space_scale':SPACE_SCALE,'height_gain':HEIGHT_GAIN,'time_gain':TIME_GAIN,
            'wavelength_m':[min(w['wavelength'] for _,w in indexed)*SPACE_SCALE,max(w['wavelength'] for _,w in indexed)*SPACE_SCALE],
            'period_s':[2*math.pi/(w['omega']/math.sqrt(SPACE_SCALE)*TIME_GAIN) for _,w in indexed],
            'grid_cell_m':CELL_M,'absolute_displacement_bound_cm':bound*100,
            'runtime_tested':False}
    (ROOT/'Receipts/ocean-reused-spectrum.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report

if __name__=='__main__':build()
