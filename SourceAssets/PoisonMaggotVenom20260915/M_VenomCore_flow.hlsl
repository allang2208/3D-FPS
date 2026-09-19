struct VenomNoise {
float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float noise(float2 p) {
 float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
 return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
             lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
float fbm(float2 p) {return .57*noise(p)+.28*noise(p*2.07+5.3)+.15*noise(p*4.13+17.1);}
}; VenomNoise vn;

float2 p=UV*float2(5,3)+float2(T*.09,-T*.06);
return vn.fbm(p+float2(vn.noise(p*.8),vn.noise(p*.8+4))*.5);

