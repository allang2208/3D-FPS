// Four ordered cloth loops, 16 points each, in component space. Keep in sync
// with FFPSRobeHemEnvelope. No opacity cut and no moving-foot exclusion sphere.
if (Strength < 0.0001) return float3(0,0,0);
// The seam belongs to this vertex in the original bound model. Crossed feet
// cannot disable the other calf, and both sides of the ankle stay coincident.
float ankleBlend=smoothstep(Shape.x,Shape.x+Shape.z*.5,RestPosition.z);
if(ankleBlend<=.000001) return float3(0,0,0);
float3 v[64]={P0,P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11,P12,P13,P14,P15,
    P16,P17,P18,P19,P20,P21,P22,P23,P24,P25,P26,P27,P28,P29,P30,P31,
    P32,P33,P34,P35,P36,P37,P38,P39,P40,P41,P42,P43,P44,P45,P46,P47,
    P48,P49,P50,P51,P52,P53,P54,P55,P56,P57,P58,P59,P60,P61,P62,P63};
float3 center[4];float2 bounds[4];
[unroll] for(int ring=0;ring<4;++ring)
{
    center[ring]=0;bounds[ring]=float2(1e8,-1e8);
    [unroll] for(int i=0;i<16;++i)
    {
        float3 p=v[ring*16+i];center[ring]+=p/16;
        bounds[ring]=float2(min(bounds[ring].x,p.z),max(bounds[ring].y,p.z));
    }
}

float2 hemDelta=Position.xy-center[0].xy;
float2 hemDirection=hemDelta/max(length(hemDelta),.0001);
float hemRadius=1e8,hemHeight=center[0].z;
[unroll] for(int i=0;i<16;++i)
{
    float3 a=v[i],b=v[(i+1)%16];
    float2 edge=b.xy-a.xy,relative=a.xy-center[0].xy;
    float den=hemDirection.x*edge.y-hemDirection.y*edge.x;
    if(abs(den)>.00001)
    {
        float t=(relative.x*edge.y-relative.y*edge.x)/den;
        float u=(relative.x*hemDirection.y-relative.y*hemDirection.x)/den;
        if(t>0 && u>=0 && u<=1 && t<hemRadius)
        {hemRadius=t;hemHeight=lerp(a.z,b.z,u);}
    }
}
// Do not invent a hem across an open/folded contour. The original complete
// leg is the fallback, never a contraction to 70% of a guessed central radius.
if(hemRadius>1e7) return float3(0,0,0);
// Finish the transition BELOW the hem: partially blending above the cloth
// edge leaves the calf between the tucked target and its penetrating source.
float blend=smoothstep(hemHeight-2*Shape.y,hemHeight,Position.z)*ankleBlend;
if(blend<=.000001) return float3(0,0,0);

float2 origin=center[0].xy;
[unroll] for(int band=0;band<3;++band)
{
    float low=center[band].z,high=max(center[band+1].z,low+.001);
    if(Position.z>=low)origin=lerp(center[band].xy,center[band+1].xy,saturate((Position.z-low)/(high-low)));
}
float2 delta=Position.xy-origin;
float distance=max(length(delta),.0001),radius=1e8;
float2 direction=delta/distance;

// Skip whole height bands before the per-edge intersections. Normal upright
// poses visit one 32-triangle band; folds can intersect more than one band.
[loop] for(int band=0;band<3;++band)
{
    if(Position.z<min(bounds[band].x,bounds[band+1].x) ||
       Position.z>=max(bounds[band].y,bounds[band+1].y))continue;
    [loop] for(int i=0;i<16;++i)
    {
        int next=(i+1)%16;
        float3 a=v[band*16+i],b=v[band*16+next];
        float3 c=v[(band+1)*16+next],d=v[(band+1)*16+i];
        [unroll] for(int tri=0;tri<2;++tri)
        {
            float3 q[3]={a,tri==0?b:c,tri==0?c:d};
            if(Position.z<min(q[0].z,min(q[1].z,q[2].z)) ||
               Position.z>=max(q[0].z,max(q[1].z,q[2].z)))continue;
            float2 hit0=0,hit1=0;int count=0;
            [unroll] for(int e=0;e<3;++e)
            {
                float3 p=q[e],s=q[(e+1)%3];
                float za=p.z-Position.z,zb=s.z-Position.z;
                if((za<=0 && zb>0)||(zb<=0 && za>0))
                {
                    float2 hit=lerp(p.xy,s.xy,za/(za-zb));
                    if(count==0)hit0=hit;else hit1=hit;
                    ++count;
                }
            }
            if(count==2)
            {
                float2 edge=hit1-hit0,relative=hit0-origin;
                float den=direction.x*edge.y-direction.y*edge.x;
                if(abs(den)>.00001)
                {
                    float t=(relative.x*edge.y-relative.y*edge.x)/den;
                    float u=(relative.x*direction.y-relative.y*direction.x)/den;
                    if(t>0 && u>=0 && u<=1)radius=min(radius,t);
                }
            }
        }
    }
}
if(radius>1e7)
{
    // The short overlap just below the open hem uses that same hem contour.
    // Above/along a folded opening with no surface intersection, retain skin.
    if(Position.z>hemHeight) return float3(0,0,0);
    origin=center[0].xy;direction=hemDirection;distance=max(length(hemDelta),.0001);radius=hemRadius;
}
float2 tucked=origin+direction*min(distance,max(radius-Shape.y,0.));
return float3((tucked-Position.xy)*(blend*Strength),0);
