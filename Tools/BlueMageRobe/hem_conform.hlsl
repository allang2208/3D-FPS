// Current cloth samples in the shared body component space. Intersect the
// connecting surface at the vertex's height BEFORE clamping its radius.
if (Strength < 0.0001) return float3(0,0,0);
float3 v[24] = {P0,P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11,
                P12,P13,P14,P15,P16,P17,P18,P19,P20,P21,P22,P23};
float3 center[3];
[unroll] for(int ring=0;ring<3;++ring)
{
    center[ring]=0;
    [unroll] for(int i=0;i<8;++i) center[ring]+=v[ring*8+i]/8;
}

// Directional hem height keeps exposed calf/foot geometry and the existing
// smooth overlap. The ankle seam on both material sections stays fixed.
float2 hemDelta=Position.xy-center[0].xy;
float2 hemDirection=hemDelta/max(length(hemDelta),.0001);
float hemRadius=1e8,hemHeight=center[0].z;
[unroll] for(int i=0;i<8;++i)
{
    float3 a=v[i],b=v[(i+1)%8];
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
float blend=smoothstep(hemHeight-Shape.y,hemHeight+Shape.z,Position.z);
float ankleDistance=min(length(Position-FootL),length(Position-FootR));
blend*=smoothstep(Shape.x,Shape.x+Shape.z,ankleDistance);
if(blend<=.000001) return float3(0,0,0);

float z1=max(center[1].z,center[0].z+.001);
float z2=max(center[2].z,z1+.001);
float2 origin=Position.z<z1
    ?lerp(center[0].xy,center[1].xy,saturate((Position.z-center[0].z)/(z1-center[0].z)))
    :lerp(center[1].xy,center[2].xy,saturate((Position.z-z1)/(z2-z1)));
float2 delta=Position.xy-origin;
float distance=max(length(delta),.0001);
float2 direction=delta/distance;
float radius=1e8;

// Two triangle strips join the three loops. A twisted quad is not planar:
// keep its diagonal so a cross-section cannot cut across the folded surface.
// This is a fixed 32-triangle envelope, not a full-mesh traversal.
[unroll] for(int band=0;band<2;++band)
[unroll] for(int i=0;i<8;++i)
{
    int next=(i+1)%8;
    float3 a=v[band*8+i],b=v[band*8+next];
    float3 c=v[(band+1)*8+next],d=v[(band+1)*8+i];
    [unroll] for(int tri=0;tri<2;++tri)
    {
        float3 q[3]={a,tri==0?b:c,tri==0?c:d};
        if(Position.z<min(q[0].z,min(q[1].z,q[2].z)) ||
           Position.z>=max(q[0].z,max(q[1].z,q[2].z)))continue;
        float2 hit0=0,hit1=0;
        int count=0;
        [unroll] for(int e=0;e<3;++e)
        {
            float3 p=q[e],s=q[(e+1)%3];
            float za=p.z-Position.z,zb=s.z-Position.z;
            // Half-open edges avoid counting a plane/vertex contact twice.
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
// At an open boundary use that boundary's contour. Do not mix independently
// clamped radii from different heights as the old shader did.
if(radius>1e7)
{
    int ring=abs(Position.z-center[0].z)<abs(Position.z-center[2].z)?0:2;
    origin=center[ring].xy;delta=Position.xy-origin;distance=max(length(delta),.0001);direction=delta/distance;
    float fallback=1e8;
    [unroll] for(int i=0;i<8;++i)
    {
        float2 a=v[ring*8+i].xy,b=v[ring*8+(i+1)%8].xy;
        float2 edge=b-a,relative=a-origin;
        fallback=min(fallback,length(relative)*.70);
        float den=direction.x*edge.y-direction.y*edge.x;
        if(abs(den)>.00001)
        {
            float t=(relative.x*edge.y-relative.y*edge.x)/den;
            float u=(relative.x*direction.y-relative.y*direction.x)/den;
            if(t>0 && u>=0 && u<=1)radius=min(radius,t);
        }
    }
    if(radius>1e7)radius=fallback;
}
float2 tucked=origin+direction*min(distance,max(radius-Shape.y,0.));
return float3((tucked-Position.xy)*(blend*Strength),0);
