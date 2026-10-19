"""Construct the approved ST6 boots: native foot last, sewn quarters, laces and lug soles."""
import json,math,sys
from pathlib import Path
import bpy,bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018';sys.path.insert(0,str(P/'Tools/ST6LowerSet'))
import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
native=json.loads((R/'native_reference.json').read_text());g.bone_ids={b['name']:b['index'] for b in native['bones']}
body=json.loads((P/'SourceAssets/ST6Reset20261017/Read/Jason.json').read_text());bp=np.array(body['positions'])
levels=np.array([8,12,16,20,24,28,32]);fields=[]
for z in levels:
    q=bp[(bp[:,0]>0)&(abs(bp[:,2]-z)<.85)]
    if z<=8:fields.append([14.8,-2.45,4.4,5.4]);continue
    lo=q.min(0);hi=q.max(0);fields.append([(lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,(hi[0]-lo[0])*.5+.85,(hi[1]-lo[1])*.5+.85])
fields=np.array(fields)
def profile(z):return np.array([np.interp(z,levels,fields[:,i]) for i in range(4)])
g.profile=profile

def patch(name,side,fn,nu,nv,slot,mode='flex',thick=.12):
    points=[fn(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)];faces=[]
    for j in range(nv):
        for i in range(nu):a=j*(nu+1)+i;faces.append([a,a+1,a+nu+2,a+nu+1])
    return g.mesh_object(name,points,faces,side,mode,slot,thick,.045)
def box(name,side,center,half,slot,mode='foot',angle=0):
    c=np.array(center);cs=math.cos(angle);sn=math.sin(angle);rot=np.array([[cs,-sn,0],[sn,cs,0],[0,0,1]])
    points=[c+rot@np.array([x,y,z]) for x in [-half[0],half[0]] for y in [-half[1],half[1]] for z in [-half[2],half[2]]]
    return g.mesh_object(name,points,[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]],side,mode,slot,bevel=.075)
def seam(name,path,side,mode='flex',slot=3):
    # A single narrow stitched welt follows each actual panel boundary.
    g.tube(name,path,.035,side,mode,slot,False,5)

for side,sign in [('l',1),('r',-1)]:
    start=len(g.objects)
    # Reuse the precise native last; shorten the upper by remapping stations.
    g.leather(side)
    for ob in g.objects[start:]:
        if ob.name.startswith('LeatherShaft'):
            for v in ob.data.vertices:v.co.z=(8+(v.co.z*100-8)*(20.4/30.4))*.01
            # Re-evaluate radial fit at the shortened height instead of scaling the leg.
            for v in ob.data.vertices:
                z=v.co.z*100;oldz=8+(z-8)*(30.4/20.4);old=profile(oldz);new=profile(z)
                x=v.co.x*100;y=-v.co.y*100
                v.co.x=(sign*new[0]+(x-sign*old[0])*new[2]/old[2])*.01
                v.co.y=-(new[1]+(y-old[1])*new[3]/old[3])*.01
        if ob.name.startswith('LeatherFoot'):
            for v in ob.data.vertices:v.co.z=max(v.co.z,.014)
        if ob.name.startswith('LayeredLeatherSole'):
            for v in ob.data.vertices:v.co.z=float(np.interp(v.co.z*100,[-2.6,-2.48,-1.05,-.60],[.6,.78,1.65,2.0]))*.01
        if ob.name.startswith(('RaisedWelt','WeltStitch')):
            for v in ob.data.vertices:v.co.z+=.0265
        if ob.name.startswith('LeatherShaft'):ob['material_slot']=5
        ob.data.update();bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    baseobjects=list(g.objects[start:]);points=[];faces=[]
    for ob in baseobjects:
        if not ob.name.startswith(('LeatherFoot','LeatherShaft')):continue
        ob.data.calc_loop_triangles();first=len(points);points.extend((v.co.x*100,-v.co.y*100,v.co.z*100) for v in ob.data.vertices)
        faces.extend([[first+i for i in reversed(t.vertices)] for t in ob.data.loop_triangles])
    surface=BVHTree.FromPolygons(points,faces,all_triangles=True)
    def project(p,offset=.12):
        q,n,_,_=surface.find_nearest(Vector(p));return np.array(q)+np.array(n)*offset
    # Reinforced toe follows the foot, leaving the instep flexible.
    patch('Black_MoldedToe_'+side,side,lambda u,v:project(g.dorsal(side,15+v*8.8,(u*2-1)*1.82,.22),.16),40,18,2,'foot',.19)
    seam('Toe_DoubleSeamA_'+side,[project(g.dorsal(side,14.95,a,.2),.25) for a in np.linspace(-1.8,1.8,90)],side,'foot')
    seam('Toe_DoubleSeamB_'+side,[project(g.dorsal(side,14.65,a,.2),.25) for a in np.linspace(-1.8,1.8,90)],side,'foot')
    patch('Black_HeelCounter_'+side,side,lambda u,v:project(g.shaft_point(side,math.pi+(u-.5)*2.9,2.0+9*v,.2),.18),40,16,2,'foot',.18)
    # Khaki leather quarter frames surround the dark woven ventilation panels.
    for flank in [-1,1]:
        patch('Khaki_Quarter_%s_%s'%(side,flank),side,lambda u,v,flank=flank:project(g.dorsal(side,-4+17*v,flank*(.95+.56*u),.3),.16),16,36,4,'flex',.14)
        seam('Quarter_Edge_%s_%s'%(side,flank),[project(g.dorsal(side,v,flank*1.5,.3),.28) for v in np.linspace(-3,13,70)],side)
        # Two diagonal uprights form the characteristic glove-like khaki frame.
        for index,baseangle in enumerate([.65,2.30]):
            def upright(u,v,baseangle=baseangle,flank=flank):
                z=11+17*v;angle=flank*(baseangle+.22*math.sin(v*math.pi)+(u-.5)*.35)
                return project(g.shaft_point(side,angle,z,.3),.16)
            patch('Khaki_ShaftFrame_%s_%s_%s'%(side,flank,index),side,upright,8,28,4)
            for edge in [0,1]:seam('Frame_Stitch_%s_%s_%s_%s'%(side,flank,index,edge),[upright(edge,v)+[0,0,.025] for v in np.linspace(.02,.98,60)],side)
        patch('Khaki_AnkleBand_%s_%s'%(side,flank),side,lambda u,v,flank=flank:project(g.shaft_point(side,flank*(.55+2.1*u),12.1+2.1*v,.3),.19),36,6,4)
        patch('Black_AnkleSupport_%s_%s'%(side,flank),side,lambda u,v,flank=flank:project(g.shaft_point(side,flank*(1.20+.65*u),18.1+5.0*v,.4),.29+.12*math.sin(v*math.pi)*math.sin(u*math.pi)),18,18,2,'calf',.16)
    # Rolled padded opening, a leather facing and posterior pull loop.
    patch('Khaki_CollarFacing_'+side,side,lambda u,v:project(g.shaft_point(side,u*math.tau,26.5+1.55*v,.3),.15),72,6,4,'calf',.14)
    g.tube('Padded_BlackRim_'+side,[g.shaft_point(side,t,28.32+.20*max(0,math.cos(t)),.08) for t in np.linspace(0,math.tau,96,endpoint=False)],.24,side,'calf',5,True,10)
    patch('Rear_PullLoop_'+side,side,lambda u,v:g.shaft_point(side,math.pi+(u-.5)*.25,24.7+4.3*v,.25+.45*math.sin(v*math.pi)),8,18,4,'calf',.14)
    for z in np.linspace(13,22.3,7):
        g.tube('Achilles_FlexRib_%s_%.2f'%(side,z),[project(g.shaft_point(side,math.pi+a,z,.2),.20) for a in np.linspace(-.44,.44,24)],.13,side,'flex',5,False,7)
    # Lace centers move smoothly from instep to the gusseted tongue.
    curve=np.array([g.dorsal(side,13.2,0,.4),g.dorsal(side,3.8,0,1.1),g.shaft_point(side,0,18,.5),g.shaft_point(side,0,27.8,.5)])
    widthaxis=np.array([sign*.9882,-.1533,0])
    def front(t):
        q=(1-t)**3*curve[0]+3*(1-t)**2*t*curve[1]+3*(1-t)*t*t*curve[2]+t**3*curve[3]
        return project(q,.30)
    patch('Padded_GussetedTongue_'+side,side,lambda u,v:project(front(v)+widthaxis*(u-.5)*4.3,.33),14,48,5,'flex',.20)
    stations=np.linspace(.02,.97,9);left=[];right=[]
    for t in stations:
        center=front(t);row=[]
        for flank in [-1,1]:
            q=project(center+widthaxis*flank*2.5,.40);row.append(q)
            radial=g.unit(q-np.array([sign*profile(q[2])[0],profile(q[2])[1],q[2]])) if q[2]>13 else np.array([0,0,1.])
            a=g.unit(widthaxis);b=g.unit(np.cross(radial,a))
            g.tube('Gunmetal_Eyelet_%s_%.2f_%s'%(side,t,flank),[q+.29*(math.cos(v)*a+math.sin(v)*b) for v in np.linspace(0,math.tau,16,endpoint=False)],.075,side,'flex',0,True,6)
        left.append(row[0]);right.append(row[1])
    for flank,rows in [(-1,left),(1,right)]:
        for j in range(len(rows)-1):
            a=rows[j];b=rows[j+1]
            patch('Khaki_LaceFacing_%s_%s_%s'%(side,flank,j),side,lambda u,v,a=a,b=b:project(a*(1-v)+b*v+widthaxis*(u-.5)*1.1,.21),6,7,4,'flex',.13)
    for j in range(len(stations)-1):
        for a,b in [(left[j],right[j+1]),(right[j],left[j+1])]:
            line=[a*(1-t)+b*t+np.array([0,.13,.12])*math.sin(t*math.pi) for t in np.linspace(0,1,14)]
            g.tube('Crossed_Lace_%s_%s'%(side,len(g.objects)),line,.105,side,'flex',2,False,7)
    center=(left[-1]+right[-1])*.5
    for flank in [-1,1]:
        loop=[center+widthaxis*(flank*1.4*math.sin(t))+np.array([0,.12,.8*(1-math.cos(t))]) for t in np.linspace(0,math.tau,40)]
        g.tube('Tied_LaceLoop_%s_%s'%(side,flank),loop,.10,side,'calf',2,False,7)
    # Discrete tread lugs with a clear medial arch; no giant flat sole slab.
    for j,v in enumerate(np.linspace(-5.1,21.8,10)):
        w,_=g.foot_shape(v)
        for flank in [-1,1]:
            center=g.foot_point(side,flank*max(.8,w-.9),v,.15)
            box('Outer_Tread_%s_%s_%s'%(side,j,flank),side,center,[.9,1.15,.55],2,angle=sign*flank*.25)
        if v<1 or v>8:
            center=g.foot_point(side,0,v,.15)
            box('Center_Tread_%s_%s'%(side,j),side,center,[max(1,w-2.1),.8,.55],2,angle=.16*((-1)**j))

data={k:[] for k in ('positions','triangles','weights','uv','normals','triangle_materials','parts')}
for ob in g.objects:
    mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active;start=len(data['positions']);pts=np.array([(v.co.x*100,-v.co.y*100,v.co.z*100) for v in mesh.vertices]);data['positions'].extend(pts.tolist())
    for p in pts:
        ws=g.skin(ob['side'],p,ob['weight_zone']);total=sum(ws.values());data['weights'].append([[int(k),float(v/total)] for k,v in ws.items() if v>1e-7])
    count=0
    for tri in mesh.loop_triangles:
        p=pts[list(tri.vertices)]
        if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-9:continue
        data['triangles'].append([start+i for i in tri.vertices]);mapped=np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops]);data['uv'].append(g.valid_uv(mapped,p).tolist())
        data['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops]);data['triangle_materials'].append(int(ob['material_slot']));count+=1
    data['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(pts),triangles=count,material=int(ob['material_slot'])))
data.update(source=native['source'],skeleton=native['skeleton'],bones=native['bones'],contract='ST6TacticalBoots20261018: original procedural native foot last; khaki quarters, black toe heel ankle shells, laces, gusset, soft collar, real sole lugs; native calf/foot/ball weights')
(R/'Jason_ST6Boots_Garment.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(R/'boot_profile.json').write_text(json.dumps(dict(levels=levels.tolist(),fields=fields.tolist(),shaft_top_cm=28.5,body_covers=[4,11,13,15,16],exposed_calf_from_cm=27),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ST6Boots_Construction.blend'))
print('ST6_BOOTS_AUTHORED',len(data['positions']),len(data['triangles']),flush=True)
