// The original painted glyphs gather power in opposing waves, then fracture in pulses.
uint w,h;NativeMask.GetDimensions(w,h);
float2 texel=2./max(float2(w,h),float2(1.,1.));
float ink=Texture2DSample(NativeMask,NativeMaskSampler,UV).r;
float halo=.25*(Texture2DSample(NativeMask,NativeMaskSampler,UV+float2(texel.x,0.)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV-float2(texel.x,0.)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV+float2(0.,texel.y)).r+
    Texture2DSample(NativeMask,NativeMaskSampler,UV-float2(0.,texel.y)).r);
float time=PreviewTime>=0.?PreviewTime:T;
float awake=saturate(RuneAwake);
float breath=.5+.5*sin(time*1.6);
float converge=pow(saturate(.5+.5*sin(abs(UV.y-.5)*52.+UV.x*17.-time*2.8)),5.);
float strike=pow(saturate(.5+.5*sin(time*5.2)),18.);
float fracture=pow(saturate(.5+.5*sin(UV.x*97.+UV.y*83.)),10.);
float3 violet=float3(1.15,.36,4.8),blue=float3(.2,1.7,4.5);
return ink*violet*(.22+.1*breath+awake*(1.8+.65*breath+1.4*converge))+
    ink*float3(2.1,2.7,4.8)*fracture*strike*awake*1.2+
    halo*blue*(.045+awake*(.38+.3*strike));
