"""Derive owned rune bakes and a red HUD while preserving current weapon sources."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
S=P.parent
sources=[]
for folder in ('KukriRuneNatural20261027','KukriHunterBlade20261027','KukriCanineBlade20261027'):
    sources+=json.loads((S/folder/'blade-layout-source.json').read_text('utf-8'))
(P/'blade-layout-source.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
script=(S/'KukriRuneNatural20261027/bake_runes.py').read_text('utf-8')
start=script.index('plans=');end=script.index('layouts=[]')
script=script[:start]+'''plans=[{'id':'berserker_rune','kind':'Berserker'}]
sources=json.loads((P/'blade-layout-source.json').read_text(encoding='utf-8'))
receipt={'runes':[]}
entries={'berserker_rune':{'id':'berserker_rune','kind':'Berserker'}}
'''+script[end:]
script=script.replace("OLD/'Concepts'/(plan['id']+'.png')","P/'Art/WolfSigil.png'")
script=script.replace("(OLD/'runes.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')",'')
script=script.replace('natural-isometric-per-blade-20261027','berserker-per-blade-20261028')
script=script.replace('Kukri_Runes_Natural_Editable.blend','Kukri_Berserker_Runes_Editable.blend')
(P/'bake_runes.py').write_text(script,encoding='utf-8')
hud=(S/'RuneboundWarhammer20261022/HudSymmetricCapsV3/RuneboundEnergyHud.hlsl').read_text('utf-8')
# Twelve equal-height charges, with the same meniscus animation and retained caps.
start=hud.index('float f9 =');end=hud.index('float charged =')
hud=hud[:start]+'''float menY=lerp(HudBottomBoundary,HudTopBoundary,fillV);
'''+hud[end:]
hud=hud.replace('Fn.SS(8.4 / 9.0, 1.0, fillV)','Fn.SS(11.0 / 12.0, 1.0, fillV)')
marker='col = saturate(col);'
art='''// Berserker: the original floating glass, helix and all 32 drifting motes remain.
// Recolor the complete light layer together, avoiding leftover blue highlights.
float bloodLum=max(col.r,max(col.g,col.b));
col=bloodLum*float3(1.0,.022,.038);
float2 wolfUV=(P-float2(132.0,-180.0))/float2(248.0,555.0);
float wolfInside=step(0,wolfUV.x)*step(wolfUV.x,1)*step(0,wolfUV.y)*step(wolfUV.y,1);
float4 wolfTexel=Texture2DSample(WolfTex,WolfTexSampler,saturate(wolfUV));
float wolf=wolfTexel.a*wolfTexel.r*wolfInside;
col+=wolf*float3(.90,.045,.05)*(.52+.40*fillV+.35*Burst+.16*Pulse);
// Fine scar cuts show twelve charging intervals without baked text.
float division=frac((P.y-HudTopBoundary)/(HudBottomBoundary-HudTopBoundary)*12.0);
float scar=(1-Fn.SS(.016,.055,min(division,1-division)))*inner*zone;
col*=1-scar*.38;
// A pointed blood drop below the glass finishes the wolf/fang silhouette.
float2 tip=(P-float2(HudCenter,1880.0))/float2(30.0,105.0);
float drop=(1-Fn.SS(.72,1.0,length(float2(tip.x*(1.3+.5*tip.y),tip.y))))*step(-1.2,tip.y)*step(tip.y,1.0);
col+=drop*float3(.56,.012,.024)*(.22+.5*fillV+.25*Pulse);
'''
hud=hud.replace(marker,art+marker)
(P/'BerserkerEnergyHud.hlsl').write_text(hud,encoding='utf-8')
shutil.copy2(S/'BleedingFixBurst20261027/build-editor.ps1',P/'build-editor.ps1')
print('BERSERKER_SOURCES_PREPARED',len(sources))
