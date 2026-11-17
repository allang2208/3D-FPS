// Keep white heat confined to the hottest centre; preserve orange density folds.
float heat=saturate(Fields.g*.80+pow(saturate(Fields.r),.65)*.20);
float3 fire=lerp(float3(.42,.008,.0002),float3(1,.11,.004),smoothstep(.15,.58,heat));
fire=lerp(fire,float3(1,.40,.04),smoothstep(.60,.84,heat));
fire=lerp(fire,float3(1,.80,.38),smoothstep(.88,1,heat));
// W opts the crown/rolls into density contrast. The short white core uses W=0.
// Hot ridges stay luminous; cooler dense folds carry the body of the fireball.
float thickness=1-exp(-max(0,Fields.r)*2.0);
float foldShade=lerp(1,.58+.42*smoothstep(.58,.96,heat),thickness);
float bodyShade=lerp(1,foldShade,saturate(Dynamic.w));
return fire*(.8+4.2*heat*heat*heat)*bodyShade*max(0,Dynamic.z)*Tint;
