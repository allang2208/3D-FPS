// Four independent moving wake records. Gun-hit rings retain all eight slots.
float4 wakeHeads[4]={Wake0,Wake1,Wake2,Wake3};
float4 wakeMotion[4]={WakeMotion0,WakeMotion1,WakeMotion2,WakeMotion3};
[unroll] for(int w=0;w<4;++w)
{
    float age=Clock-wakeMotion[w].w;
    if(age<0||age>.65||wakeMotion[w].z<=0)continue;
    if(abs(Position.z-wakeHeads[w].z)>24)continue;
    float2 direction=normalize(wakeMotion[w].xy+float2(.00001,0));
    float2 side=float2(-direction.y,direction.x);
    float speed=wakeMotion[w].z;
    float2 delta=Position.xy-wakeHeads[w].xy-direction*(speed*650*min(age,.10));
    float behind=-dot(delta,direction),across=dot(delta,side);
    float lengthWake=65+speed*150;
    if(behind< -15||behind>lengthWake||abs(across)>wakeHeads[w].w+lengthWake*.3)continue;
    float halfWidth=wakeHeads[w].w+max(0,behind)*.22;
    float width=max(3,pixelWidth);
    float front=(abs(across)-halfWidth)/width;
    float envelope=smoothstep(-15,10,behind)*(1-smoothstep(lengthWake*.35,lengthWake,behind))
        *(1-smoothstep(.16,.65,age))*speed;
    float wave=exp(-front*front);
    gradient+=side*sign(across)*(-2*front*wave)*envelope*.15;
    float center=exp(-pow(across/max(8,wakeHeads[w].w),2));
    foam+=(wave*.16+center*.035)*envelope*(.72+.28*sin(behind*.15+Clock*3));
}
