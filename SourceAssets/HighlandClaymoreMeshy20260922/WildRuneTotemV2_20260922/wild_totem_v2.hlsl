// One continuous beast-jaw / claw-cut / bone-spear composition, never tiled.
float3 axis=normalize(BladeAxis.xyz);
float3 offset=P.xyz-BladeOrigin.xyz;
float along=dot(offset,axis);
float3 widthAxis=normalize(cross(float3(0,1,0),axis));
float3 depthAxis=normalize(cross(axis,widthAxis));
float width=Dimensions.x*.92;
float2 bladeUV=float2(.5+dot(offset,widthAxis)/width,
                     1.0-(along-Dimensions.y)/Dimensions.z);
float inside=smoothstep(0,.018,bladeUV.x)*(1-smoothstep(.982,1,bladeUV.x));
inside*=smoothstep(0,.018,bladeUV.y)*(1-smoothstep(.982,1,bladeUV.y));
inside*=smoothstep(.40,.82,abs(dot(normalize(N.xyz),depthAxis)));
inside*=step(4.5,RuneMode);

// Sample the intact generated horizontal image through its authored crop rect.
// Jaw at the blade root; spear converges toward the tip. No raster transforms.
float2 uv=ArtUVRect.xy+float2(bladeUV.y,1-bladeUV.x)*ArtUVRect.zw;
uint tw,th;RuneTexture.GetDimensions(tw,th);
float2 texel=HaloRadiusTexels/max(float2(tw,th),float2(1,1));
float value=Texture2DSample(RuneTexture,RuneTextureSampler,uv).r;
float core=saturate((value-.028)/.88);
float nearHalo=.25*(
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+float2(texel.x,0)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv-float2(texel.x,0)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+float2(0,texel.y)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv-float2(0,texel.y)).r);
float farHalo=.25*(
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+texel*2.6).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv-texel*2.6).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+texel*float2(2.6,-2.6)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+texel*float2(-2.6,2.6)).r);
float halo=saturate((nearHalo*.72+farHalo*.28-.028)/.88);
float time=PreviewTime>=0?PreviewTime:T;
float jaw=smoothstep(.68,.87,bladeUV.y);
float slow=.5+.5*sin(time*WildPulseSpeed+along*.047+3*sin(along*.032));
float ember=pow(saturate(.5+.5*sin(time*.92-along*.12)),8);
float pulse=.55+.19*slow+.13*ember;
float3 accent=lerp(WildGlowColor,float3(1,.055,.009),ember*.32);
float3 carved=WildCoreColor*BaseBrightness;
float3 coreColor=carved+accent*GlowStrength*pulse*(.86+.18*jaw);
float3 haloColor=WildGlowColor*GlowStrength*.40*pulse;
float blendCore=saturate(core/max(core+halo*.20,.0001));
float3 color=lerp(haloColor,coreColor,blendCore);
float peak=max(color.r,max(color.g,color.b));
color*=min(1.,EmissionPeak/max(peak,.0001));
float coverage=saturate(core*RuneOpacity+halo*HaloOpacity*(.76+.24*slow));
return float4(color,coverage*inside);
