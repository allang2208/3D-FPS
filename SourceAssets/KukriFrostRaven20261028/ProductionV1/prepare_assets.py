"""Derive independent production shaders and projection fitting from the current accepted pipeline."""
from pathlib import Path
import shutil
import runpy
P=Path(__file__).resolve().parent
S=P.parents[1]
B=S/'KukriBerserker20261028'
shutil.copy2(B/'blade-layout-source.json',P/'blade-layout-source.json')
fit="from pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).resolve().parent.parent/'BladeSigilV2/fit_projection.py'),run_name='__main__')\n"
(P/'fit_projection.py').write_text(fit,encoding='utf-8')
shutil.copy2(B/'VolumeRefine/RuneProjection.hlsl',P/'RuneProjection.hlsl')
hud=(B/'WolfHeadComposite/BerserkerWolfHeadHud.hlsl').read_text('utf-8')
start=hud.index('// Berserker: the original floating glass')
end=hud.index('col = saturate(col);',start)
hud=hud[:start]+'''// Frost Raven: the same glass and continuous helix, with a dimensional authored crown.
float iceLum=max(col.r,max(col.g,col.b));
col=iceLum*float3(.22,.66,1.0);
float2 headUV=(P-float2(6.0,56.0))/float2(500.0,500.0);
float headInside=step(0,headUV.x)*step(headUV.x,1)*step(0,headUV.y)*step(headUV.y,1);
float4 head=Texture2DSample(WolfHeadTex,WolfHeadTexSampler,saturate(headUV));
float headOpacity=head.a*headInside*saturate(BodyOpacity*1.15);
float3 headColor=head.rgb*(.94+.06*fillV+.10*Pulse+.12*Burst);
float blueVein=saturate(head.b-max(head.r,head.g*.75));
headColor+=blueVein*float3(.02,.12,.18)*(fillV*.45+Pulse*.3+Burst*.5);
col=col*(1.0-headOpacity)+headColor*headOpacity;
float division=frac((P.y-HudTopBoundary)/(HudBottomBoundary-HudTopBoundary)*8.0);
float seam=(1-Fn.SS(.016,.045,min(division,1-division)))*inner*zone;
col*=1-seam*.34;
'''+hud[end:]
hud=hud.replace('11.0 / 12.0','7.0 / 8.0')
compose=runpy.run_path(str(P.parent/'CrystalCrownV3/compose_head.py'))
hud=compose['apply_crown_layout'](hud)
(P/'FrostRavenEnergyHud.hlsl').write_text(hud,encoding='utf-8')
active=(B/'ActiveFX/author_materials.py').read_text('utf-8')
active=active.replace("P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/ActiveFX/author_materials.py').resolve().parent","P=Path(__file__).resolve().parent")
active=active.replace("ROOT='/Game/Weapons/Kukri20261020/Berserker20261028/ActiveFX'","ROOT='/Game/Weapons/Kukri20261020/FrostRaven20261028/ActiveFX'")
a=active.index("edge=material(");b=active.index("ember=material(",a)
active=active[:a]+active[b:]
active=active.replace('Berserker','FrostRaven').replace('materials=(edge,ember,weapon)','materials=(ember,weapon)').replace('RisingArmCloudAndWholeWeaponRedV2','IceFlecksAndBladeSheenV1')
(P/'author_materials.py').write_text(active,encoding='utf-8')
