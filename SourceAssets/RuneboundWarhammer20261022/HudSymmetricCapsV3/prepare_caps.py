"""Complete the rune vessel with its own vertically reflected lower glass cap."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OLD=P.parent/'HudMotesV2'
source=P.parent/'PassiveV1/RuneboundEnergyHud.hlsl'
code=source.read_text('utf-8');original=code
layout=json.loads((ROOT/'SourceAssets/AzureDragon20261004/HudV10/Export/layout.json').read_text('utf-8'))
top=layout['top_boundary'];bottom=layout['bottom_boundary'];tip=layout['levels'][0]
def replace(old,new):
    global code
    if old not in code:raise RuntimeError('HUD source anchor changed: '+old[:70])
    code=code.replace(old,new,1)
replace('// Runebound HUD Motes V2; retain the measured glass/ribbon layout (texture pixels).','// Runebound symmetric glass caps V3; preserve the original fill and floating-mote layout.')
replace('static const float HudTopBoundary = 422.52;',f'static const float HudTopBoundary = {top:.8f};\nstatic const float HudBottomBoundary = {bottom:.8f};\n// Reflect the existing lower cap about the midpoint of the glass column.\nstatic const float HudCapMirrorY = {top+bottom:.8f};')
replace('float2 T = P / HudSize;\nfloat inTex = step(HudTopBoundary, P.y); // Exclude every baked dragon-head pixel.','''float topCap = 1.0-step(HudTopBoundary,P.y);
float2 sourceP = float2(P.x,lerp(P.y,HudCapMirrorY-P.y,topCap));
float2 T = sourceP/HudSize;
// Explicit derivatives avoid a false coarse mip where the two atlas regions meet.
float2 texDx=ddx(P)/HudSize;
float2 texDy=ddy(P)/HudSize;
texDx.y*=1.0-2.0*topCap;
texDy.y*=1.0-2.0*topCap;
float inTex=step(0.0,sourceP.y)*step(sourceP.y,HudSize.y);
// Upper pixels sample only the lower glass cap, so no old crest is reintroduced.''')
replace('float mixV = zone * below + (1.0 - zone) * (0.20 + 0.45 * capV);','float mixV = zone * below + (1.0 - zone) * capV;')
for name in ('MaskTex','EmptyTex','FullTex'):
    replace(f'Texture2DSample({name}, {name}Sampler, T)',f'Texture2DSampleGrad({name}, {name}Sampler, T, texDx, texDy)')
start=code.index('// Concentric blue rings now gather a soft nebula and moving round lights.')
end=code.index('// One bounded analytic layer:',start)
code=code[:start]+'''// The cap structure comes entirely from the retained lower glass texture.
// A restrained, vertically soft light cloud follows the same blue magic style.
// No independent circle, neck line, centre gem or floating crystal is added.
float capFocusY=HudTopBoundary-(HudLevels[0]-HudBottomBoundary)*.48;
float2 sealP=P-float2(HudCenter,capFocusY);
float2 cloudUV=sealP/230.0+float2(Age*.016,-Age*.023);
float cloudNoise=Texture2DSample(NoiseTex,NoiseTexSampler,cloudUV).g;
float2 hazeP=sealP/float2(52.0,86.0);
float haze=exp(-dot(hazeP,hazeP))*(.35+.65*cloudNoise);
float gathering=exp(-dot(sealP,sealP)/(23.0*23.0))*(.65+.35*sin(Age*.9));
float capLight=(haze*.12+gathering*.08)*(.22+fillV*.55+Burst*.7);
float luminance=max(col.r,max(col.g,col.b));
col=luminance*float3(.12,.47,1.0)+capLight*float3(.18,.58,1.0);
''' + code[end:]
replace('225.0+sin(orbit)*radius*.68+5.0*sin(Age*.8+phase)','capFocusY+sin(orbit)*radius*.68+5.0*sin(Age*.8+phase)')
code=code.replace('the dragon head occludes by','the upper mirrored glass cap occludes by')
code=code.replace('// This shader is shared by the passive installer and the dedicated HudMotesV2 author.','// Dedicated V3 shader; the previous V2 source and shared Azure Dragon assets remain intact.')
(P/'RuneboundEnergyHud.hlsl').write_text(code,encoding='utf-8')
record={'source_shader':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
 'top_boundary_px':top,'bottom_boundary_px':bottom,'reflection_sum_y_px':top+bottom,
 'body_midpoint_px':(top+bottom)/2.,'bottom_tip_px':tip,'top_tip_px':top+bottom-tip,
 'cap_height_px':tip-bottom,'cap_source':'existing lower cap, vertically mirrored with original masks and glass textures',
 'retained':['32 analytic floating motes','blue energy and rune ribbon','original nine fill levels','one UI material quad','viewport size and placement','Reveal/Fill/Age/Pulse/Burst/BodyOpacity parameters'],
 'removed':['independent upper circular seal','rigid upper neck line'],'new_texture_files':0,'tests_run':False}
(P/'cap_layout.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
script=(OLD/'install_assets.py').read_text('utf-8')
script=script.replace("DEST = '/Game/Weapons/RuneboundWarhammer20261022/HudMotesV2'","DEST = '/Game/Weapons/RuneboundWarhammer20261022/HudSymmetricCapsV3'")
script=script.replace("DONOR = '/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundEnergyHud'","DONOR = '/Game/Weapons/RuneboundWarhammer20261022/HudMotesV2/M_RuneboundEnergyHud'")
script=script.replace("'RuneboundHudMotesOwner', 'RuneboundHudMotesV2_20261023'","'RuneboundHudCapsOwner', 'RuneboundHudSymmetricCapsV3_20261023'")
script=script.replace("shader = P.parent/'PassiveV1/RuneboundEnergyHud.hlsl'","shader = P/'RuneboundEnergyHud.hlsl'")
script=script.replace('Blue glass and rune ribbon; gathering fireflies and rising soft motes; no floating crystals or centre gem','Symmetric top and bottom glass caps; lower cap vertically reflected; blue drifting motes; no dragon or independent top ring')
script=script.replace("'RuneboundWarhammer20261022/HudMotesV2'","'RuneboundWarhammer20261022/HudSymmetricCapsV3'")
script=script.replace("'centre_gem': False,","'centre_gem': False, 'symmetric_glass_caps': True, 'cap_layout': json.loads((P/'cap_layout.json').read_text('utf-8')),")
(P/'install_assets.py').write_text(script,encoding='utf-8')
script=(OLD/'author_isolated.py').read_text('utf-8')
script=script.replace("Path('Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundEnergyHud')","Path('Weapons/RuneboundWarhammer20261022/HudMotesV2/M_RuneboundEnergyHud')")
script=script.replace("Path('Weapons/RuneboundWarhammer20261022/HudMotesV2/M_RuneboundEnergyHud')\nHOST.mkdir","Path('Weapons/RuneboundWarhammer20261022/HudSymmetricCapsV3/M_RuneboundEnergyHud')\nHOST.mkdir")
(P/'author_isolated.py').write_text(script,encoding='utf-8')
(P/'build.ps1').write_text((P.parent/'FinalTollIntegrationV1/build.ps1').read_text('utf-8'),encoding='utf-8')
print('RUNEBOUND_SYMMETRIC_CAPS_AUTHORED',json.dumps({'top_tip_px':record['top_tip_px'],'body_midpoint_px':record['body_midpoint_px'],'cap_height_px':record['cap_height_px']}),flush=True)
