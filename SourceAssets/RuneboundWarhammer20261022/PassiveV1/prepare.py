"""Author the native UV emission mask and the blue, dragon-free energy vessel shader."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
(P/'Export').mkdir(exist_ok=True)
rgb=np.asarray(Image.open(P.parent/'Textures/BaseColor.jpg').convert('RGB'),dtype=np.float32)/255.
r,g,b=rgb.transpose(2,0,1)
# The supplied atlas paints the engraved runes blue. Reject neutral steel and gold;
# retain their original UVs so all clipped factory modules use the same strokes.
excess=np.minimum(b-r,(b-g)*2.)
mask=np.clip((excess-.025)/.10,0,1)*np.clip((b-.12)/.12,0,1)
mask=Image.fromarray(np.uint8(mask*255),'L').filter(ImageFilter.GaussianBlur(.35))
mask.save(P/'Export/T_RuneboundNativeRuneMask.png')

donor=ROOT/'SourceAssets/AzureDragon20261004/HudV10'
code=(donor/'HudLayout.hlsl').read_text(encoding='utf-8')+(donor/'AzureDragonHud.hlsl').read_text(encoding='utf-8')
code=code.replace('float inTex = step(0.0, P.y);','float inTex = step(HudTopBoundary, P.y); // Exclude every baked dragon-head pixel.')
ornament=r'''
// Native rune seal replaces the animal crest. Concentric blue rings enclose a
// faceted stone and straight rune strokes, joined to the original glass column.
float2 sealP=P-float2(HudCenter,225.0);
float rad=length(sealP);
float outer=exp(-pow((rad-108.0)/2.0,2.0));
float innerRing=exp(-pow((rad-91.0)/1.5,2.0));
float angle=atan2(sealP.y,sealP.x);
float notches=pow(saturate(cos(angle*12.0+Age*.15)),18.0)*exp(-pow((rad-100.0)/5.0,2.0));
float diamond=abs(sealP.x)/49.0+abs(sealP.y)/80.0;
float facet=exp(-pow((diamond-1.0)/.025,2.0));
float stone=(1.0-Fn.SS(.92,1.0,diamond))*(.12+.2*fillV);
float stem=exp(-pow(sealP.x/1.6,2.0))*step(abs(sealP.y),41.0);
float branch=(exp(-pow((sealP.y+sealP.x*.65+16.0)/1.5,2.0))+
              exp(-pow((sealP.y-sealP.x*.65+16.0)/1.5,2.0)))*step(abs(sealP.x),22.0);
float neck=exp(-pow((P.x-HudCenter)/3.0,2.0))*step(334.0,P.y)*step(P.y,HudTopBoundary);
float seal=(outer*.65+innerRing*.4+notches*.8+facet+stone+stem+branch+neck*.7)*(0.6+fillV*.5+Burst*.5);
float luminance=max(col.r,max(col.g,col.b));
col=luminance*float3(.12,.47,1.0)+seal*float3(.18,.58,1.0);
// Additional slow floating motes, including while charge is still accumulating.
[unroll] for(int mote=0;mote<24;++mote)
{
    float seed=Fn.Hash(mote*17.713+2.0);
    float life=frac(Age*(.045+seed*.025)+Fn.Hash(mote*31.2));
    float2 pos=float2(HudCenter+(Fn.Hash(mote*23.7)-.5)*390.0+13.0*sin(Age*.65+mote*2.1),1900.0-life*1820.0);
    float2 delta=P-pos;
    float intensity=sin(life*3.14159265)*(.18+.45*fillV)*(1.0+.2*Burst);
    float core=exp(-dot(delta,delta)/(2.5+seed*5.0));
    float halo=exp(-dot(delta,delta)/(25.0+seed*28.0))*.18;
    col+=(core+halo)*intensity*float3(.23,.6,1.0);
}
'''
code=code.replace('col = saturate(col);',ornament+'\ncol = saturate(col);')
(P/'RuneboundEnergyHud.hlsl').write_text(code,encoding='utf-8')
(P/'RuneboundMote.hlsl').write_text('''float2 d=(UV-.5)*2.;
float radius=dot(d,d);
float a=saturate(exp(-radius*5.)-exp(-5.))*Strength;
return float4(float3(.16,.48,1.0)*(1.0+exp(-radius*20.)*2.),a*.8);
''',encoding='utf-8')
print('RUNEBOUND_PASSIVE_SOURCE_AUTHORED')
