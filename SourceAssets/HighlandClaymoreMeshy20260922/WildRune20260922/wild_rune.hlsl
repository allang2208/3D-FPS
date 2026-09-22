// Stable blade-local projection keeps broadblade bevels from stretching glyphs.
float3 axis = normalize(BladeAxis.xyz);
float3 offset = P.xyz - BladeOrigin.xyz;
float along = dot(offset, axis);
float3 widthAxis = normalize(cross(float3(0,1,0),axis));
float3 depthAxis = normalize(cross(axis,widthAxis));
float width = Dimensions.x * .70;
float2 uv = float2(.5 + dot(offset,widthAxis)/width,
                  1.0 - (along-Dimensions.y)/Dimensions.z);
float inside = smoothstep(0,.025,uv.x)*(1-smoothstep(.975,1,uv.x));
inside *= smoothstep(0,.025,uv.y)*(1-smoothstep(.975,1,uv.y));
inside *= smoothstep(.35,.78,abs(dot(normalize(N.xyz),depthAxis)));
inside *= step(4.5,RuneMode);
uint tw, th;
RuneTexture.GetDimensions(tw,th);
float2 texel = HaloRadiusTexels/max(float2(tw,th),float2(1,1));
float core = Texture2DSample(RuneTexture,RuneTextureSampler,saturate(uv)).r;
float nearHalo = .25*(
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+float2(texel.x,0)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv-float2(texel.x,0)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+float2(0,texel.y)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv-float2(0,texel.y)).r);
float farHalo = .25*(
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+texel*2.3).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv-texel*2.3).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+texel*float2(2.3,-2.3)).r+
    Texture2DSample(RuneTexture,RuneTextureSampler,uv+texel*float2(-2.3,2.3)).r);
float time = PreviewTime >= 0 ? PreviewTime : T;
float wave = .5+.5*sin(time*WildPulseSpeed-along*.050);
float heartbeat = wave*wave*(3-2*wave);
float pulse = .58+.42*heartbeat;
float halo = nearHalo*.70+farHalo*.30;
float coverage = saturate(core*RuneOpacity+halo*HaloOpacity*(.75+.25*heartbeat));
float blendCore = saturate(core/max(core+halo*.24,.0001));
float3 coreColor = WildCoreColor*BaseBrightness+WildGlowColor*GlowStrength*pulse;
float3 glowColor = WildGlowColor*GlowStrength*.58*pulse;
float3 color = lerp(glowColor,coreColor,blendCore);
float peak = max(color.r,max(color.g,color.b));
color *= min(1.,EmissionPeak/max(peak,.0001));
return float4(color,coverage*inside);
