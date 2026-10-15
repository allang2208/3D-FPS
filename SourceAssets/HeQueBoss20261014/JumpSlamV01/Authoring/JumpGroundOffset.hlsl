float3 up=normalize(Up);
float3 delta=Position-Center;
float3 radial=normalize(delta-up*dot(delta,up));
float width=min(55.,Radius*.8);
return radial*(UV.y-.5)*(width-Radius*.02);
