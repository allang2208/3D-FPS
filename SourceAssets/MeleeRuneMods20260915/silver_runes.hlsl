// Component-space projection follows the current Blade_Base/Blade_Tip frame.
float3 axis = normalize(BladeAxis.xyz);
float3 offset = P.xyz - BladeOrigin.xyz;
float along = dot(offset, axis);
float3 widthAxis = cross(normalize(N.xyz), axis);
widthAxis *= rsqrt(max(dot(widthAxis,widthAxis), 0.0001));
float2 uv = float2(0.5 + dot(offset,widthAxis)/Dimensions.x,
                  1.0 - (along-Dimensions.y)/Dimensions.z);
float inside = step(0,uv.x)*step(uv.x,1)*step(0,uv.y)*step(uv.y,1);
float radial = length(offset-along*axis);
inside *= 1-smoothstep(Dimensions.x*.48,Dimensions.x*.56,radial);
float4 tex = Texture2DSample(RuneTexture,RuneTextureSampler,saturate(uv));
// Extract the silver cores; the artwork's dark/soft backdrop never coats metal.
float luminance = dot(tex.rgb,float3(.2126,.7152,.0722));
float mask = smoothstep(.62,.94,luminance)*tex.a*inside;
float time = PreviewTime>=0 ? PreviewTime : T;
float pulse;
if(RuneMode<.5)
    pulse = .52 + .38*(.5+.5*sin(time*2.2-along*.024)) + .1*pow(.5+.5*sin(time*7.1),8);
else if(RuneMode<1.5)
    pulse = .38 + .36*(.5+.5*sin(time*9.7+along*.39)) + .26*pow(.5+.5*sin(time*17.3-along*.17),4);
else
{
    float wave = pow(.5+.5*sin(along*.17-time*4.5),10);
    pulse = .42 + .46*wave + .12*(.5+.5*sin(time*6.1));
}
float brightness = GlowStrength*pulse;
return float4(brightness.xxx,mask);
