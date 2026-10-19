"""Continuous native-last mage boots with inset cloth, real rim and native flex."""
import sys,math,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
g=module('mage_boots_geometry','Tools/ST6LowerSet/geometry.py');bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
native=read(P/'SourceAssets/BlueMagePants20261019/native_reference.json');g.bone_ids={b['name']:b['index'] for b in native['bones']};original_profile=g.profile
def profile(z):
    q=original_profile(z);q[2]+=.35;q[3]+=.35;return q
g.profile=profile
ANGLE=math.atan2(2.00392146,12.92064786);ca,sa=math.cos(ANGLE),math.sin(ANGLE)
foot_levels=np.array([-7.,-6.6,-5.5,-3,0,3,6,10,14,18,21,22.8,24.])
widths=np.array([.12,2.4,3.9,4.35,4.6,4.95,5.5,6.,6.15,5.65,4.7,3.35,.12])
heights=np.array([4.1,6.2,8.2,10.,11.6,10.4,8.2,6.6,5.7,5.15,4.75,3.7,1.55])
rays=np.linspace(0,35,801)
def smooth(a,b,x):
    t=float(np.clip((x-a)/(b-a),0,1));return t*t*(3-2*t)
def bounds(z):
    half=.08+.82*smooth(7.8,19,z);return .45-half,.45+half
def top(theta):return 38.45+.45*max(0,math.cos(theta))-.18*max(0,-math.cos(theta))
def point(side,theta,z,offset=0):
    sign=1 if side=='l' else -1;cx,cy,rx,ry=profile(z);dx,dy=math.sin(theta),math.cos(theta);rs=1/math.sqrt((dx/rx)**2+(dy/ry)**2);rf=0.
    if z<11.65:
        xx=cx+dx*rays-14.798;yy=cy+dy*rays+2.45465;u=xx*ca-yy*sa;v=xx*sa+yy*ca
        w=np.interp(v,foot_levels,widths);h=np.interp(v,foot_levels,heights);mid=(h+.65)*.5;half=np.maximum((h-.65)*.5,.1)
        valid=(v>=-7)&(v<=24)&((u/w)**2+((z-mid)/half)**2<=1)
        if np.any(valid):rf=float(rays[np.flatnonzero(valid)[-1]])
    radius=(rs**10+rf**10)**.1
    wrinkle=.115*math.sin(z*2.05+math.sin(theta)*1.8)*math.exp(-((z-14)/4.6)**2)
    radius+=wrinkle+offset;lift=(top(theta)-38.45)*smooth(35.3,38.45,z)
    return np.array([sign*(cx+radius*dx),cy+radius*dy,z+lift])
def shaft_path(side,theta,zs,offset=.04):return [point(side,theta(z) if callable(theta) else theta,z,offset) for z in zs]
def strip(name,side,theta,z0,z1,width,slot):
    verts=[];faces=[]
    for z in np.linspace(z0,z1,45):
        for t in np.linspace(theta-width*.5,theta+width*.5,4):verts.append(point(side,t,z,.028))
    for j in range(44):
        for i in range(3):a=j*4+i;faces.append([a,a+1,a+5,a+4])
    return g.mesh_object(name,verts,faces,side,'flex',slot,thickness=.065)
def star(name,side,theta,z,radius,slot=2,depth=.065):
    c=point(side,theta,z,.065);sg=1 if side=='l' else -1;n=np.array([sg*math.sin(theta),math.cos(theta),0.]);a=np.array([sg*math.cos(theta),-math.sin(theta),0.]);b=np.array([0,0,1.]);verts=[]
    for lift in (0,depth):
        for i in range(16):
            t=math.tau*i/16;rr=radius*(1 if i%4==0 else .72 if i%2==0 else .24);verts.append(c+rr*(math.sin(t)*a+math.cos(t)*b)+lift*n)
    faces=[list(reversed(range(16))),list(range(16,32))]
    faces.extend([i,(i+1)%16,(i+1)%16+16,i+16] for i in range(16));return g.mesh_object(name,verts,faces,side,'calf' if z>20 else 'flex',slot,bevel=.014 if radius>.5 else 0.)

for side,sign in [('l',1),('r',-1)]:
    nr=96;outer=list(np.r_[np.linspace(1.55,12,24),np.linspace(12.8,37.9,32),38.25,38.45]);rows=[(z,0,False) for z in outer]+[(38.48,-.12,True),(38.37,-.29,True)]+[(z,-.30,True) for z in reversed(outer[:-1])];verts=[];faces=[];slots=[]
    for z,off,inner in rows:
        left,right=bounds(z);ts=np.r_[np.linspace(left,right,32,endpoint=False),np.linspace(right,left+math.tau,64,endpoint=False)]
        verts.extend(point(side,float(t),z,off) for t in ts)
    for j in range(len(rows)):
        for i in range(nr):
            faces.append([j*nr+i,j*nr+(i+1)%nr,((j+1)%len(rows))*nr+(i+1)%nr,((j+1)%len(rows))*nr+i])
            slots.append(4 if rows[j][2] else 1 if i<32 and rows[j][0]>=8.5 else 0)
    upper=g.mesh_object('ContinuousUpper_'+side,verts,faces,side,'flex',0)
    for name in SLOTS:upper.data.materials.append(bpy.data.materials.get(name) or bpy.data.materials.new(name))
    for poly,slot in zip(upper.data.polygons,slots):poly.material_index=slot
    upper['per_face_slots']=True
    # Panel piping and stitches follow the actual continuous shell, not a second shaft.
    for edge in (0,1):
        g.tube('SilverPanelPiping_%s_%d'%(side,edge),shaft_path(side,lambda z:bounds(z)[edge],np.linspace(8.7,38.38,96),.04),.028,side,'flex',2,False,5)
        delta=-.025 if edge==0 else .025
        g.tube('PanelStitch_%s_%d'%(side,edge),shaft_path(side,lambda z:bounds(z)[edge]+delta,np.linspace(8.9,38.2,92),.025),.018,side,'flex',3,False,4)
    g.tube('CuffStitch_'+side,[point(side,t,38.03,.022) for t in np.linspace(0,math.tau,128,endpoint=False)],.018,side,'calf',3,True,4)
    g.tube('RearSeam_'+side,shaft_path(side,math.pi,np.linspace(9,38.15,92),.026),.033,side,'flex',3,False,5)
    # Shallow silver thread curves and eight-point stars are anatomical surface details.
    star('UpperSilverStar_'+side,side,.45,33.4,1.23)
    for sidebranch in (-1,1):
        def stem(z):return .45+sidebranch*(.25+.07*math.sin((z-11)*.42))
        g.tube('VineStem_%s_%s'%(side,sidebranch),shaft_path(side,stem,np.linspace(11.5,32.3,100),.035),.025,side,'flex',2,False,5)
        for j,z0 in enumerate(np.linspace(13,30.6,9)):
            direction=sidebranch*(-1 if j%2 else 1);path=[]
            for t in np.linspace(0,1,14):path.append(point(side,stem(z0)+direction*.12*math.sin(math.pi*t),z0+1.1*t,.04))
            g.tube('VineLeaf_%s_%s_%s'%(side,sidebranch,j),path,.024,side,'flex',2,False,5)
    for z in (18.4,26.1):star('SmallStar_%s_%s'%(side,z),side,.45,z,.38,depth=.028)
    star('SilverClasp_'+side,side,1.52,35.5,.95,depth=.13)
    c=point(side,1.52,35.5,.25);normal=Vector((sign*math.sin(1.52),math.cos(1.52),0));bn=Vector((normal.x,-normal.y,normal.z))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(c[0]*.01,-c[1]*.01,c[2]*.01));gem=bpy.context.object;gem.name='InsetSapphire_'+side;gem.rotation_mode='QUATERNION';gem.rotation_quaternion=bn.to_track_quat('Z','Y');gem.scale=(.0046,.0046,.0022);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);gem['material_slot']=6;gem['side']=side;gem['weight_zone']='calf';g.objects.append(gem)
    for poly in gem.data.polygons:poly.use_smooth=True
    # Inner zipper has a narrow leather facing; teeth and pull remain close to the shaft.
    strip('InnerZipFacing_'+side,side,-math.pi*.5,10.5,36.9,.11,0)
    for t in (-math.pi*.5-.025,-math.pi*.5+.025):g.tube('ZipTape_%s_%s'%(side,t),shaft_path(side,t,np.linspace(11,36.7,92),.085),.032,side,'flex',3,False,5)
    for j,z in enumerate(np.arange(11.2,36.5,.28)):
        t=-math.pi*.5+(.018 if j%2 else -.018);g.tube('ZipTooth_%s_%s'%(side,j),[point(side,t+d,z,.10) for d in [-.015,.015]],.027,side,'flex',2,False,4)
    pull=[point(side,-math.pi*.5+.045*math.sin(t),35.7+.50*math.cos(t),.18) for t in np.linspace(0,math.tau,28,endpoint=False)];g.tube('ZipPull_'+side,pull,.052,side,'calf',3,True,6)
    # Continuous low heel and flexible forefoot sole, including the medial arch.
    verts=[];faces=[];vs=np.linspace(-7.15,24.15,98)
    for v in vs:
        w=float(np.interp(v,foot_levels,widths))+.36;bottom=float(np.interp(v,[-7,-1,2.5,7,10,24],[-.38,-.38,.95,1.02,-.18,-.18]));topz=1.75+max(0,v-20)*.035
        ring=[(-w+.07,bottom), (w-.07,bottom),(w,bottom+.10),(w,topz-.10),(w-.06,topz),(-w+.06,topz),(-w,topz-.10),(-w,bottom+.10)]
        verts.extend(g.foot_point(side,u,float(v),z) for u,z in ring)
    for j in range(len(vs)-1):
        for i in range(8):faces.append([j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i])
    faces.extend([list(reversed(range(8))),list(range((len(vs)-1)*8,len(vs)*8))]);g.mesh_object('LowHeelRubberSole_'+side,verts,faces,side,'foot',5,bevel=.045)
    outline=[g.foot_point(side,float(np.interp(v,foot_levels,widths))+.25,v,1.73) for v in np.linspace(-7.1,24.1,100)]+[g.foot_point(side,-float(np.interp(v,foot_levels,widths))-.25,v,1.73) for v in np.linspace(24.1,-7.1,100)]
    g.tube('LeatherWelt_'+side,outline,.095,side,'foot',0,True,6)
    for j,v in enumerate(list(np.linspace(-5.9,-1.4,5))+list(np.linspace(10.4,22.9,12))):
        w=float(np.interp(v,foot_levels,widths))-.25;bottom=-.43 if v<0 else -.23
        for flank in (-1,1):
            center=.52*w*flank;half=.38*w;pts=[g.foot_point(side,center+u,v+vv,bottom+zz) for u in (-half,half) for vv in (-.22,.22) for zz in (-.10,.08)]
            g.mesh_object('Tread_%s_%s_%s'%(side,j,flank),pts,[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]],side,'foot',5,bevel=.025)

data={k:[] for k in ('positions','triangles','weights','uv','normals','triangle_materials','parts')}
for ob in g.objects:
    mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active;start=len(data['positions']);pts=np.array([(v.co.x*100,-v.co.y*100,v.co.z*100) for v in mesh.vertices]);data['positions'].extend(pts.tolist())
    for p in pts:
        ws=g.skin(ob['side'],p,ob['weight_zone']);total=sum(ws.values());data['weights'].append([[int(k),float(v/total)] for k,v in ws.items() if v>1e-7])
    count=0
    for tri in mesh.loop_triangles:
        p=pts[list(tri.vertices)]
        if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-9:continue
        data['triangles'].append([start+i for i in tri.vertices]);mapped=np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops]);data['uv'].append(g.valid_uv(mapped,p).tolist());data['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops]);data['triangle_materials'].append(int(tri.material_index if ob.get('per_face_slots') else ob['material_slot']));count+=1
    data['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(pts),triangles=count,material=int(ob['material_slot'])))
data.update(source=native['source'],skeleton=native['skeleton'],bones=native['bones'],material_slots=SLOTS,contract='BlueMageBoots V1: continuous native foot-to-shaft hollow upper, inset cobalt panels, real cuff thickness, silver stars/vines, inner zip, low heel; native calf-foot-ball articulation; high-boot fit envelope plus 3.5mm allowance')
write(R/'Authored/Jason_BlueMageBoots_Garment.json',data);write(R/'Authored/Jason_BlueMageBoots.json',data);write(R/'native_reference.json',native)
# The display is one empty left boot; pickup and wearable retain the pair.
single=copy.deepcopy(data);keep=[i for i,p in enumerate(data['positions']) if p[0]>0];remap={old:new for new,old in enumerate(keep)};fi=[i for i,f in enumerate(data['triangles']) if all(v in remap for v in f)]
single['positions']=[data['positions'][v] for v in keep];single['weights']=[data['weights'][v] for v in keep];single['triangles']=[[remap[v] for v in data['triangles'][i]] for i in fi]
for k in ('uv','normals','triangle_materials'):single[k]=[data[k][i] for i in fi]
single['parts']=[];write(R/'Authored/Display.json',single)
write(R/'boot_profile.json',dict(levels=[4,8,12,18,24,30,36,40],fields=[profile(z).tolist() for z in [4,8,12,18,24,30,36,40]],shaft_top_cm=[38.27,38.9],body_covers=[4,11,13,15,16],trouser_fit_contract='Reuse current ue_armored_boots high-fit variants; new shaft has 3.5mm additional exterior allowance and same native calf basis'))
write(R/'construction_receipt.json',dict(reference='Design/blue-mage-boots-concept-v01.png',vertices=len(data['positions']),triangles=len(data['triangles']),parts=len(data['parts']),body_source=native['source'],runtime_tested=False))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports/BlueMageBoots_Construction.blend'));print('MAGE_BOOTS_GEOMETRY_AUTHORED',len(data['positions']),len(data['triangles']),flush=True)
