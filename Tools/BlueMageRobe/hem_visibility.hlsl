// Actual inner-layer coverage, in the same component space as the cloth.
// WPO remains a secondary fit; it cannot by itself suppress a protruding face.
if(Strength<.0001) return 1.;
float ankleBlend=smoothstep(Shape.x,Shape.x+Shape.z*.5,RestPosition.z);
if(ankleBlend<=.000001) return 1.;
float3 hem[16]={P0,P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11,P12,P13,P14,P15};
float3 center=0;float highest=-1e8;
[unroll] for(int i=0;i<16;++i){center+=hem[i]/16.;highest=max(highest,hem[i].z);}
float2 delta=Position.xy-center.xy;
float2 direction=delta/max(length(delta),.0001);
float localHeight=-1e8;
[unroll] for(int i=0;i<16;++i)
{
    float3 a=hem[i],b=hem[(i+1)%16];
    float2 edge=b.xy-a.xy,relative=a.xy-center.xy;
    float den=direction.x*edge.y-direction.y*edge.x;
    if(abs(den)>.00001)
    {
        float t=(relative.x*edge.y-relative.y*edge.x)/den;
        float u=(relative.x*direction.y-relative.y*direction.x)/den;
        if(t>0 && u>=0 && u<=1)localHeight=max(localHeight,lerp(a.z,b.z,u));
    }
}
// A folded hem may have several intersections, or no projected intersection.
// Use its highest opening rather than cutting away an exposed calf below it.
if(localHeight<-1e7)localHeight=highest;
float overlap=max(Shape.z,1.);
float keep=1-smoothstep(localHeight+overlap,localHeight+overlap+max(Shape.y,.25),Position.z);
return lerp(1.,keep,saturate(Strength)*ankleBlend);
