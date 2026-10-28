// Discrete sparks travel on the exact retained helix (radius/pitch/turns/rotation).
// Invert its two projected halves and evaluate only adjacent particles per pixel.
// Two narrow, staggered lanes share the old ribbon centreline; no solid rails or glyphs.
float sR=(HudCenter-P.x)/HudRibbon.x;
float sC=clamp(sR,-.999,.999);
float phi=Age*.45;
float amax=TwoPi*HudRibbonTurns;
float helixPitch=HudRibbon.y/TwoPi;
float particleStep=amax/156.0;
float particleTravel=Age*.62;
float pixelFootprint=max(length(ddx(P)),length(ddy(P)));
float helixLight=0.0;
float helixParticleCoverage=0.0;
float helixBounds=Fn.SS(HudRibbon.x+24.0,HudRibbon.x+14.0,abs(P.x-HudCenter));
[unroll] for(int side=0;side<2;++side)
{
    float thetaGuess=side==0?asin(sC):3.14159265-asin(sC);
    float a0=thetaGuess-phi;
    float turn=round(((P.y-HudRibbon.w)/helixPitch-a0)/TwoPi);
    float closest=a0+TwoPi*turn;
    float2 curvePoint=float2(HudCenter-HudRibbon.x*sin(closest+phi),HudRibbon.w+helixPitch*closest);
    float2 curveSlope=float2(-HudRibbon.x*cos(closest+phi),helixPitch);
    // Refine near the silhouette where inverse-sine alone loses the band width.
    closest+=clamp(dot(P-curvePoint,curveSlope)/max(dot(curveSlope,curveSlope),1.0),-.28,.28);
    [unroll] for(int lane=0;lane<2;++lane)
    {
        float cell=floor((closest+particleTravel)/particleStep-lane*.5);
        [unroll] for(int neighbor=-1;neighbor<=1;++neighbor)
        {
            float id=cell+neighbor;
            float seed=Fn.Hash(id*73.173+lane*117.79+3.1);
            float variant=Fn.Hash(id*19.419+lane*47.21+8.0);
            float alpha=(id+lane*.5+(seed-.5)*.18)*particleStep-particleTravel;
            float theta=alpha+phi;
            float face=step(0.0,cos(theta));
            float belongs=side==0?face:1.0-face;
            float edgeFade=Fn.SS(0.0,.38,alpha)*Fn.SS(amax,amax-.38,alpha);
            float radius=HudRibbon.x+(lane==0?-4.0:4.0)+2.0*sin(Age*.83+seed*TwoPi);
            float2 pos=float2(HudCenter-radius*sin(theta),HudRibbon.w+helixPitch*alpha);
            pos.y+=2.8*sin(Age*.91+variant*TwoPi);
            float2 velocity=normalize(float2(radius*cos(theta)*(.62-.45),-helixPitch*.62));
            float2 delta=P-pos;
            float longitudinal=dot(delta,velocity);
            float lateral=dot(delta,float2(-velocity.y,velocity.x));
            float size=max(1.8+variant*1.8,pixelFootprint*.65);
            float core=exp(-dot(delta,delta)/(size*size));
            float halo=exp(-dot(delta,delta)/(size*size*7.0))*.14;
            float tailLength=4.5+seed*4.0;
            float tailPosition=(longitudinal+tailLength*.5)/tailLength;
            float tail=exp(-lateral*lateral/(size*size*.8)
                -tailPosition*tailPosition)*.24;
            float depth=lerp(.42*(1.0-.60*sil),1.0,face);
            float breath=.76+.24*sin(Age*(1.1+variant*.6)+seed*TwoPi);
            float visible=belongs*edgeFade*depth*helixBounds;
            float gain=visible*breath*(.74+.28*fillV+.18*Pulse+.30*Burst);
            helixLight+=(core+halo+tail)*gain;
            helixParticleCoverage=max(helixParticleCoverage,saturate((core*.82+tail*.35)*visible));
        }
    }
}
col+=helixLight*float3(.60,.97,1.0);
