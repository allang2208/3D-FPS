struct VenomNoise {
float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float noise(float2 p) {
 float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
 return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
             lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
float fbm(float2 p) {return .57*noise(p)+.28*noise(p*2.07+5.3)+.15*noise(p*4.13+17.1);}
}; VenomNoise vn;

float2 p=(UV-.5)*2;float angle=atan2(p.y,p.x);
float boundary=.61+.09*sin(angle*5+.4)+.065*sin(angle*9-1.1);
float d=length(p)-boundary-(vn.fbm(p*8)-.5)*.10;
float coverage=1-smoothstep(-.015,.035,d);
for(int i=0;i<7;i++) {
 float a=float(i)*2.39996+.6;float2 center=float2(cos(a),sin(a))*(.68+.11*vn.hash(float2(i,2)));
 float r=.025+.04*vn.hash(float2(i,5));
 coverage=max(coverage,1-smoothstep(r*.65,r,length(p-center)));
}
return saturate(coverage)*Life*.82;

