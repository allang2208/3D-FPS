float vein=pow(saturate(1-abs(sin(UV.x*183+sin(UV.y*127)*2.6+sin(UV.x*41+UV.y*59)))),10);
float branch=pow(saturate(1-abs(sin(UV.y*211+sin(UV.x*93)*2.2))),17);
float veins=saturate(vein+branch*.65);
float3 glow=lerp(float3(.22,.045,.31),float3(2.7,2.05,3.1),veins);
return float4(glow*(.35+Alpha*1.4),Mask*Alpha*(.22+.58*veins));
