// Soft crossed ribbons with flowing, uneven internal strands. No solid cylinder.
float across=UV.x*2-1;
float wobble=.10*sin(UV.y*28-Clock*7)+.045*sin(UV.y*63+Clock*3);
float soft=exp(-5.5*pow(across-wobble,2))*(1-smoothstep(.70,1.,abs(across)));
float strands=.64+.19*sin(UV.y*46-Clock*17+across*5)+.11*sin(UV.y*91-Clock*23-across*9);
float tips=smoothstep(0.,.016,UV.y)*(1-smoothstep(.985,1.,UV.y));
float3 tint=lerp(float3(.19,.15,.31),float3(.31,.39,.43),saturate(.5+.5*sin(UV.y*13-Clock*2+across)));
float glow=1.7+FirePower*1.5;
// V12: stronger, soft-edged warning at charge time. The release keeps its
// existing width/colour/energy path; no change to its gameplay collision.
float warning=1-smoothstep(.02,.18,FirePower);
float warningSoft=exp(-3.2*pow(across-wobble*.55,2))*(1-smoothstep(.82,1.,abs(across)));
float warningCore=exp(-28*across*across);
float warningFlow=.94+.06*sin(UV.y*18-Clock*7);
float profile=lerp(soft*strands,(warningSoft*.88+warningCore*.12)*warningFlow,warning);
tint=lerp(tint,float3(.56,.48,.78),warning*.8);
glow+=warning*.7;
return float4(tint*glow/max(Exposure,.25),saturate(Strength*.58*profile*tips*lerp(1.,3.2,warning)));
