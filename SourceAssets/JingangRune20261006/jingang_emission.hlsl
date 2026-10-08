// Jingang mode 9: actual sutra brushwork, continuous antique/amber/champagne gold.
if (RuneMode > 8.5 && RuneMode < 9.5)
{
    float3 axis=normalize(BladeAxis.xyz);
    float3 offset=P.xyz-BladeOrigin.xyz;
    float along=dot(offset,axis);
    float3 widthAxis=normalize(cross(normalize(N.xyz),axis));
    float2 uv=float2(.5+dot(offset,widthAxis)/Dimensions.x,1-(along-Dimensions.y)/Dimensions.z);
    float inside=smoothstep(.12,.21,uv.x)*(1-smoothstep(.79,.88,uv.x));
    inside*=smoothstep(.035,.095,uv.y)*(1-smoothstep(.92,.98,uv.y));
    inside*=1-smoothstep(Dimensions.x*.48,Dimensions.x*.56,length(offset-along*axis));
    // Mirror the brushwork vertically within its horizontal source strip.
    // Keep sentence order, projection bounds and the separate HUD atlas intact.
    float2 artUV=float2(saturate((uv.y-.075)/.86),.50-(uv.x-.5)*.52);
    float ink=Texture2DSample(RuneTexture,RuneTextureSampler,artUV).r;
    float time=PreviewTime>=0?PreviewTime:T;
    float flowing=.5+.5*sin(time*.75-uv.y*10.0+uv.x*3.1);
    float highlight=pow(saturate(flowing),4);
    float3 gold=lerp(float3(.39,.16,.025),float3(.96,.56,.115),.4+.6*flowing);
    gold=lerp(gold,float3(1.,.88,.52),highlight*.68);
    float dx=Texture2DSample(RuneTexture,RuneTextureSampler,artUV+float2(.00065,-.002)).r;
    float bevel=saturate(ink-dx);
    gold+=bevel*float3(.17,.12,.045);
    return float4(gold*(.62+.10*sin(time*.9)),ink*inside*RuneOpacity);
}
