// Original Mantaflow density is stored in R, not the opaque texture alpha.
// Two adjacent 8x8 frames, with independent zero-coverage sprite borders.
float age=saturate(Age);
float2 p=UV-.5;
float turn=(Seed-.5)*.32+sin(age*3.1+Seed*6.283185)*.075;
float cs=cos(turn),sn=sin(turn);
p=mul(float2x2(cs,-sn,sn,cs),p);
p+=float2(sin(p.y*10+age*3+Seed*11),cos(p.x*9-age*2.6+Seed*7))*.019;
float2 q=p+.5;
q.x=lerp(q.x,1-q.x,step(.5,Seed));
float frame=min(62.99,(.035+age*.965)*63);
float first=floor(frame),second=min(first+1,63);
float2 safeUV=clamp(q,float2(.5/256,.5/256),float2(255.5/256,255.5/256));
float2 tileA=float2(fmod(first,8),floor(first/8));
float2 tileB=float2(fmod(second,8),floor(second/8));
float a=Texture2DSampleLevel(Atlas,AtlasSampler,(tileA+safeUV)/8,0).r;
float b=Texture2DSampleLevel(Atlas,AtlasSampler,(tileB+safeUV)/8,0).r;
float density=lerp(a,b,frac(frame));
float edge=min(min(UV.x,1-UV.x),min(UV.y,1-UV.y));
float sampleEdge=min(min(q.x,1-q.x),min(q.y,1-q.y));
float border=smoothstep(.012,.09,edge)*smoothstep(.012,.07,sampleEdge);
float radial=1-smoothstep(.72,1.02,length((UV-.5)*2));
float erosion=lerp(.004,.07,smoothstep(.5,1,age));
float coverage=smoothstep(erosion,erosion+.40,density);
return saturate(coverage*border*radial*Alpha);
