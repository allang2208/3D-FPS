// Value noise and its analytic gradient: no texture fetches or ray marching.
// P is the undeformed sphere position / 50. The long axis is local X.
struct M14Noise
{
    float hash(float3 p)
    {
        p=frac(p*.1031);
        p+=dot(p,p.yzx+33.33);
        return frac((p.x+p.y)*p.z);
    }
    float4 field(float3 p)
    {
        float3 i=floor(p),f=frac(p);
        float3 w=f*f*(3-2*f),dw=6*f*(1-f);
        float a=hash(i),b=hash(i+float3(1,0,0));
        float c=hash(i+float3(0,1,0)),d=hash(i+float3(1,1,0));
        float e=hash(i+float3(0,0,1)),g=hash(i+float3(1,0,1));
        float h=hash(i+float3(0,1,1)),j=hash(i+float3(1,1,1));
        float z0=lerp(lerp(a,b,w.x),lerp(c,d,w.x),w.y);
        float z1=lerp(lerp(e,g,w.x),lerp(h,j,w.x),w.y);
        float dx=lerp(lerp(b-a,d-c,w.y),lerp(g-e,j-h,w.y),w.z)*dw.x;
        float dy=lerp(lerp(c-a,d-b,w.x),lerp(h-e,j-g,w.x),w.z)*dw.y;
        return float4(lerp(z0,z1,w.z),dx,dy,(z1-z0)*dw.z);
    }
};
M14Noise n;
float3 offset=float3(Seed*17.3,Seed*29.1,Seed*11.7);
// Slow advection down the stretched filament, not a synchronized sine pulse.
float3 q=P*float3(1.7,3.6,3.6)+offset-float3(Clock*.31,Clock*.043,-Clock*.027);
float4 broad=n.field(q);
float4 fine=n.field(q*2.31+float3(7.1,-3.2,8.4)+broad.x*.43);
float density=saturate(broad.x*.76+fine.x*.24);
float2 slope=-(broad.zw*.052+fine.zw*.024);
// Sparse isolated inclusions. Each cell has a stable size and occupancy.
float3 cellP=q*2.1,cell=floor(cellP);
float pick=n.hash(cell+41.7);
float3 center=.28+.44*float3(n.hash(cell+3.7),n.hash(cell+17.2),n.hash(cell+8.4));
float radius=lerp(.055,.16,n.hash(cell+31.4));
float dist=length(frac(cellP)-center);
float aa=max(fwidth(dist),.018);
float bubble=(1-smoothstep(radius-aa,radius+aa,dist))*step(.91,pick);
return float4(slope,density,bubble);
