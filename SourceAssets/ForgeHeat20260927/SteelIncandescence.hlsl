float heat=max(Heat,0);
float edge=1-smoothstep(.9,3.1,abs(P.y));
float tang=smoothstep(-29,-19,P.x);
float impact=exp(-dot(P-HitPoint,P-HitPoint)/3.2)*exp(-max(HitAge,0)*7);
float temperature=saturate((heat-.18)/1.08)*lerp(.76,1,edge)*lerp(.77,1,tang);
temperature=saturate(temperature+(Surface.w-.5)*.11+impact*.12);
float3 red=float3(1,.028,.0015);
float3 orange=float3(1,.23,.012);
float3 hot=float3(1,.52,.095);
float3 color=lerp(red,orange,smoothstep(.2,.78,temperature));
color=lerp(color,hot,smoothstep(.77,1.08,temperature));
// Thin oxide scales occlude the glow; fresh metal briefly brightens at contact.
float oxide=Surface.x*(1-impact*.8);
float emission=pow(saturate(heat/1.2),2.25)*(9+8*edge+impact*9);
return color*emission*lerp(1,.12,oxide)*lerp(.87,1.05,Surface.y);
