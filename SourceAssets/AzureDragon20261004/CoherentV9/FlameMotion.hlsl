// Local offsets keep every tongue attached to the same hovering 3D vessel.
float t=saturate(Attr.g);
float seed=Attr.b*6.2831853;
float f=saturate(Fill);
float rootZ=Attr.r*60.-24.;
float lengthScale=.28+.72*f+Burst*.22;
float wave=sin(Age*(2.9+f*2.1)-t*5.2+seed);
float cross=sin(Age*2.1-t*7.3+seed*1.6);
float sway=t*t*(.32+.68*f);
return float3(wave*sway*.60,cross*sway*.70,(LocalPosition.z-rootZ)*(lengthScale-1.)+wave*sway*.28);
