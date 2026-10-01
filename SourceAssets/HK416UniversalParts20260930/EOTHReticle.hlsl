// Physical circle-dot glyph: no atlas mip loss, minimum pixel coverage.
float2 p=UV-.5;
float radius=length(p);
float pixel=max(length(ddx(p)),length(ddy(p)));
float aa=max(pixel*.5,1e-5);
float halfStroke=max(.0075,pixel*.60);
float dotRadius=max(.023,pixel*1.30);
float ring=abs(radius-.30)-halfStroke;
float dot=radius-dotRadius;
float tickX=max(abs(abs(p.x)-.354)-.029,abs(p.y)-halfStroke);
float tickY=max(abs(abs(p.y)-.354)-.029,abs(p.x)-halfStroke);
float distance=min(min(ring,dot),min(tickX,tickY));
float core=1-smoothstep(-aa,aa,distance);
float outline=1-smoothstep(-aa,aa,distance-max(pixel*.65,.003));
float centre=1-smoothstep(dotRadius,dotRadius+aa,radius);
return float3(core,outline,lerp(.85,1.15,centre));
