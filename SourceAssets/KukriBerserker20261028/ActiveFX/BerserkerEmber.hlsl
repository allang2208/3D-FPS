// Runebound hit-mote reference: round bright core and a broad Gaussian body.
// A soft second layer fills the arm cloud without sharp shards or broken strips.
float2 p=UV*2.0-1.0;
float radius=dot(p,p);
float core=exp(-radius*19.0);
float body=max(0.0,exp(-radius*4.2)-exp(-4.2));
float rim=(1.0-smoothstep(.76,.99,abs(p.x)))*(1.0-smoothstep(.76,.99,abs(p.y)));
float shape=lerp(core*.62+body*.82,body*.88,saturate(Kind));
float alpha=saturate(shape*rim*Alpha);
float3 crimson=lerp(float3(2.6,.018,.038),float3(5.2,.10,.14),core*(1.0-Kind*.7));
crimson*=lerp(1.0,.78,saturate(Life));
return float4(crimson,alpha);
