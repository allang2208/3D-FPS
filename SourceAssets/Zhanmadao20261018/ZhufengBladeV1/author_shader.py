"""Map all existing rune modes onto Zhufeng's authored central face."""
import json,runpy
import numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
layout=json.loads((P/'layout.json').read_text(encoding='utf-8'));z=np.array(layout['z_cm'])
def curve(name,values):
    y=np.array(values);h=np.diff(z);d=np.diff(y)/h;m=np.zeros_like(y);m[0]=d[0];m[-1]=d[-1]
    for i in range(1,len(y)-1):
        if d[i-1]*d[i]>0:
            a=2*h[i]+h[i-1];b=h[i]+2*h[i-1];m[i]=(a+b)/(a/d[i-1]+b/d[i])
    lines=['float '+name+'=0.;']
    for i in range(len(h)):
        coeff=[2*y[i]-2*y[i+1]+h[i]*(m[i]+m[i+1]),-3*y[i]+3*y[i+1]-h[i]*(2*m[i]+m[i+1]),h[i]*m[i],y[i]]
        gate=('if' if i==0 else 'else if')+' ('+('true' if i==len(h)-1 else 'ZhanZ<=%.9f'%z[i+1])+')'
        lines.extend([gate+' {','float s=saturate((ZhanZ-%.9f)/%.9f);'%(z[i],h[i]),
            name+'=((%.9f*s+%.9f)*s+%.9f)*s+%.9f;'%tuple(coeff),'}'])
    return '\n'.join(lines)
code='''// ZHANMADAO_BLADE_CONTOUR_V1: Zhufeng central face; excludes the dorsal inlay.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ=P.z;
float ZhanFaceCoverage=smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity*=ZhanFaceCoverage;HaloOpacity*=ZhanFaceCoverage;
'''+curve('ZhanCenter',layout['center_x_cm'])+'\n'+curve('ZhanWidth',layout['rune_width_cm'])
code+='''
float ZhanAlong=(ZhanZ-%.9f)/%.9f;
P=float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N=float3(0,N.y>=0?1:-1,0);BladeOrigin=float3(0,0,0);BladeAxis=float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
'''%(z[0],z[-1]-z[0])
branch=(P.parent/'BeiweiRuneV1/beiwei_emission.hlsl').read_text(encoding='utf-8')
branch=branch.replace('BEIWEI_WIDTH_CM',format(layout['rune_width_cm'][len(z)//2],'.8f')).replace('BEIWEI_CENTER_CM',format(z[0]+(z[-1]-z[0])*.52,'.8f'))
(P/'rune_placement.hlsl').write_text('float3 BeiweiRawP=P.xyz;\n'+code+branch,encoding='utf-8')
print('ZHUFENG_RUNE_PLACEMENT_AUTHORED')
