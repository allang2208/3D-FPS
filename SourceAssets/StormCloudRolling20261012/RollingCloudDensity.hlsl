// Derived from HundredEyedSlag / SmokeVisibilityFixV21 / PersistentBodySmoke.
// Same Mantaflow R-density atlas as M10's local gas, with a storm hold clock.
// Age is connected to Material Time here, independent of the spell's lifetime.
float clock=Age*(.34+Seed*.13)+Seed*6.2831853;
float2 p=UV-.5;
float turn=(Seed-.5)*1.3+sin(clock*.63)*.14;
float cs=cos(turn),sn=sin(turn);
p=mul(float2x2(cs,-sn,sn,cs),p);
p/=1+.045*sin(clock*.81+Seed*4.0);
p+=float2(sin(p.y*9+clock*1.2+Seed*11),cos(p.x*8-clock*.94+Seed*7))*.023;
float2 q=p+.5;
q.x=lerp(q.x,1-q.x,step(.5,Seed));
// Smoothly traverse the dense section; every lobe has a separate phase.
// Never enter the impact bake's dissipated tail during a long spell.
float phase=.5-.5*cos(clock*.72);
float frame=(.035+phase*.45)*63;
float first=floor(frame),second=min(first+1,63);
float2 safeUV=clamp(q,float2(.5/256,.5/256),float2(255.5/256,255.5/256));
float2 tileA=float2(fmod(first,8),floor(first/8));
float2 tileB=float2(fmod(second,8),floor(second/8));
float a=Texture2DSampleLevel(Atlas,AtlasSampler,(tileA+safeUV)/8,0).r;
float b=Texture2DSampleLevel(Atlas,AtlasSampler,(tileB+safeUV)/8,0).r;
float density=lerp(a,b,frac(frame));
float edge=min(min(UV.x,1-UV.x),min(UV.y,1-UV.y));
float sampleEdge=min(min(q.x,1-q.x),min(q.y,1-q.y));
float border=smoothstep(.012,.085,edge)*smoothstep(.012,.075,sampleEdge);
float radial=1-smoothstep(.76,1.01,length((UV-.5)*2));
float coverage=1-exp(-max(0,density-.002)*6.8);
return saturate(coverage*border*radial*Alpha);
