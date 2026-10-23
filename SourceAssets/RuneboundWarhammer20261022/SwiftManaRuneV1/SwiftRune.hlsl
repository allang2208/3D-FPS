// Original painted UV strokes, with a brighter cyan-blue traveling pulse.
uint w,h;NativeMask.GetDimensions(w,h);
float2 texel=1.5/max(float2(w,h),float2(1.,1.));
float ink=Texture2DSample(NativeMask,NativeMaskSampler,UV).r;
float halo=.25*(Texture2DSample(NativeMask,NativeMaskSampler,UV+float2(texel.x,0.)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV-float2(texel.x,0.)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV+float2(0.,texel.y)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV-float2(0.,texel.y)).r);
float awake=saturate(RuneAwake);
float time=PreviewTime>=0.?PreviewTime:T;
float breath=.72+.28*sin(time*2.1);
float wave=pow(saturate(.5+.5*sin(UV.y*38.-UV.x*14.-time*4.8)),8.);
float energy=.16+.09*breath+awake*(1.4+.35*breath+1.1*wave);
float3 blue=float3(.12,1.1,4.5);
return ink*blue*energy+halo*float3(.08,.7,2.7)*awake*.38+
    ink*float3(.5,2.,4.)*pow(wave,2.)*awake*.42;
