"""Rebuild the boonie as a softly sewn cloth hat with controlled rear motion."""
import sys,math,types
import bpy,numpy as np
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
sys.path.insert(0,str(P/'Tools/FieldHat'))
# Reuse the fit/export contract; replace silhouette and tailoring explicitly.
code=(P/'Tools/FieldHat/author_boonie.py').read_text(encoding='utf-8')
code=code.replace('np.array([0.30, 3.20])','np.array([0.30, 2.10])').replace('(0.30, 3.20)','(0.30, 2.10)').replace('(3.20, 1.0)','(2.10, 1.0)').replace('(0.40, 3.10)','(0.40, 2.00)').replace('1.75','1.20').replace('2.80, 1.90, 0.30','2.15, 1.45, 0.25').replace('0.30, 3.02','0.30, 1.92')
h=types.ModuleType('workwear_hat_author');exec(compile(code,'workwear_hat_template','exec'),h.__dict__)
h.SRC=R/'Hat';h.H=8.35;h.BRIM=5.35;h.THICK=.16;h.BRIM_THICK=.18;h.CAP_DOME=.45;h.CAP_RINGS=(.88,.72,.52,.30,.12)
def crown(t,a,inner=False):
    # Rounded, slightly collapsed crown; the lower opening keeps the captured fit.
    rs=1-.025*t-.04*float(h.smoothstep(.72,1,t))
    fold=(.16*math.sin(a*7+1.6*t)+.10*math.sin(a*11-2*t))*math.sin(math.pi*t)**1.3
    dent=-.28*math.exp(-(h.angular_distance(a,.65)/.36)**2)*math.sin(math.pi*t)
    rx=h.RBX*rs+fold+dent;ry=h.RBY*rs+fold+dent
    if inner:rx-=h.THICK;ry-=h.THICK
    z=h.H*t+.20*math.sin(3*a+.4)*float(h.smoothstep(.55,1,t))
    return np.array([rx*math.sin(a),-ry*math.cos(a),z])
def brim(u,a,lower=False):
    width=h.BRIM*(1-.055*math.cos(2*a))
    rx=h.RBX-.45+u*(width+.45);ry=h.RBY-.45+u*(width+.45)
    z=-1.15*u-1.00*u*u*max(math.cos(a),0)**4
    z+=(.58*math.sin(3*a+.65)+.29*math.sin(5*a-1.2)+.14*math.sin(9*a+.2))*u**2.2
    z+=.52*math.exp(-(h.angular_distance(a,1.7)/.35)**2)*u*u
    if lower:z-=h.BRIM_THICK
    return np.array([rx*math.sin(a),-ry*math.cos(a),z])
h.crown_point=crown;h.brim_point=brim
head=read(R/'Hat/native_head_jason.json');d,center,z0,rx,ry,names=h.build_mesh(head)
# Canvas repeats over 25 cm; leather shares the jacket's 8 cm physical field.
for fi,slot in enumerate(d['triangle_materials']):
    if slot==2:d['uv'][fi]=(np.array(d['uv'][fi])*25/8).tolist()
from geometry import tube,finish
def stitches(path,normals,weights,pitch=.32):
    pp=np.array(path);nn=np.array(normals);length=np.linalg.norm(np.roll(pp,-1,axis=0)-pp,axis=1);arc=np.r_[0,np.cumsum(length)]
    def sample(s):
        i=min(np.searchsorted(arc,s%arc[-1],side='right')-1,len(pp)-1);t=(s-arc[i])/max(length[i],1e-9);j=(i+1)%len(pp)
        return pp[i]*(1-t)+pp[j]*t,nn[i]*(1-t)+nn[j]*t,weights[i]
    for s in np.arange(.14,arc[-1]-.15,pitch):
        line=[];ww=[]
        for t in (0,.33,.67,1):
            p,n,w=sample(s+(t-.5)*.20);line.append(p+n*(.005+.018*math.sin(math.pi*t)));ww.append(w)
        tube(d,line,.018,5,lambda q,line=line,ww=ww:ww[int(np.argmin(np.linalg.norm(np.array(line)-q,axis=1)))],sides=4)
for u in (.19,.36,.53,.70,.87):
    angles=np.linspace(0,math.tau,220,endpoint=False);stitches([brim(u,a)+[0,0,.022] for a in angles],[[0,0,1]]*len(angles),[h.brim_weight(a,u) for a in angles])
angles=np.linspace(0,math.tau,200,endpoint=False)
stitches([crown(.965,a) for a in angles],[h.radial_normal(crown(.965,a),h.RBX,h.RBY) for a in angles],[h.ROOT_W]*len(angles))
for a in np.linspace(0,math.tau,6,endpoint=False):
    path=[crown(t,a)+h.radial_normal(crown(t,a),h.RBX,h.RBY)*.035 for t in np.linspace(.26,.96,50)]
    tube(d,path,.020,5,h.ROOT_W,sides=4)
finish(d);d['contract']='Workwear boonie: soft 8.35cm crown, variable 5.35cm bound brim, 5 stitched quilting rows, sewn panels, thin sweatband; original head interface and bounded rear spring'
compact(R/'Hat/Authored/hat.json',d);fit=h.save_fit(head,d,center,z0,rx,ry)
obj=h.build_blender(d,names)
from workwear_inventory import studio
icons=studio(R/'Hat','ue_field_hat')
result=icons.render_current('ue_field_hat',obj,item=dict(grid_w=2,grid_h=2),camera_offset=(.75,3.0,1.6))
write(R/'Hat/authored.json',dict(completed=True,triangles=len(d['triangles']),fit=fit,bones=names,icon=result,blend=str(R/'Hat/Exports/FieldHat.blend'),fbx=str(R/'Hat/Exports/FieldHat.fbx'),runtime_tested=False))
print('WORKWEAR_HAT_AUTHORED',len(d['triangles']),flush=True)
