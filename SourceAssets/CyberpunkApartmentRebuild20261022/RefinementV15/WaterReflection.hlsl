// Apartment-local deterministic reflection supplement, metres throughout.
float3 pos=Position*.01,cam=Camera*.01;
float3 N=normalize(lerp(float3(0,0,1),normalize(WaterNormal),NormalWeight));
float3 ray=reflect(normalize(pos-cam),N);
float3 dx=ddx(ray),dy=ddy(ray),px=ddx(pos),py=ddy(pos);
float footprint=max(length(dx),length(dy));
float3 total=0;
float facing=smoothstep(.025,.075,ray.y);
float Brightness=lerp(.55,2.6,Night);

{ // Nexus: ray intersection with the same front-row display plane.
float3 center=float3(1196.694810324,672.697505200,8.750000000);float2 size=float2(55.000000000,77.500000000);
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
// Analytic ray-plane derivatives, calculated before any divergent sample branch.
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size);
Foot=clamp(Foot,.001,.45);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
// Explicit mip selection is stable even when this region leaves the main view.
float T=(Clock+0.000000000)*1.000000000;
float Slot=0.000000000;float Aspect=0.709677419;
float Lod=clamp(log2(max(max(Foot.x*512,Foot.y*1024),1)),2,6);
[branch] if(mask>.0001){
float3 Color=0;

float k=fmod(floor(T/12)+Slot,4), k1=fmod(k+1,4), f=frac(T/12);
float zoom=1+.035*sin(f*3.14159265);
float2 q=(UV-.5)/zoom+.5+float2(.003*sin(T*.31),.003*cos(T*.27));
// Keep the complete footprint inside its atlas cell, including distant mips.
float2 inset=max(float2(.018,.018),exp2(Lod)*float2(2.0/512,2.0/1024));
q=clamp(q,inset,1-inset);
float2 qa=(q+float2(fmod(k,2),floor(k/2)))*.5;
float2 qb=(q+float2(fmod(k1,2),floor(k1/2)))*.5;
float3 ca=Texture2DSampleLevel(Atlas,AtlasSampler,qa,Lod).rgb;
float3 cb=Texture2DSampleLevel(Atlas,AtlasSampler,qb,Lod).rgb;
float wipe=smoothstep(.88,.98,f+(UV.x-.5)*.10);
float2 p=(UV-.5)*float2(.6667,1);float rad=length(p),ang=atan2(p.y,p.x);
float3 accent=k<.5?float3(.15,.65,1):k<1.5?float3(1,.38,.055):k<2.5?float3(.35,.22,1):float3(1,.06,.5);
float scan=exp(-pow((UV.y-frac(T*.09))/.055,2));
float ringWidth=max(.009,Foot.y);
float ring=exp(-pow((rad-(.22+.035*sin(ang*2-T*.7)))/ringWidth,2))*.009/ringWidth;
float orbit=.5+.5*sin(ang*3-T*1.2);
float bars=smoothstep(.84,.90,UV.y)*(1-smoothstep(.92,.97,UV.y))*smoothstep(-Foot.y,Foot.y,.87+.06*sin(floor(UV.x*18)*1.7+T*2)-UV.y);
bars*=1-smoothstep(.025,.08,Foot.x);
float fx=k<.5?scan*.07:k<1.5?ring*orbit*.085:k<2.5?scan*.045:bars*.085;
float dropout=smoothstep(.70,.73,f)*(1-smoothstep(.74,.77,f))*exp(-pow((UV.y-.61)/.06,2));
Color=min((lerp(ca,cb,wipe)*(1-dropout*.06)+accent*fx)*Brightness,3.0);

total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}

{ // Estuary: ray intersection with the same front-row display plane.
float3 center=float3(463.842918666,778.573044008,10.000000000);float2 size=float2(37.500000000,55.000000000);
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
// Analytic ray-plane derivatives, calculated before any divergent sample branch.
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size);
Foot=clamp(Foot,.001,.45);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
// Explicit mip selection is stable even when this region leaves the main view.
float T=(Clock+4.100000000)*1.000000000;
float Slot=1.000000000;float Aspect=0.681818182;
float Lod=clamp(log2(max(max(Foot.x*512,Foot.y*1024),1)),2,6);
[branch] if(mask>.0001){
float3 Color=0;

float k=fmod(floor(T/12)+Slot,4), k1=fmod(k+1,4), f=frac(T/12);
float zoom=1+.035*sin(f*3.14159265);
float2 q=(UV-.5)/zoom+.5+float2(.003*sin(T*.31),.003*cos(T*.27));
// Keep the complete footprint inside its atlas cell, including distant mips.
float2 inset=max(float2(.018,.018),exp2(Lod)*float2(2.0/512,2.0/1024));
q=clamp(q,inset,1-inset);
float2 qa=(q+float2(fmod(k,2),floor(k/2)))*.5;
float2 qb=(q+float2(fmod(k1,2),floor(k1/2)))*.5;
float3 ca=Texture2DSampleLevel(Atlas,AtlasSampler,qa,Lod).rgb;
float3 cb=Texture2DSampleLevel(Atlas,AtlasSampler,qb,Lod).rgb;
float wipe=smoothstep(.88,.98,f+(UV.x-.5)*.10);
float2 p=(UV-.5)*float2(.6667,1);float rad=length(p),ang=atan2(p.y,p.x);
float3 accent=k<.5?float3(.15,.65,1):k<1.5?float3(1,.38,.055):k<2.5?float3(.35,.22,1):float3(1,.06,.5);
float scan=exp(-pow((UV.y-frac(T*.09))/.055,2));
float ringWidth=max(.009,Foot.y);
float ring=exp(-pow((rad-(.22+.035*sin(ang*2-T*.7)))/ringWidth,2))*.009/ringWidth;
float orbit=.5+.5*sin(ang*3-T*1.2);
float bars=smoothstep(.84,.90,UV.y)*(1-smoothstep(.92,.97,UV.y))*smoothstep(-Foot.y,Foot.y,.87+.06*sin(floor(UV.x*18)*1.7+T*2)-UV.y);
bars*=1-smoothstep(.025,.08,Foot.x);
float fx=k<.5?scan*.07:k<1.5?ring*orbit*.085:k<2.5?scan*.045:bars*.085;
float dropout=smoothstep(.70,.73,f)*(1-smoothstep(.74,.77,f))*exp(-pow((UV.y-.61)/.06,2));
Color=min((lerp(ca,cb,wipe)*(1-dropout*.06)+accent*fx)*Brightness,3.0);

total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}

{ // Tideline: ray intersection with the same front-row display plane.
float3 center=float3(94.978446442,825.619565989,-2.500000000);float2 size=float2(43.750000000,65.000000000);
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
// Analytic ray-plane derivatives, calculated before any divergent sample branch.
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size);
Foot=clamp(Foot,.001,.45);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
// Explicit mip selection is stable even when this region leaves the main view.
float T=(Clock+8.300000000)*1.000000000;
float Slot=2.000000000;float Aspect=0.673076923;
float Lod=clamp(log2(max(max(Foot.x*512,Foot.y*1024),1)),2,6);
[branch] if(mask>.0001){
float3 Color=0;

float k=fmod(floor(T/12)+Slot,4), k1=fmod(k+1,4), f=frac(T/12);
float zoom=1+.035*sin(f*3.14159265);
float2 q=(UV-.5)/zoom+.5+float2(.003*sin(T*.31),.003*cos(T*.27));
// Keep the complete footprint inside its atlas cell, including distant mips.
float2 inset=max(float2(.018,.018),exp2(Lod)*float2(2.0/512,2.0/1024));
q=clamp(q,inset,1-inset);
float2 qa=(q+float2(fmod(k,2),floor(k/2)))*.5;
float2 qb=(q+float2(fmod(k1,2),floor(k1/2)))*.5;
float3 ca=Texture2DSampleLevel(Atlas,AtlasSampler,qa,Lod).rgb;
float3 cb=Texture2DSampleLevel(Atlas,AtlasSampler,qb,Lod).rgb;
float wipe=smoothstep(.88,.98,f+(UV.x-.5)*.10);
float2 p=(UV-.5)*float2(.6667,1);float rad=length(p),ang=atan2(p.y,p.x);
float3 accent=k<.5?float3(.15,.65,1):k<1.5?float3(1,.38,.055):k<2.5?float3(.35,.22,1):float3(1,.06,.5);
float scan=exp(-pow((UV.y-frac(T*.09))/.055,2));
float ringWidth=max(.009,Foot.y);
float ring=exp(-pow((rad-(.22+.035*sin(ang*2-T*.7)))/ringWidth,2))*.009/ringWidth;
float orbit=.5+.5*sin(ang*3-T*1.2);
float bars=smoothstep(.84,.90,UV.y)*(1-smoothstep(.92,.97,UV.y))*smoothstep(-Foot.y,Foot.y,.87+.06*sin(floor(UV.x*18)*1.7+T*2)-UV.y);
bars*=1-smoothstep(.025,.08,Foot.x);
float fx=k<.5?scan*.07:k<1.5?ring*orbit*.085:k<2.5?scan*.045:bars*.085;
float dropout=smoothstep(.70,.73,f)*(1-smoothstep(.74,.77,f))*exp(-pow((UV.y-.61)/.06,2));
Color=min((lerp(ca,cb,wipe)*(1-dropout*.06)+accent*fx)*Brightness,3.0);

total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}

{ // Port: ray intersection with the same front-row display plane.
float3 center=float3(-470.361175537,1057.745684752,42.500000000);float2 size=float2(37.500000000,45.000000000);
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
// Analytic ray-plane derivatives, calculated before any divergent sample branch.
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size);
Foot=clamp(Foot,.001,.45);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
// Explicit mip selection is stable even when this region leaves the main view.
float T=(Clock+2.700000000)*0.920000000;
float Slot=3.000000000;float Aspect=0.833333333;
float Lod=clamp(log2(max(max(Foot.x*512,Foot.y*1024),1)),2,6);
[branch] if(mask>.0001){
float3 Color=0;

float k=fmod(floor(T/12)+Slot,4), k1=fmod(k+1,4), f=frac(T/12);
float zoom=1+.035*sin(f*3.14159265);
float2 q=(UV-.5)/zoom+.5+float2(.003*sin(T*.31),.003*cos(T*.27));
// Keep the complete footprint inside its atlas cell, including distant mips.
float2 inset=max(float2(.018,.018),exp2(Lod)*float2(2.0/512,2.0/1024));
q=clamp(q,inset,1-inset);
float2 qa=(q+float2(fmod(k,2),floor(k/2)))*.5;
float2 qb=(q+float2(fmod(k1,2),floor(k1/2)))*.5;
float3 ca=Texture2DSampleLevel(Atlas,AtlasSampler,qa,Lod).rgb;
float3 cb=Texture2DSampleLevel(Atlas,AtlasSampler,qb,Lod).rgb;
float wipe=smoothstep(.88,.98,f+(UV.x-.5)*.10);
float2 p=(UV-.5)*float2(.6667,1);float rad=length(p),ang=atan2(p.y,p.x);
float3 accent=k<.5?float3(.15,.65,1):k<1.5?float3(1,.38,.055):k<2.5?float3(.35,.22,1):float3(1,.06,.5);
float scan=exp(-pow((UV.y-frac(T*.09))/.055,2));
float ringWidth=max(.009,Foot.y);
float ring=exp(-pow((rad-(.22+.035*sin(ang*2-T*.7)))/ringWidth,2))*.009/ringWidth;
float orbit=.5+.5*sin(ang*3-T*1.2);
float bars=smoothstep(.84,.90,UV.y)*(1-smoothstep(.92,.97,UV.y))*smoothstep(-Foot.y,Foot.y,.87+.06*sin(floor(UV.x*18)*1.7+T*2)-UV.y);
bars*=1-smoothstep(.025,.08,Foot.x);
float fx=k<.5?scan*.07:k<1.5?ring*orbit*.085:k<2.5?scan*.045:bars*.085;
float dropout=smoothstep(.70,.73,f)*(1-smoothstep(.74,.77,f))*exp(-pow((UV.y-.61)/.06,2));
Color=min((lerp(ca,cb,wipe)*(1-dropout*.06)+accent*fx)*Brightness,3.0);

total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}

{ // NexusRibbon: ray intersection with the same front-row display plane.
float3 center=float3(1191.761016846,679.015611063,-50.000000000);float2 size=float2(47.500000000,8.750000000);
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
// Analytic ray-plane derivatives, calculated before any divergent sample branch.
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size);
Foot=clamp(Foot,.001,.45);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
// Explicit mip selection is stable even when this region leaves the main view.
float T=(Clock+6.400000000)*1.000000000;
float Slot=0.000000000;float Aspect=5.428571429;
float Lod=clamp(log2(max(max(Foot.x*Aspect/16*2048,Foot.y*128),1)),1,3);
[branch] if(mask>.0001){
float3 Color=0;

float2 q=float2(UV.x*Aspect/16+T*.028,(clamp(UV.y,.035,.965)+Slot)*.25);
float edge=smoothstep(0,.035,UV.x)*(1-smoothstep(.965,1,UV.x));
Color=Texture2DSampleLevel(Ticker,TickerSampler,q,Lod).rgb*Brightness*edge;

total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}

{ // EstuaryRibbon: ray intersection with the same front-row display plane.
float3 center=float3(466.331367493,773.660716084,-37.500000000);float2 size=float2(50.000000000,7.500000000);
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
// Analytic ray-plane derivatives, calculated before any divergent sample branch.
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size);
Foot=clamp(Foot,.001,.45);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
// Explicit mip selection is stable even when this region leaves the main view.
float T=(Clock+11.200000000)*1.000000000;
float Slot=2.000000000;float Aspect=6.666666667;
float Lod=clamp(log2(max(max(Foot.x*Aspect/16*2048,Foot.y*128),1)),1,3);
[branch] if(mask>.0001){
float3 Color=0;

float2 q=float2(UV.x*Aspect/16+T*.028,(clamp(UV.y,.035,.965)+Slot)*.25);
float edge=smoothstep(0,.035,UV.x)*(1-smoothstep(.965,1,UV.x));
Color=Texture2DSampleLevel(Ticker,TickerSampler,q,Lod).rgb*Brightness*edge;

total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}

{ // NexusA: same yaw, pitch, phase and length as the authored beam.
float pitch=radians(20.000000000+7.000000000*sin(Clock*6.2831853/32.000000000+0.000000000));
float yaw=radians(-20.000000000+32.000000000*sin(Clock*6.2831853/(32.000000000*1.31)+0.000000000*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin=float3(903.750000000,996.250000000,340.250000000),w=origin-pos;
float beamLength=360.000000000,b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength);
float travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float radius=lerp(.6*beamLength/400,20*beamLength/400,along/beamLength);
float blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float q=along/beamLength;
float lengthFade=smoothstep(0,.018,q)*pow(saturate(1-q),1.1)*(1-smoothstep(.72,1,q));
float mist=.94+.06*sin(Clock*.17+q*7);
total+=float3(0.080000000,0.550000000,1.000000000)*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}

{ // NexusB: same yaw, pitch, phase and length as the authored beam.
float pitch=radians(18.000000000+8.000000000*sin(Clock*6.2831853/39.000000000+2.000000000));
float yaw=radians(155.000000000+38.000000000*sin(Clock*6.2831853/(39.000000000*1.31)+2.000000000*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin=float3(885.000000000,996.250000000,340.250000000),w=origin-pos;
float beamLength=420.000000000,b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength);
float travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float radius=lerp(.6*beamLength/400,20*beamLength/400,along/beamLength);
float blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float q=along/beamLength;
float lengthFade=smoothstep(0,.018,q)*pow(saturate(1-q),1.1)*(1-smoothstep(.72,1,q));
float mist=.94+.06*sin(Clock*.17+q*7);
total+=float3(0.340000000,0.140000000,0.800000000)*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}

{ // EstuaryA: same yaw, pitch, phase and length as the authored beam.
float pitch=radians(19.000000000+6.000000000*sin(Clock*6.2831853/35.000000000+1.300000000));
float yaw=radians(15.000000000+27.000000000*sin(Clock*6.2831853/(35.000000000*1.31)+1.300000000*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin=float3(1885.000000000,1025.000000000,206.500000000),w=origin-pos;
float beamLength=340.000000000,b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength);
float travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float radius=lerp(.6*beamLength/400,20*beamLength/400,along/beamLength);
float blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float q=along/beamLength;
float lengthFade=smoothstep(0,.018,q)*pow(saturate(1-q),1.1)*(1-smoothstep(.72,1,q));
float mist=.94+.06*sin(Clock*.17+q*7);
total+=float3(0.080000000,0.480000000,0.700000000)*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}

{ // EstuaryB: same yaw, pitch, phase and length as the authored beam.
float pitch=radians(22.000000000+7.000000000*sin(Clock*6.2831853/43.000000000+3.400000000));
float yaw=radians(160.000000000+33.000000000*sin(Clock*6.2831853/(43.000000000*1.31)+3.400000000*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin=float3(1848.750000000,1025.000000000,206.500000000),w=origin-pos;
float beamLength=380.000000000,b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength);
float travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float radius=lerp(.6*beamLength/400,20*beamLength/400,along/beamLength);
float blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float q=along/beamLength;
float lengthFade=smoothstep(0,.018,q)*pow(saturate(1-q),1.1)*(1-smoothstep(.72,1,q));
float mist=.94+.06*sin(Clock*.17+q*7);
total+=float3(0.600000000,0.055000000,0.320000000)*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}

{ // PortA: same yaw, pitch, phase and length as the authored beam.
float pitch=radians(20.000000000+6.000000000*sin(Clock*6.2831853/41.000000000+0.800000000));
float yaw=radians(0.000000000+24.000000000*sin(Clock*6.2831853/(41.000000000*1.31)+0.800000000*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin=float3(-1347.500000000,2256.250000000,106.250000000),w=origin-pos;
float beamLength=480.000000000,b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength);
float travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float radius=lerp(.6*beamLength/400,20*beamLength/400,along/beamLength);
float blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float q=along/beamLength;
float lengthFade=smoothstep(0,.018,q)*pow(saturate(1-q),1.1)*(1-smoothstep(.72,1,q));
float mist=.94+.06*sin(Clock*.17+q*7);
total+=float3(0.120000000,0.480000000,0.750000000)*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}

{ // PortB: same yaw, pitch, phase and length as the authored beam.
float pitch=radians(22.000000000+8.000000000*sin(Clock*6.2831853/37.000000000+4.100000000));
float yaw=radians(180.000000000+27.000000000*sin(Clock*6.2831853/(37.000000000*1.31)+4.100000000*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin=float3(-1427.500000000,2256.250000000,106.250000000),w=origin-pos;
float beamLength=440.000000000,b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength);
float travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float radius=lerp(.6*beamLength/400,20*beamLength/400,along/beamLength);
float blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float q=along/beamLength;
float lengthFade=smoothstep(0,.018,q)*pow(saturate(1-q),1.1)*(1-smoothstep(.72,1,q));
float mist=.94+.06*sin(Clock*.17+q*7);
total+=float3(0.280000000,0.170000000,0.750000000)*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}
float nv=saturate(dot(N,normalize(cam-pos)));
float fresnel=.02037+.97963*pow(1-nv,5);
return min(total*fresnel,MaxRadiance);