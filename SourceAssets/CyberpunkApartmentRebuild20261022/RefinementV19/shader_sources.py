"""Shared visible/reflected hologram grammar and additional bounded emitters."""
from pathlib import Path
import json,runpy
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'))
old=runpy.run_path(str(R.parent/'RefinementV16/shader_sources.py'))
def f(v):return format(float(v),'.9f')
def v3(v):return 'float3('+','.join(f(x) for x in v)+')'
SHAPES='''
struct AP19Shapes {
 float segment(float2 p,float2 a,float2 b,float width,float aa){float2 q=p-a,v=b-a;float d=length(q-v*saturate(dot(q,v)/dot(v,v)));return 1-smoothstep(max(0,width-aa),width+aa,d);}
}; AP19Shapes shape;
'''
def hologram(sample):
 return '''
float aa=clamp(max(Foot.x,Foot.y)*1.25,.0015,.12);
float2 p=UV-float2(.5,.34);float r=length(p),angle=atan2(p.y,p.x);
float ring=(1-smoothstep(max(0,.005-aa),.005+aa,abs(r-.245)))*.005/max(.005,aa);
float gate=smoothstep(-.15,.15,sin(angle*3-T*.28));
ring*=.24+.76*gate;
float glyph=0;
if(Style<.5){
 glyph=max(shape.segment(p,float2(-.115,.105),float2(0,-.13),.009,aa),shape.segment(p,float2(0,-.13),float2(.115,.105),.009,aa));
 glyph=max(glyph,shape.segment(p,float2(-.069,.027),float2(.069,.027),.009,aa));
 float diamond=abs(abs(p.x)+abs(p.y)-.175);
 glyph=max(glyph,(1-smoothstep(max(0,.003-aa),.003+aa,diamond))*.20);
} else {
 for(int k=0;k<3;k++){
  float a=T*.095+k*1.04719755;float2 q=float2(cos(a)*p.x-sin(a)*p.y,sin(a)*p.x+cos(a)*p.y);
  float d=abs(length(q*float2(1,2.5))-.175);
  glyph=max(glyph,(1-smoothstep(max(0,.006-aa),.006+aa,d))*.006/max(.006,aa));
 }
 glyph=max(glyph,1-smoothstep(.023,.023+aa,r));
}
float text='''+sample+''';
float scan=.90+.10*exp(-pow((UV.y-(.48+.35*sin(T*.22)))/.08,2));
Color=(Tint*(glyph+ring*.55)+lerp(Tint,float3(1,1,1),.65)*text)*Gain*scan*Night;
'''
def reflection():
 # Generate the retained six displays/beams plus the two new physical displays
 # using the existing shared animation source and resident campaign atlas.
 config=dict(old['C']);config['BOARDS']=list(config['BOARDS'])+C['BOARDS']
 old['reflection'].__globals__['C']=config
 base=old['reflection']();end='float nv=saturate(dot(N,normalize(cam-pos)));'
 head,tail=base.rsplit(end,1);code=[SHAPES,head]
 for i,b in enumerate(json.loads((R/'assembly.json').read_text())['holograms']):
  center=C['world_metres'](b['p']);size=(b['w']*1.25,b['h']*1.25)
  code.append('''
{ // '''+b['key']+''' shared holographic plane, derivative filtered.
float3 center='''+v3(center)+''';float2 size=float2('''+f(size[0])+','+f(size[1])+''');
float travel=(center.y-pos.y)/max(ray.y,.025);
float3 delta=pos+ray*travel-center;
float2 UV=float2(.5-delta.x/size.x,.5-delta.z/size.y);
float tx=(-px.y-travel*dx.y)/max(ray.y,.025),ty=(-py.y-travel*dy.y)/max(ray.y,.025);
float3 hx=px+dx*travel+ray*tx,hy=py+dy*travel+ray*ty;
float2 Foot=clamp(max(float2(abs(hx.x)+abs(hy.x),abs(hx.z)+abs(hy.z))/size,Blur*abs(travel)/size),.001,.4);
float2 coverage=smoothstep(-Foot,Foot,UV)*(1-smoothstep(1-Foot,1+Foot,UV));
float mask=coverage.x*coverage.y*facing*smoothstep(0,5,travel);
float Lod=clamp(log2(max(max(Foot.x,Foot.y)*1024,1)),1,7);
float T=Clock+'''+f(b['phase'])+';float Style='+f(b['style'])+';float3 Tint='+v3(b['color'])+''';float Gain=1.5;
[branch] if(mask>.0001){float3 Color=0;
'''+hologram('Texture2DSampleLevel(Holo'+str(i)+',Holo'+str(i)+'Sampler,saturate(UV),Lod).a')+'''
total+=Color*mask*AdGain*.75;}
}
''')
  origin=C['world_metres'](b['beam_origin']);a=b['beam_axis'];axis=(-a[0],a[1],a[2]);length=b['beam_length']*1.25
  code.append('''
{ // '''+b['key']+''' roof projector; same endpoints as visible cone.
float3 origin='''+v3(origin)+',axis='+v3(axis)+''',w=origin-pos;
float beamLength='''+f(length)+''',b=dot(ray,axis),d=dot(w,ray),e=dot(w,axis);
float along=clamp((b*d-e)/max(1-b*b,.002),0,beamLength),travel=dot(w+axis*along,ray);
float3 separation=pos+ray*travel-(origin+axis*along);
float q=along/beamLength,radius=lerp(1.675,15,q),blur=max(footprint*abs(travel)*1.5,Blur*abs(travel));
float rr=radius*radius+blur*blur;
float radial=exp(-dot(separation,separation)*2.4/max(rr,.001))*radius*radius/max(rr,.001);
float fade=smoothstep(0,.018,q)*(1-smoothstep(.76,1,q))*(.96+.04*sin((Clock+'''+f(b['phase'])+''')*.22+q*4));
total+='''+v3(b['color'])+'''*.22*BeamGain*radial*fade*Night*smoothstep(0,5,travel);
}
''')
 code.append(end+tail);return ''.join(code)
def main():
 visible=SHAPES+'float2 Foot=max(abs(ddx(UV))+abs(ddy(UV)),.0001);float3 Color=0;'+hologram('Texture2DSampleGrad(Glyph,GlyphSampler,UV,ddx(UV),ddy(UV)).a')+'return Color;'
 (R/'Hologram.hlsl').write_text(visible,encoding='utf8');(R/'WaterReflection.hlsl').write_text(reflection(),encoding='utf8')
 print('AP19_SHARED_SHADERS_AUTHORED')
if __name__=='__main__':main()
