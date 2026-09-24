if(Pilot<=0) return float3(0,0,0);
float4 hits[8]={Hit0,Hit1,Hit2,Hit3,Hit4,Hit5,Hit6,Hit7};
// Height confines fountain hits to one basin. River uses w=0 (sloping ribbon).
float4 meta[8]={Meta0,Meta1,Meta2,Meta3,Meta4,Meta5,Meta6,Meta7};
float2 flowDirection=normalize(Flow.rg*2-1+float2(.00001,0));
float2 flowSide=float2(-flowDirection.y,flowDirection.x);
float pixelWidth=max(length(ddx(Position.xy)),length(ddy(Position.xy)));
float2 gradient=0;
float foam=0;
[unroll] for(int i=0;i<8;i++)
{
    float age=Clock-hits[i].z;
    if(age>0 && age<2.2 && hits[i].w>0)
    {
        if(meta[i].w>0 && abs(Position.z-meta[i].x)>meta[i].w)continue;
        float scale=meta[i].z>0?meta[i].z:1;
        float power=meta[i].y>0?meta[i].y:1;
        // Advect gently with the existing river flow, rather than a fixed decal.
        float2 delta=Position.xy-hits[i].xy-flowDirection*(Flow.b*160)*age*.28;
        // Uniform lifetime gate plus tight spatial gate: distant water pays no wave trig/exp.
        if(dot(delta,delta)>pow(245*max(.4,scale)+pixelWidth*2,2))continue;
        float stretch=1+min(age,.9)*.10;
        float2 local=float2(dot(delta,flowDirection)/stretch,dot(delta,flowSide));
        float distance=length(local);
        float2 radial=local/max(distance,1);
        float width=max(2.8+age*2.6,pixelWidth*.75);
        float radius=(5+age*105/(1+age*.14))*max(.4,scale);
        // A small changing distortion breaks perfect concentric circles.
        float variation=sin(radial.x*8+radial.y*5+hits[i].x*.009)*sin(radial.y*11-hits[i].y*.007);
        distance+=variation*min(age*3,2.5);
        float3 front=(distance-float3(radius,radius-18,radius-34))/width;
        float3 waves=exp(-front*front);
        float3 amplitudes=float3(1,.52*smoothstep(.10,.30,age),.25*smoothstep(.24,.48,age));
        float envelope=hits[i].w*smoothstep(0,.025,age)*(1-smoothstep(.65,2.2,age))/(1+age*.38);
        float slope=dot(-2*front*waves,amplitudes)*envelope*.36;
        float2 normalDirection=flowDirection*(radial.x/stretch)+flowSide*radial.y;
        gradient+=normalDirection*slope;
        // Only short-lived, broken foam. The lasting rings come from signed normals.
        float broken=.60+.40*sin(radial.x*17+radial.y*13+hits[i].y*.023);
        foam+=dot(waves,amplitudes)*envelope*broken*.38*(1-smoothstep(.35,1.2,age));
        foam+=exp(-distance*distance/225)*envelope*(1-smoothstep(.06,.30,age))*.55;
        // Two delayed cosmetic droplet returns per impact; no particle collision or CPU events.
        // Their offsets/delays vary per shot, while the original eight hit records stay bounded.
        float seed=frac(sin(dot(hits[i].xyz,float3(.017,.031,2.73)))*43758.5453);
        [unroll] for(int j=0;j<2;j++)
        {
            float random=frac(seed+j*.61803399);
            float fallAge=age-(.43+random*.20)*power;
            if(fallAge<=0 || fallAge>=.72)continue;
            float angle=random*6.2831853+j*2.2;
            float2 offset=float2(cos(angle),sin(angle))*(28+random*42)*power;
            float2 smallDelta=delta-offset;
            float d=length(smallDelta);
            float w=max(1.5+fallAge*1.8,pixelWidth*.8);
            float front=(d-(2+fallAge*52*max(.4,scale)))/w;
            float wave=exp(-front*front);
            float fade=smoothstep(0,.035,fallAge)*(1-smoothstep(.16,.72,fallAge))*hits[i].w;
            gradient+=smallDelta/max(d,1)*(-2*front*wave)*fade*.12;
            float broken=smoothstep(.28,.70,.5+.5*sin(smallDelta.x*.57+sin(smallDelta.y*.63)*2+seed*13));
            foam+=wave*fade*broken*.28*(1-smoothstep(.12,.40,fallAge));
        }
    }
}
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

// Many overlapping hits must not turn the water normals inside out.
gradient*=min(1,.45/max(length(gradient),.001));
return float3(gradient,saturate(foam))*Pilot*smoothstep(1,12,Depth);
