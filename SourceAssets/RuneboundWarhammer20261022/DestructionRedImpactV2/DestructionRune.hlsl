// Preserve the native painted glyphs; crimson converging waves and a hot red core.
uint w,h;NativeMask.GetDimensions(w,h);
float2 texel=2./max(float2(w,h),float2(1.,1.));
float ink=Texture2DSample(NativeMask,NativeMaskSampler,UV).r;
float halo=.25*(Texture2DSample(NativeMask,NativeMaskSampler,UV+float2(texel.x,0.)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV-float2(texel.x,0.)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV+float2(0.,texel.y)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV-float2(0.,texel.y)).r);
float time=PreviewTime>=0.?PreviewTime:T;
float awake=saturate(RuneAwake),impact=saturate(RuneImpact);
float breath=.5+.5*sin(time*1.8);
float converge=pow(saturate(.5+.5*sin(abs(UV.y-.5)*52.+UV.x*17.-time*3.4)),5.);
float strike=pow(saturate(.5+.5*sin(time*5.2)),18.);
float fracture=pow(saturate(.5+.5*sin(UV.x*97.+UV.y*83.)),10.);
float3 crimson=float3(4.6,.028,.012),hot=float3(6.2,.38,.055);
return ink*crimson*(.18+.06*breath+awake*(1.5+.55*breath+1.3*converge+impact*1.4))+
    ink*hot*fracture*(strike*.85+impact*2.2)*awake+
    halo*float3(2.4,.018,.006)*(.035+awake*(.36+.22*strike+.7*impact));
