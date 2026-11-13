// Radian geometry, not arbitrary distances on a screen overlay. 1 mrad stays
// 1 mrad throughout the zoom transition. Fine ticks/labels cull by pixel size.
struct Marks
{
    float segment(float2 p,float2 a,float2 b)
    {float2 v=b-a;return length(p-a-v*saturate(dot(p-a,v)/max(dot(v,v),1e-6)));}
    float coverage(float d,float width,float px)
    {return 1-smoothstep(width-px*.45,width+px*.45,d);}
    float2 glyph(float2 p,float2 at,int digit,float px,Texture2D tex,SamplerState samp)
    {
        float2 q=(p-at)/(float2(5.5,8.5)*px)+.5;
        float inside=step(0,q.x)*step(q.x,1)*step(0,q.y)*step(q.y,1);
        return Texture2DSample(tex,samp,float2((saturate(q.x)+digit)/16,saturate(q.y))).rg*inside;
    }
    float2 number(float2 p,float2 at,int n,float px,Texture2D tex,SamplerState samp)
    {
        if(n<10)return glyph(p,at,n,px,tex,samp);
        return max(glyph(p,at-float2(3.2*px,0),n/10,px,tex,samp),glyph(p,at+float2(3.2*px,0),n%10,px,tex,samp));
    }
};
Marks m;
float2 uv=.5+(ScreenUV-.5)*ScreenToLens.xy;
float3 scene=Texture2DSample(Scene,SceneSampler,saturate(uv)).rgb;
float2 p=atan((uv-.5)*(2*CaptureTanHalfFOV))*1000;
float px=max(max(fwidth(p.x),fwidth(p.y)),.001);
float stroke=px*.42,d=1e4,lit=0;
float2 labels=0;
int style=(int)(ReticleStyle+.5);
float ppm=1/px;
float tickStep=ppm>=7?.5:ppm>=3?1:ppm>=1.5?2:5;
float labelStep=ppm>=5?2:ppm>=2.5?4:10;
float labelVisibility=smoothstep(1.7,2.5,ppm);

if(style==0||style==3||style==5) // M24 precision / KV open centre / handgun duplex.
{
    float gap=style==3?max(.45,px*2):style==0?px*1.3:0;
    d=min(d,m.segment(p,float2(-35,0),float2(-gap,0)));
    d=min(d,m.segment(p,float2(gap,0),float2(35,0)));
    d=min(d,m.segment(p,float2(0,-35),float2(0,-gap)));
    d=min(d,m.segment(p,float2(0,gap),float2(0,35)));
    if(style==5&&max(abs(p.x),abs(p.y))>12)stroke=px*1.15;
    if(style==3)lit=m.coverage(length(p),max(.12,px*.8),px);
    if(style==0)d=min(d,max(0,length(p)-px*.25));
}
else if(style==1) // LPVO: open-bottom horseshoe with an illuminated centre dot.
{
    float ring=abs(length(p)-6.0);
    if(p.y<3.5)d=min(d,ring);
    lit=max(m.coverage(length(p),max(.18,px*.9),px),m.coverage(ring,max(.11,px*.65),px)*step(p.y,3.5)*.65);
    d=min(d,m.segment(p,float2(0,2),float2(0,14)));
}
else if(style==2||style==4) // Prism / PSO: the primary chevron TIP is the aim ray.
{
    float w=style==2?1.5:1.1,h=style==2?1.6:1.0;
    d=min(m.segment(p,float2(-w,h),float2(0,0)),m.segment(p,float2(0,0),float2(w,h)));
    lit=m.coverage(d,max(px*.7,.06),px);
    if(style==4)
    {
        [unroll]for(int i=1;i<=3;++i)
        {
            float y=i*2.;
            d=min(d,m.segment(p,float2(-.75,y+.7),float2(0,y)));
            d=min(d,m.segment(p,float2(0,y),float2(.75,y+.7)));
        }
        d=min(d,m.segment(p,float2(-12,0),float2(-2.5,0)));
        d=min(d,m.segment(p,float2(2.5,0),float2(12,0)));
        // Stadia: reference height 1.7 m, range labels in hundreds of metres.
        // This is geometric ranging; it does not claim ammo-specific zeroing.
        d=min(d,m.segment(p,float2(-22,23),float2(-6,23)));
        [unroll]for(int i=0;i<8;++i)
        {
            float2 a=float2(-22+i*2,23-1700./(200+i*100));
            float2 b=float2(-20+i*2,23-1700./(300+i*100));
            d=min(d,m.segment(p,a,b));
            if(i%2==0)labels=max(labels,m.number(p,a-float2(0,6*px),2+i,px,Glyphs,GlyphsSampler)*labelVisibility);
        }
        labels=max(labels,m.number(p,float2(-6,23-1.7-6*px),10,px,Glyphs,GlyphsSampler)*labelVisibility);
        labels=max(labels,m.glyph(p,float2(-22,23+7*px),1,px,Glyphs,GlyphsSampler)*labelVisibility);
        labels=max(labels,m.glyph(p,float2(-22+6*px,23+7*px),10,px,Glyphs,GlyphsSampler)*labelVisibility);
        labels=max(labels,m.glyph(p,float2(-22+12*px,23+7*px),7,px,Glyphs,GlyphsSampler)*labelVisibility);
    }
}
else if(style==7) // Peakwatch: fine mountain-tip aim and angular hold references.
{
    // Tip is the unchanged camera aim ray. These marks are mrad references,
    // not distance labels or an assumed arrow-specific ballistic zero.
    d=min(d,m.segment(p,float2(-1.4,1.6),float2(0,0)));
    d=min(d,m.segment(p,float2(0,0),float2(1.4,1.6)));
    d=min(d,m.segment(p,float2(-12,0),float2(-3,0)));
    d=min(d,m.segment(p,float2(3,0),float2(12,0)));
    d=min(d,m.segment(p,float2(0,2.8),float2(0,12)));
    // Preserve the bow's draw/full/perfect/piercing cues inside its lens.
    // Normal HUD remains the authoritative, fully legible feedback display.
    if(BowDrawState.r>.01)
    {
        float x=lerp(8,3,saturate(BowDrawState.r));
        float cue=min(m.segment(p,float2(-x,-1),float2(-x,1)),m.segment(p,float2(x,-1),float2(x,1)));
        lit=max(lit,m.coverage(cue,px*.7,px)*BowDrawState.r*.6);
    }
    lit=max(lit,m.coverage(d,max(.04,px*.55),px)*saturate(BowDrawState.g*.25+BowDrawState.b*.75));
    if(BowDrawState.a>.01)
    {
        float pierce=min(m.segment(p,float2(-1,-2),float2(0,-3)),m.segment(p,float2(0,-3),float2(1,-2)));
        lit=max(lit,m.coverage(pierce,px*.65,px)*BowDrawState.a);
    }
    lit=max(lit,m.coverage(abs(length(p)-lerp(2,4,1-BowRelease)),px*.5,px)*BowRelease*.5);
}
else // Thermal: open central cross, square acquisition corners and mil ladder.
{
    float gap=max(.4,2*px);
    d=min(d,m.segment(p,float2(-4,0),float2(-gap,0)));
    d=min(d,m.segment(p,float2(gap,0),float2(4,0)));
    d=min(d,m.segment(p,float2(0,-4),float2(0,-gap)));
    d=min(d,m.segment(p,float2(0,gap),float2(0,4)));
    [unroll]for(int x=-1;x<=1;x+=2)[unroll]for(int y=-1;y<=1;y+=2)
    {
        d=min(d,m.segment(p,float2(x*9,y*12),float2(x*12,y*12)));
        d=min(d,m.segment(p,float2(x*12,y*12),float2(x*12,y*9)));
    }
    lit=m.coverage(length(p),px*.7,px);
}

// Angular graduations share calibration but retain the optic's own layout.
[unroll]for(int i=1;i<=20;++i)
{
    float a=i*.5;
    bool visible=abs(a/tickStep-round(a/tickStep))<.01;
    bool major=abs(a/labelStep-round(a/labelStep))<.01;
    float len=px*(major?3.1:1.65);
    if(style==5){visible=(i%8==0);major=visible;}
    if(style==1||style==2||style==6||style==7){visible=(i%4==0);major=visible&&major;}
    if(style==4){visible=i%2==0&&a>=3;major=i%10==0;}
    if(visible)
    {
        if(style==0||style==3||style==4||style==5)
        {
            [unroll]for(int s=-1;s<=1;s+=2)d=min(d,m.segment(p,float2(s*a,-len),float2(s*a,len)));
        }
        if(style!=4)d=min(d,m.segment(p,float2(-len,a),float2(len,a)));
        if(style==0||style==5)d=min(d,m.segment(p,float2(-len,-a),float2(len,-a)));
        if(major&&style!=4)
        {
            labels=max(labels,m.number(p,float2(len+6*px,a),(int)a,px,Glyphs,GlyphsSampler)*labelVisibility);
            if(style==0||style==3)labels=max(labels,m.number(p,float2(a,-8*px),(int)a,px,Glyphs,GlyphsSampler)*labelVisibility);
        }
        if(major&&style==4)
        {
            labels=max(labels,m.number(p,float2(a,-8*px),(int)a,px,Glyphs,GlyphsSampler)*labelVisibility);
            labels=max(labels,m.number(p,float2(-a,-8*px),(int)a,px,Glyphs,GlyphsSampler)*labelVisibility);
        }
    }
    // KV wind-hold dots: sparse two-mil rows, not the LPVO's horseshoe.
    if(style==3&&i%4==0&&i>=8)
    {
        [unroll]for(int s=-1;s<=1;s+=2)[unroll]for(int col=1;col<=3;++col)
            d=min(d,max(0,length(p-float2(s*col*2,a))-px*.45));
    }
}
// A small unit legend belongs to the image, never to the surrounding HUD.
float2 legend=atan(CaptureTanHalfFOV*float2(.35,.62))*1000;
float legendVisibility=smoothstep(42,70,1000*CaptureTanHalfFOV/px);
[unroll]for(int j=0;j<4;++j)
    labels=max(labels,m.glyph(p,legend+float2((j-1.5)*6.4*px,0),11+j,px,Glyphs,GlyphsSampler)*legendVisibility);
float ink=max(m.coverage(d,stroke,px),labels.r);
float halo=max(m.coverage(d,stroke+px*.95,px),labels.g);
scene*=float3(.985,.995,1.0);
scene=lerp(scene,float3(.72,.77,.72),halo*.8);
float3 etched=style==6?float3(.42,.95,.72):float3(.003,.004,.003);
scene=lerp(scene,etched,ink*.97);
float3 illumination=style==2?float3(.95,.22,.025):style==6?float3(.45,1,.76):float3(.85,.028,.012);
if(style==7)illumination=lerp(float3(.82,.67,.35),float3(.55,.92,.78),saturate(BowDrawState.b+BowDrawState.a));
return lerp(scene,illumination,lit*.9);
