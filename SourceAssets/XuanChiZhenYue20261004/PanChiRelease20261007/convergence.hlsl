struct PanChiNoise
{
    float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
    float noise(float2 p)
    {
        float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
    }
};
PanChiNoise n;
float t=max(0,Seconds);
float2 q=(UV-Converge.xy)*float2(600,1200);
float radius=length(q);
float angle=atan2(q.y,q.x);
float noise=n.noise(q*.031+float2(t*.9,-t*.65))*.64+n.noise(q*.071-t)*.36;
float gather=smoothstep(.16,.72,t);
float life=smoothstep(0,.07,t)*(1-smoothstep(.83,1.28,t));
float sealLife=smoothstep(.40,.69,t)*(1-smoothstep(.76,1.08,t));
float ringRadius=lerp(154,52,gather);
float cloudBand=exp(-pow((radius-ringRadius)/33,2));
float broken=smoothstep(.24,.76,noise+.15*sin(angle*3-t*4));
float inward=cloudBand*broken*life*.19;
// Brief contact feedback starts at the gameplay hit; the later visual convergence
// never delays damage or pulling. No outward blast implying knockback.
float contact=exp(-radius*radius/1900)*exp(-t*21)*.30;
float core=exp(-radius*radius/3600)*sealLife*.18;
float stamp=0;
[unroll] for(int i=0;i<2;i++)
{
    float around=frac(angle/6.283185+i*.5+t*.035);
    float2 duv=float2(around*2,.5+(radius-62)/92);
    float bounds=step(0,duv.x)*step(duv.x,1)*step(0,duv.y)*step(duv.y,1);
    float4 dragon=Texture2DSample(Dragon,DragonSampler,saturate(duv));
    stamp+=dragon.a*bounds*smoothstep(0,.12,duv.x)*(1-smoothstep(.86,1,duv.x));
}
float alpha=(inward+contact+core+stamp*sealLife*.27)*(1-smoothstep(170,220,radius));
float border=smoothstep(0,.035,UV.x)*(1-smoothstep(.965,1,UV.x))*smoothstep(0,.025,UV.y)*(1-smoothstep(.975,1,UV.y));
float3 color=lerp(float3(.53,.19,.025),float3(1,.69,.19),saturate(core*3+stamp*.35));
return float4(color*(1.5+Charge*.18),saturate(alpha)*border);
