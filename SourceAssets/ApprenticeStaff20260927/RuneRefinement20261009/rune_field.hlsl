// Original art is untouched. UV0 is the actual bark patch, with FBX V inverted.
float2 uv = ArtOrigin.xy + saturate(UV.xy) * ArtSize.xy;
uint width, height;
RuneTexture.GetDimensions(width, height);
float2 texel = 1.0 / max(float2(width, height), 1.0);
float ink = Texture2DSample(RuneTexture, RuneTextureSampler, uv).r;
float l = Texture2DSample(RuneTexture, RuneTextureSampler, uv-float2(texel.x,0)).r;
float r = Texture2DSample(RuneTexture, RuneTextureSampler, uv+float2(texel.x,0)).r;
float b = Texture2DSample(RuneTexture, RuneTextureSampler, uv+float2(0,texel.y)).r;
float t = Texture2DSample(RuneTexture, RuneTextureSampler, uv-float2(0,texel.y)).r;
float feather = max(fwidth(ink)*0.6, .035);
float coverage = smoothstep(.19-feather, .19+feather, ink);
float border = smoothstep(0,.014,UV.x)*(1-smoothstep(.986,1,UV.x));
border *= smoothstep(0,.008,UV.y)*(1-smoothstep(.992,1,UV.y));
// Raised metal line edge, shallow enough to keep the coarse bark normal readable.
float2 bevel = float2(l-r,t-b)*BevelStrength;
return float4(coverage*border,bevel.x,bevel.y,ink);
