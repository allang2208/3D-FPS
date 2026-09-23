// Centimeter-scale surface detail in the undeformed mesh's local coordinates.
// Sparse shallow marks affect coating reflectance; structural normals survive.
struct FinishNoise
{
    float hash(float3 p)
    {
        p=frac(p*.1031);p+=dot(p,p.yzx+33.33);
        return frac((p.x+p.y)*p.z);
    }
    float noise(float3 p)
    {
        float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),
                         lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y),
                    lerp(lerp(hash(i+float3(0,0,1)),hash(i+float3(1,0,1)),f.x),
                         lerp(hash(i+float3(0,1,1)),hash(i+float3(1,1,1)),f.x),f.y),f.z);
    }
    float marks(float2 uv,float seed)
    {
        float value=0;
        [unroll] for(int layer=0;layer<2;++layer)
        {
            float2 q=uv/(layer==0?1.8:2.8);
            float2 id=floor(q),p=frac(q)-.5;
            float3 h=float3(hash(float3(id,seed+layer*17)),hash(float3(id,seed+3+layer*17)),hash(float3(id,seed+9+layer*17)));
            float angle=(h.y-.5)*(layer==0?.7:2.5);
            float2 d=float2(cos(angle),sin(angle));
            float2 v=float2(dot(p,d),dot(p,float2(-d.y,d.x)));
            v.y-=(h.z-.5)*.36;
            float width=lerp(.002,.004,h.z),len=lerp(.06,.28,h.y);
            float aa=max(length(fwidth(q)),.0002);
            float stroke=1-smoothstep(width,width+aa,abs(v.y));
            float ends=1-smoothstep(len*.70,len+aa,abs(v.x));
            value=max(value,stroke*ends*step(layer==0?.67:.82,h.x)*min(1.,width/aa));
        }
        return value;
    }
};
FinishNoise f;
float3 weights=pow(abs(normalize(N)),float3(6,6,6));
weights/=max(dot(weights,float3(1,1,1)),.0001);
float scratch=dot(weights,float3(f.marks(P.yz,2),f.marks(P.xz,11),f.marks(P.xy,23)));
float footprint=max(length(ddx(P)),length(ddy(P)));
float grain=lerp(.5,f.noise(P*16.0+31),1-saturate(footprint*16.0));
return float4(saturate(scratch),f.noise(P*.65),smoothstep(.50,.82,f.noise(P*.23+7)),grain);
