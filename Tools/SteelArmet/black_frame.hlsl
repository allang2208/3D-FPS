// Rounded horizontal aperture, measured in viewport-height units.
// Opaque black outside; a soft outward fade preserves the clear centre.
float aspect=max(Aspect,.1);
float2 p=(UV-float2(.5,CenterY)-Motion.xy)*float2(aspect,1.);
float c=cos(Motion.z),s=sin(Motion.z);
p=float2(c*p.x+s*p.y,-s*p.x+c*p.y);
float2 halfSize=float2(HalfWidth*aspect,HalfHeight);
float radius=min(CornerRadius,min(halfSize.x,halfSize.y));
float2 q=abs(p)-halfSize+radius;
float distanceToOpening=length(max(q,0.))+min(max(q.x,q.y),0.)-radius;
float feather=max(Feather,1.5*fwidth(distanceToOpening));
return smoothstep(0.,feather,distanceToOpening);
