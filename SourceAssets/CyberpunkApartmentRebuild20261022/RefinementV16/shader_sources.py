"""One animation source for the mounted displays and their water reflections."""
from pathlib import Path
import runpy
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'))

def campaign():
 return '''
float k=fmod(floor(T/12)+Slot,4), k1=fmod(k+1,4), f=frac(T/12);
float zoom=1+.015*sin(f*3.14159265);
float2 q=(UV-.5)/zoom+.5;
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
'''

def ribbon():
 return '''
float2 q=float2(UV.x*Aspect/16+T*.028,(clamp(UV.y,.035,.965)+Slot)*.25);
float edge=smoothstep(0,.035,UV.x)*(1-smoothstep(.965,1,UV.x));
Color=Texture2DSampleLevel(Ticker,TickerSampler,q,Lod).rgb*Brightness*edge;
'''

def display(kind):
 if kind=='portrait':
  lod='clamp(log2(max(max(Foot.x*512,Foot.y*1024),1)),0,6)'
 else:lod='clamp(log2(max(max(Foot.x*Aspect/16*2048,Foot.y*128),1)),0,3)'
 code='float2 Foot=max(abs(ddx(UV))+abs(ddy(UV)),.0001);float Lod='+lod+';float Brightness=lerp(.75,2.2,Night);float3 Color=0;'+(campaign() if kind=='portrait' else ribbon())+'return Color;'
 code=code.replace('Texture2DSampleLevel(Atlas,AtlasSampler,qa,Lod)','Texture2DSampleGrad(Atlas,AtlasSampler,qa,ddx(qa)*.85,ddy(qa)*.85)').replace('Texture2DSampleLevel(Atlas,AtlasSampler,qb,Lod)','Texture2DSampleGrad(Atlas,AtlasSampler,qb,ddx(qb)*.85,ddy(qb)*.85)').replace('Texture2DSampleLevel(Ticker,TickerSampler,q,Lod)','Texture2DSampleGrad(Ticker,TickerSampler,q,ddx(q)*.85,ddy(q)*.85)')
 return code

def f(v):return format(float(v),'.9f')
def v3(v):return 'float3('+','.join(f(x) for x in v)+')'

def reflection():
 code=['''// Apartment-local deterministic reflection supplement, metres throughout.
float3 pos=Position*.01,cam=Camera*.01;
float3 N=normalize(lerp(float3(0,0,1),normalize(WaterNormal),NormalWeight));
float3 ray=reflect(normalize(pos-cam),N);
float3 dx=ddx(ray),dy=ddy(ray),px=ddx(pos),py=ddy(pos);
float footprint=max(length(dx),length(dy));
float3 total=0;
float facing=smoothstep(.025,.075,ray.y);
float Brightness=lerp(.55,2.6,Night);
''']
 for b in C['BOARDS']:
  center=C['world_metres'](b['p']);w=b['w']*1.25;h=b['h']*1.25
  code.append('''
{ // '''+b['key']+''': ray intersection with the same front-row display plane.
float3 center='''+v3(center)+''';float2 size=float2('''+f(w)+','+f(h)+''');
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
float T=(Clock+'''+f(b['phase'])+')*'+f(.92 if b['key']=='Port' else 1)+''';
float Slot='''+f(b['slot'])+';float Aspect='+f(b['w']/b['h'])+''';
float Lod='''+('clamp(log2(max(max(Foot.x*512,Foot.y*1024),1)),2,6)' if b['kind']=='portrait' else 'clamp(log2(max(max(Foot.x*Aspect/16*2048,Foot.y*128),1)),1,3)')+''';
[branch] if(mask>.0001){
float3 Color=0;
'''+(campaign() if b['kind']=='portrait' else ribbon())+'''
total+=Color*mask*AdGain*lerp(.18,1,Night);
}
}
''')
 for b in C['SEARCH']:
  p=list(C['world_metres'](b['p']));p[2]+=3.75
  code.append('''
{ // '''+b['key']+''': same yaw, pitch, phase and length as the authored beam.
float pitch=radians('''+f(b['tilt'])+'+'+f(b['tilt_sweep'])+'*sin(Clock*6.2831853/'+f(b['period'])+'+'+f(b['phase'])+'''));
float yaw=radians('''+f(b['yaw'])+'+'+f(b['yaw_sweep'])+'*sin(Clock*6.2831853/('+f(b['period'])+'*1.31)+'+f(b['phase'])+'''*.73));
float3 axis=float3(sin(pitch)*cos(yaw),sin(pitch)*sin(yaw),cos(pitch));
float3 origin='''+v3(p)+''',w=origin-pos;
float beamLength='''+f(b['length'])+''',b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
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
total+='''+v3(b['color'])+'''*.36*BeamGain*radial*lengthFade*mist*Night*smoothstep(0,5,travel);
}
''')
 code.append('''float nv=saturate(dot(N,normalize(cam-pos)));
float fresnel=.02037+.97963*pow(1-nv,5);
return min(total*fresnel,MaxRadiance);''')
 return ''.join(code)

def write():
 for name,code in [('Portrait',display('portrait')),('Ribbon',display('ribbon')),('WaterReflection',reflection())]:
  (R/(name+'.hlsl')).write_text(code,encoding='utf8')
if __name__=='__main__':write()
