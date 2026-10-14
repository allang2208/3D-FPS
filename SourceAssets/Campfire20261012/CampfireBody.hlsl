// Reuse the owned, offline Mantaflow combustion atlas; retain continuous coverage.
float h=saturate(1-UV.y);
float x=(UV.x-.5)*2;
float flame=saturate(Combustion.r);
float heat=saturate(Combustion.g);
float noise=N1*.62+N2*.38;
float width=.10+.76*pow(saturate(1-h),.58);
float sway=(N1-.5)*.22*h+(N2-.5)*.09;
float edge=1-smoothstep(width*.58,width,abs(x+sway));
float height=smoothstep(0,.065,h)*(1-smoothstep(.70,1,h));
float thickness=saturate(1-abs(x)/max(.10,width));
float temperature=saturate(.25+.35*thickness+.20*heat+.18*flame-.28*h);
float3 rgb=lerp(float3(1,.07,.004),float3(1,.36,.035),temperature);
rgb=lerp(rgb,float3(1,.62,.11),smoothstep(.64,.95,temperature));
return float4(rgb,edge*height*(.72+.20*noise+.08*flame));
