// Irregular branching fractures, chipped bright edges and a compact impact scar.
// Native material code; no generated image or permanent geometry deformation.
struct Fracture
{
    float hash(float x) { return frac(sin(x*127.1+Seed*73.19)*43758.5453); }
    float segment(float2 p,float2 a,float2 b)
    {
        float2 d=b-a;
        return length(p-(a+d*saturate(dot(p-a,d)/max(dot(d,d),.00001))));
    }
    float Seed;
};
Fracture f;f.Seed=Seed;
float2 p=(UV-.5)*2;
float cs=cos(Seed*6.283185),sn=sin(Seed*6.283185);
p=mul(float2x2(cs,-sn,sn,cs),p);
float dist=10,wide=10;
[unroll] for(int i=0;i<9;++i)
{
    float angle=(i+.6*f.hash(i+1))*6.283185/9;
    float2 dir=float2(cos(angle),sin(angle)),side=float2(-dir.y,dir.x);
    float reach=lerp(.48,.91,f.hash(i+20));
    float2 a=dir*.035;
    [unroll] for(int j=1;j<=4;++j)
    {
        float2 b=dir*(reach*j/4)+side*(f.hash(i*5+j+32)-.5)*.17;
        float d=f.segment(p,a,b);
        dist=min(dist,d);wide=min(wide,d/(1.4-.20*j));
        if(j==2||j==3)
        {
            float sign=f.hash(i+j+71)>.5?1:-1;
            float2 tip=b+dir*.11+side*sign*(.10+.08*f.hash(i+j+53));
            dist=min(dist,f.segment(p,b,tip)*1.6);
        }
        a=b;
    }
}
float grain=f.hash(dot(floor(p*110),float2(1,163)));
float width=.0035+grain*.003;
float crack=1-smoothstep(width,width+.0035,dist);
float rim=(1-smoothstep(.014,.026,wide))*(1-crack);
float scar=(1-smoothstep(.04,.125,length(p*float2(.8,1.3))))*(.35+.45*grain);
float edge=1-smoothstep(.84,.98,length(p));
float grow=smoothstep(0,.06,Age)*(1-smoothstep(saturate(Age/.18),saturate(Age/.18)+.05,length(p)));
float fade=1-smoothstep(3.3,5.0,Age);
return float3(saturate(crack*.88+rim*.36+scar)*edge*grow*fade,crack,rim);
