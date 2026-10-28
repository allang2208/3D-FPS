"""Splice the generated crown into the existing bar; preserve the lower design."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
P=Path(__file__).resolve().parent
im=Image.open(P/'Art/WolfHead_Crown.png').convert('RGBA')
a=np.asarray(im)[:,:,3]
# Fit the actual neck connection, not the head's overall bounding box.
neck_y=1030
xs=np.where(a[neck_y]>128)[0]
neck_x=float(xs[0]+xs[-1])*.5
scale=182.04/float(xs[-1]-xs[0])
cut=480.0
origin=[256.0-neck_x*scale,cut-neck_y*scale]
extent=[im.width*scale,im.height*scale]
code=(P.parent/'BerserkerEnergyHud.hlsl').read_text('utf-8')
# Replace only the old ribbon drawing. Its layout constants remain authoritative.
start=code.index('// Helical rune ribbon:')
end=code.index('// Rising sparks.',start)
code=code[:start]+(P/'HelixParticles.hlsl').read_text('utf-8')+'\n\n'+code[end:]
start=code.index('        float speed=.039+seed*.027;')
end=code.index('        visibility=envelope*envelope;',start)+len('        visibility=envelope*envelope;')
code=code[:start]+(P/'HelixDrift.hlsl').read_text('utf-8').rstrip()+code[end:]
code=code.replace('// rising beside the glass. Position and fade are continuous at each life boundary.',
    '// born on the helix and drifting away. Birth and death remain continuous.')
code=code.replace('static const float HudTopBoundary = 422.52290809;',f'static const float HudTopBoundary = {cut:.8f};')
start=code.index('float topCap =')
end=code.index('float fillV =',start)
code=code[:start]+'''// Remove the old upper pointed cap. The retained straight column starts here.
float2 sourceP=P;
float2 T=sourceP/HudSize;
float2 texDx=ddx(P)/HudSize;
float2 texDy=ddy(P)/HudSize;
float inTex=Fn.SS(HudTopBoundary-1.0,HudTopBoundary+1.0,P.y)*step(P.y,HudSize.y);
'''+code[end:]
start=code.index('float2 wolfUV=')
end=code.index('// Fine scar cuts',start)
# Head composites after the vessel, lights and helical layer, using real alpha
# instead of brightness-derived linework. Its original design shading survives.
head=f'''// Generated volumetric head: same production-image technique as Azure Dragon HUD V10.
float2 headUV=(P-float2({origin[0]:.9f},{origin[1]:.9f}))/float2({extent[0]:.9f},{extent[1]:.9f});
float headInside=step(0,headUV.x)*step(headUV.x,1)*step(0,headUV.y)*step(headUV.y,1);
float4 head=Texture2DSample(WolfHeadTex,WolfHeadTexSampler,saturate(headUV));
float headOpacity=head.a*headInside*saturate(BodyOpacity*1.15);
float3 headColor=head.rgb*(.92+.08*fillV+.10*Pulse+.12*Burst);
// Only existing red veins breathe; never reduce the whole head to red luminance.
float redVein=saturate(head.r-max(head.g,head.b)*2.0);
headColor+=redVein*float3(.07,.001,.002)*(fillV*.45+Pulse*.3+Burst*.5);
col=col*(1.0-headOpacity)+headColor*headOpacity;
'''
code=code[:start]+head+code[end:]
code=code.replace('float coverage = saturate(max(bodyA,','bodyA=max(bodyA,headOpacity);\nfloat coverage = saturate(max(bodyA,')
code=code.replace('bodyA=max(bodyA,headOpacity);','bodyA=max(bodyA,max(headOpacity,helixParticleCoverage));')
(P/'BerserkerWolfHeadHud.hlsl').write_text(code,encoding='utf-8')
(P/'head-layout.json').write_text(json.dumps({'source_size':list(im.size),'neck_sample_y':neck_y,
    'neck_edges':[int(xs[0]),int(xs[-1])],'neck_center_x':neck_x,'uniform_scale':scale,
    'hud_origin':origin,'hud_extent':extent,'column_cut_y':cut,'column_width':182.04,
    'projection':'Single uniform scale; same camera-space HUD quad; no gameplay change'},indent=2),encoding='utf-8')
print('WOLF_CROWN_COMPOSED',json.dumps({'origin':origin,'extent':extent,'cut_y':cut}))
