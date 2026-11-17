// Dense pressure filaments lose both width and energy toward their tips.
// A short envelope prevents the impact from lingering as stationary light rods.
float2 p=float2(UV.x-.5,(UV.y-.90)*.56);
float r=length(p),a=atan2(p.y,p.x);
float twist=.65*sin(a*5)+.42*sin(a*13+.7);
float reach=.32+.065*sin(a*7+.4)+.035*sin(a*19);
float taper=pow(saturate(1-r/max(.10,reach)),1.7);
float sharpness=9+28*saturate(r/max(.10,reach));
float primary=pow(saturate(.5+.5*cos(a*43+twist)),sharpness);
float fine=pow(saturate(.5+.5*cos(a*71+.9*sin(a*11))),28)*.22;
float root=smoothstep(.015,.06,r);
float grain=.65+.35*sin(r*47+a*9)*sin(r*29-a*13);
float core=pow(1-smoothstep(0,.18,r),3)*.20;
return saturate((primary+fine)*taper*root*grain*2.4+core)*(1-smoothstep(.90,.98,UV.y));
