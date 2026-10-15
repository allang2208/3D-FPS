float3 up=normalize(Up);
float3 delta=Position-Center;
float3 radial=normalize(delta-up*dot(delta,up));
float width=min(85.,Radius*.85);
// Keep the outside of the visible crest on the gameplay radius. Extra width
// grows into the wake, rather than appearing beyond the damaging front.
return radial*((UV.y-1)*width-(UV.y-.5)*Radius*.02);
