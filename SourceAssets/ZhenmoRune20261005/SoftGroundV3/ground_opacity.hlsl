// One depth-tested surface, six mask taps total; no extra full-field layer.
float2 offset=World.xy-Center.xy;
float fieldR=length(offset)/max(Radius,1);
float sealRadius=min(500,Radius*.34);
float2 p=offset/max(sealRadius,1);
float sealR=length(p);
float2 uv=saturate(p*.5+.5);
float footprint=max(max(fwidth(uv.x),fwidth(uv.y)),.0025);
float2 d=float2(min(footprint*1.5,.009),0);
float core=Texture2DSample(Ink,InkSampler,uv).r;
float soft=(Texture2DSample(Ink,InkSampler,saturate(uv+d)).r
           +Texture2DSample(Ink,InkSampler,saturate(uv-d)).r
           +Texture2DSample(Ink,InkSampler,saturate(uv+d.yx)).r
           +Texture2DSample(Ink,InkSampler,saturate(uv-d.yx)).r)*.25;
float outer=Texture2DSample(Ink,InkSampler,saturate(offset/(2*max(Radius,1))+.5)).r;
float innerEdge=1-smoothstep(.84,1,sealR);
float outerEdge=1-smoothstep(.86,.995,fieldR);
float ink=(.74*core+.27*soft)*innerEdge;
float boundary=outer*.27*smoothstep(.32,.5,fieldR)*outerEdge;
float angle=atan2(p.y,p.x);
float sweep=pow(.5+.5*cos(angle-T*.28),8);
float pulse=.94+.06*sin(T*1.4-sealR*3);
// Approximate normal separation rather than raw view-depth distance. Grazing
// views must not classify a correctly lifted ground seal as floating in air.
float gap=max(0,GroundDepth-PixelDepth)*max(.04,abs(dot(normalize(SurfaceNormal),normalize(ViewDirection))));
float support=1-smoothstep(45,180,gap);
float nearFade=smoothstep(25,85,PixelDepth);
float coverage=saturate(ink+boundary)*Opacity*support*nearFade;
// A stable amber body supplies contrast on pale floors; warm moving highlights
// stay in the same draw and do not pulse the core opacity out of existence.
float3 gold=lerp(float3(1.18,.43,.065),float3(2.35,1.25,.26),saturate(core*.48+sweep*.4));
gold*=pulse*(1+.18*sweep);
return float4(gold,coverage);
