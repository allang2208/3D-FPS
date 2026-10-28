// Frost Raven: one sapphire-glass eagle and vessel; no silver collar or separate socket.
float iceLum=max(col.r,max(col.g,col.b));
col=iceLum*float3(.22,.66,1.0);

// Keep the charge divisions on the glass beneath the integral crystal throat.
float division=frac((P.y-HudTopBoundary)/(HudBottomBoundary-HudTopBoundary)*8.0);
float seam=(1-Fn.SS(.016,.045,min(division,1-division)))*inner*zone;
col*=1-seam*.34;

// CROWN_PROJECTION
float headInside=step(0,headUV.x)*step(headUV.x,1)*step(0,headUV.y)*step(headUV.y,1);
float4 head=Texture2DSample(WolfHeadTex,WolfHeadTexSampler,saturate(headUV));
// The original image's sculpted volume remains; its short glass root blends into the column.
float rootBlend=Fn.SS(478.0,533.0,P.y);
float rootFade=1.0-Fn.SS(520.0,540.0,P.y);
float headOpacity=head.a*headInside*rootFade*saturate(BodyOpacity*1.15);
// Tint specular facets as blue glass instead of leaving chrome-white borders.
float3 headColor=head.rgb*lerp(float3(.38,.82,1.0),float3(.22,.66,1.0),rootBlend);
headColor*=.84+.06*fillV+.08*Pulse+.10*Burst;
float blueVein=saturate(head.b-max(head.r,head.g*.75));
headColor+=blueVein*float3(.01,.055,.085)*(fillV*.4+Pulse*.3+Burst*.4);
col=col*(1.0-headOpacity)+headColor*headOpacity;
