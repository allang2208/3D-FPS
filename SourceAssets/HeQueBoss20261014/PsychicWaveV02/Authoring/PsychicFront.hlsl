float flight=max(0,Phase);
float progress=saturate(flight/.36);
float poles=sin(UV.y*3.14159265);
float2 flowUV=float2(frac(UV.x+Seed*.173+flight*.075),UV.y);
float3 coarse=Texture2DSample(FlowTex,FlowTexSampler,flowUV).rgb;
float2 drift=(coarse.rb-.5)*float2(.055,.025)*poles;
float3 flow=Texture2DSample(FlowTex,FlowTexSampler,float2(frac(flowUV.x+drift.x),saturate(flowUV.y+drift.y))).rgb;
float rim=1-abs(dot(normalize(NormalWS),normalize(View)));
float outline=pow(saturate(rim),2.2);
float birth=smoothstep(0,.018,flight);
float density=smoothstep(.29,.76,flow.r);
float filament=pow(saturate(flow.g),1.5);
float dissolve=smoothstep(.34,.60,flight);
float edgeBreak=lerp(1,smoothstep(dissolve*.72,dissolve*.72+.23,flow.r),dissolve);
float opacity=0;
float3 color=0;
if(Layer.r<.5)
{
    // A coherent thin compression edge, not bright stripes over a filled orb.
    float edge=outline*(.78+.22*flow.b);
    opacity=(edge*.50+filament*.032)*edgeBreak;
    color=lerp(float3(.52,.40,.67),float3(1.55,1.40,1.85),outline);
}
else if(Layer.g<.5)
{
    float breakup=smoothstep(.24+.40*progress,.75,flow.r);
    opacity=(density*.045+filament*.19)*(.18+.82*outline)*breakup*(1-smoothstep(.28,.52,flight));
    color=lerp(float3(.20,.12,.31),float3(.82,.65,1.05),filament);
}
else
{
    float shred=smoothstep(.40+.35*progress,.85,flow.r);
    opacity=filament*.12*shred*(.12+.88*outline)*(1-smoothstep(.18,.42,flight));
    color=float3(.35,.23,.49);
}
opacity=saturate(opacity*Alpha*birth);
return float4(color,opacity);
