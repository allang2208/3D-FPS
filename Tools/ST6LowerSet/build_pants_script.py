"""Specialize the continuous native capri construction for the approved ST6 design."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');T=P/'Tools/ST6LowerSet'
s=(P/'Tools/SmokeGreyCapri/author_geometry.py').read_text()
s=s.replace("R=P/'SourceAssets/SmokeGreyCapri20261004'","R=P/'SourceAssets/ST6LowerSet20261018'")
s=s.replace("str(P/'Tools/BrownLeatherSet/geometry.py')","str(P/'Tools/ST6LowerSet/geometry.py')")
a=s.index('def leg(z,t,side,offset=0):');b=s.index('\ndef grid(',a)
s=s[:a]+'''def leg(z,t,side,offset=0):
    sign=1 if side=='l' else -1;hs=[14,20,30,40,47.35,58,67,72]
    cx=np.interp(z,hs,[14.7,14.2,13.5,12.6,12.04,11.2,10.5,9.8]);cy=np.interp(z,hs,[-2.6,-2,-1.2,-.4,.8,1.7,2.3,2.6])
    rx=np.interp(z,hs,[4.2,4.65,5.85,6.2,6.5,7.45,8.5,9.1]);ry=np.interp(z,hs,[4.9,5.5,6.65,7.45,8.2,9.2,10.3,10.6])
    fold=(.13*math.sin(z*.63+1.4*math.sin(t))+.07*math.sin(5*t+z*.31))*min(1,max(0,(z-15)/5))*min(1,max(0,(72-z)/8))
    knee=.15*math.sin(z*1.4+math.sin(t))*math.exp(-((z-46)/4)**2)
    return np.array([sign*(cx+(rx+fold+offset)*math.sin(t)),cy+(ry+fold+knee+offset)*math.cos(t),z])
''' +s[b:]
s=s.replace('np.linspace(64.8,30,30)','np.linspace(64.8,14,47)')
s=s.replace('vent=2.4*max(0,1-gap/.10)*max(0,1-(z-30)/3.0)','vent=0.')
s=s.replace('center=np.array([sign*13.5,-1.2])','center=np.array([sign*14.7,-2.6])')
s=s.replace('z=41.5+12*v;spread=.50','z=39.8+15.6*v;spread=.65')
s=s.replace("patch('Soft_KneeFacing_'+side,side,knee,22,20,1,.08)","patch('Khaki_KneeFrame_'+side,side,knee,24,24,4,.14)")
s=s.replace('np.linspace(33,64.7,90)','np.linspace(16,64.7,110)')
s=s.replace('for z in [30.55,31.45]','for z in [14.55,15.45]').replace('lift=2.4*max(0,1-gap/.10)','lift=0.')
s=s.replace("[p[0]-sign*13.5,p[1]+1.2,0]","[p[0]-sign*14.7,p[1]+2.6,0]")
extra='''
# Integrated rounded black kneecups and a stretch insert behind each knee.
for side,sign in [('l',1),('r',-1)]:
    verts=[];faces=[];nr=64
    def cap(r,a):
        dx=4.65*math.copysign(abs(math.cos(a))**.82,math.cos(a))*r
        dz=6.55*math.copysign(abs(math.sin(a))**.88,math.sin(a))*r
        point=project(leg(47.5+dz,0,side)+[sign*dx,0,0],.29+.85*(1-r*r))
        return point
    verts.append(cap(0,0))
    for r in [.12,.28,.46,.64,.8,.92,1]:verts.extend(cap(r,a) for a in np.linspace(0,math.tau,nr,endpoint=False))
    for i in range(nr):faces.append([0,1+i,1+(i+1)%nr])
    for j in range(6):
        for i in range(nr):a=1+j*nr+i;b=1+j*nr+(i+1)%nr;faces.append([a,b,b+nr,a+nr])
    g.mesh_object('Rounded_HardKnee_'+side,verts,faces,side,'pants',2,.22,.085)
    patch('Knee_RearStretch_'+side,side,lambda u,v:project(leg(40+14*v,math.pi+(u-.5)*1.1,side),.08),24,22,5,.07)
    patch('Ankle_KhakiCinch_'+side,side,lambda u,v:leg(14.3+2.1*v,.95+u*.65,side,.20),20,5,4,.13)
    patch('Ankle_BlackHookLoop_'+side,side,lambda u,v:leg(14.4+1.8*v,1.56+u*.48,side,.25),18,5,5,.09)
    patch('Pocket_KhakiPull_'+side,side,lambda u,v:project(leg(64-2.6*v,1.45+(u-.5)*.075,side),.55),4,8,4,.12)
patch('Black_WebBelt','both',lambda u,v:torso(96.9+2.6*v,u*math.tau,.23),96,4,5,.15)
for side,sign in [('l',1),('r',-1)]:
    patch('Waist_Adjuster_'+side,side,lambda u,v:torso(97.25+1.8*v,sign*(1.25+.40*u),.44),16,4,4,.13)
center=torso(98.2,0,.66);verts=[center+[x,y,z] for x in [-2.1,2.1] for y in [-.22,.22] for z in [-1.5,1.5]]
g.mesh_object('LowProfile_BeltBuckle',verts,[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]],'both','pants',2,bevel=.16)
'''
s=s.replace("data={k:[] for k in",extra+"\ndata={k:[] for k in")
s=s.replace('Jason_SmokeGreyCapri_Garment','Jason_ST6Trousers_Garment').replace('Capri_Construction.blend','ST6Trousers_Construction.blend')
s=s.replace('SmokeGreyCapri20261004 CrotchSeamFix20261005 NativeWaistFit20261018','ST6Trousers20261018 NativeWaistFit20261018')
s=s.replace('mid-calf hem 30cm','tapered full-length hem 14cm').replace("hem_height_cm=30,matching_shirt='ue_field_sweater_charcoal'","hem_height_cm=14,matching_shirt='ue_st6_sleeves'")
s=s.replace("(R/'production.json')","(R/'pants_production.json')")
s=s.replace("data.update(source=native['source']", "\n# Integrated crotch stretch uses the same welded mesh and skinning.\nfor fi,face in enumerate(data['triangles']):\n    mid=np.mean([data['positions'][i] for i in face],axis=0)\n    if data['triangle_materials'][fi]==1 and abs(mid[0])<4 and 68<mid[2]<80:data['triangle_materials'][fi]=5\ndata.update(source=native['source']")
(T/'author_pants.py').write_text(s,encoding='utf-8')
print('ST6_TROUSER_AUTHOR_WRITTEN')
