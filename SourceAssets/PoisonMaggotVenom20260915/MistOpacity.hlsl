struct VenomNoise {
float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float noise(float2 p) {
 float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
 return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
             lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
float fbm(float2 p) {return .57*noise(p)+.28*noise(p*2.07+5.3)+.15*noise(p*4.13+17.1);}
}; VenomNoise vn;

float2 p=(UV-.5)*2;
float2 q=p*2.5+float2(Variant*13+T*.09,Variant*7-T*.15);
float n=vn.fbm(q+float2(vn.noise(q+2),vn.noise(q+9))*.8);
float radius=length(p)+(.5-n)*.28;
return pow(saturate(1-radius),1.7)*smoothstep(.20,.78,n)*Alpha;

