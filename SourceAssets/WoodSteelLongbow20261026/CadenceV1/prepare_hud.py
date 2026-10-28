from pathlib import Path
P=Path(__file__).parent
s=(P.parent/'MountainEchoAlpineV23/import_hud.py').read_text(encoding='utf-8')
s=s.replace('MountainEchoAlpineV23','CadenceV1').replace('MountainEcho_Alpine','Cadence_HUD')
s=s.replace('M_Cadence_HUDHUD','M_Cadence_HUD').replace('AlpineTexture','CadenceTexture')
s=s.replace('import-receipt.json','hud-import-receipt.json')
s=s.replace('0 / 1/3 / 2/3 / 1; continuous animated reveal','0 / 1/5 / 2/5 / 3/5 / 4/5 / 1; animated reveal')
a=s.index('float p=saturate(Progress);');b=s.index("\n''')",a)
s=s[:a]+'''float p=saturate(Progress);
float lit=p<=0.0001?0:(p>=0.9999?1:1-smoothstep(p-0.008,p+0.008,UV.x));
float full=smoothstep(0.99,1.0,p);
float alpha=pow(saturate(Alpha),1.25);
float luma=dot(RGB,float3(0.2126,0.7152,0.0722));
float3 silver=luma*float3(0.72,0.89,1.04);
float3 gold=luma*float3(1.14,0.97,0.67);
float3 dormant=luma*float3(0.20,0.25,0.29);
float front=exp(-pow((UV.x-p)/0.027,2));
float crest=smoothstep(0.35,0.95,luma);
float3 active=lerp(silver,gold,full)*(0.92+0.08*Breath);
active+=lerp(float3(0.55,0.80,1),float3(1,0.86,0.58),full)*crest*(0.35*Gain*front+full*(0.16*Pulse+0.065*Breath));
return float4(lerp(dormant,active,lit),alpha*lerp(0.62,1,lit));
'''+s[b:]
(P/'import_hud.py').write_text(s,encoding='utf-8')
