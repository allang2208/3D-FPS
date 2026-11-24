"""Build nine fitted, interchangeable game meshes on the saved Frontier R2 reference."""
import json, math
from pathlib import Path
import bpy, bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
OUT = HERE/'Export'
OUT.mkdir(exist_ok=True)
TAU = math.tau
TILES = 'graphite steel bronze cyan recess mark wax weave thin pad thread fast twist soft serving rubber'.split()
SHARED = 'M_FrontierMods_Surface'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
with bpy.data.libraries.load(str(HERE.parent/'RigContactR2/FrontierCompoundBow_R2.blend')) as (src,dst):
    dst.objects = ['Grip','Riser']
grip_src, riser_src = dst.objects
for obj in dst.objects: scene.collection.objects.link(obj)

def bvh(obj):
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return BVHTree.FromPolygons(verts, [list(p.vertices) for p in obj.data.polygons])
grip_tree, riser_tree = bvh(grip_src), bvh(riser_src)
atlas = bpy.data.materials.new(SHARED)
atlas.use_nodes = True
nodes,links = atlas.node_tree.nodes, atlas.node_tree.links
bs = nodes.get('Principled BSDF')
for k in ('Color','Normal','ORM'):
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(HERE/'Textures'/f'T_FrontierMods_{k}.png'))
    if k=='Color': links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    else:
        tex.image.colorspace_settings.name='Non-Color'
        if k=='Normal':
            normal=nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'],normal.inputs['Color']); links.new(normal.outputs[0],bs.inputs['Normal'])
        else:
            channels=nodes.new('ShaderNodeSeparateColor'); links.new(tex.outputs[0],channels.inputs[0])
            links.new(channels.outputs['Green'],bs.inputs['Roughness']); links.new(channels.outputs['Blue'],bs.inputs['Metallic'])
glass={}
for power in (2,4):
    m=bpy.data.materials.new(f'M_BowOptic_Glass{power}x');m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.65,.86,.78,1)
    p.inputs['Transmission Weight'].default_value=1.;p.inputs['Roughness'].default_value=.045
    glass[power]=m

def cell(style,u,v):
    row,col=divmod(TILES.index(style),4)
    return ((col+.025+.95*u)/4,(3-row+.025+.95*v)/4) if style in TILES else (u,v)

def unit(v): return Vector(v).normalized()
def wave(x): return math.sin(x)
class Surface:
    def __init__(self):
        self.verts=[];self.faces=[];self.uv=[];self.styles=[];self.smooth=[]
    def face(self,indices,uv,style,smooth=True):
        self.faces.append(indices);self.styles.append(style);self.smooth.append(smooth)
        self.uv.append([cell(style,*p) if style in TILES else p for p in uv])
    def rings(self,rings,styles,periodic=False,smooth=True):
        base=len(self.verts);rows=len(rings);n=len(rings[0])
        for ring in rings:self.verts.extend(ring)
        span=rows if periodic else rows-1
        for j in range(span):
            k=(j+1)%rows
            for i in range(n):
                h=(i+1)%n
                self.face([base+j*n+i,base+j*n+h,base+k*n+h,base+k*n+i],
                          [(i/n,j/span),((i+1)/n,j/span),((i+1)/n,(j+1)/span),(i/n,(j+1)/span)],
                          styles[j] if isinstance(styles,list) else styles,smooth)
    def tube(self,path,radius,style,sides=7,closed=False):
        path=[Vector(p) for p in path]; rings=[];previous=None
        for i,p in enumerate(path):
            t=unit(path[(i+1)%len(path)]-path[(i-1)%len(path)]) if closed else unit(path[min(i+1,len(path)-1)]-path[max(i-1,0)])
            normal=t.orthogonal().normalized() if previous is None else unit(previous-t*previous.dot(t))
            previous=normal;across=t.cross(normal);r=radius(i/(len(path)-1)) if callable(radius) else radius
            rings.append([p+r*(normal*math.cos(TAU*k/sides)+across*wave(TAU*k/sides)) for k in range(sides)])
        self.rings(rings,style,closed)
    def lathe(self,center,axis,profile,style,sides=64,flutes=0,depth=0):
        axis=unit(axis);u=Vector((0,1,0)) if abs(axis.x)>.99 else Vector((1,0,0))
        u=unit(u-axis*axis.dot(u));v=axis.cross(u);center=Vector(center)
        rings=[]
        for h,r,relief in profile:
            ring=[]
            for j in range(sides):
                t=TAU*j/sides; rr=r+relief*depth*(.5+.5*math.cos(flutes*t))**2
                ring.append(center+axis*h+(u*math.cos(t)+v*wave(t))*rr)
            rings.append(ring)
        self.rings(rings,style,True)
    def solid(self,points,offset,style):
        # Two polygon faces and a bevel around the perimeter.
        pts=[Vector(p) for p in points];off=Vector(offset);c=sum(pts,Vector())/len(pts)
        rings=[[c+(p-c)*.91 for p in pts],[p+off*.16 for p in pts],[p+off*.84 for p in pts],[c+(p-c)*.91+off for p in pts]]
        base=len(self.verts);self.rings(rings,style,smooth=False)
        n=len(pts);uv=[(.5+(p-c).x*.09,.5+(p-c).z*.09) for p in pts]
        self.face(list(reversed(range(base,base+n))),list(reversed(uv)),style,False)
        self.face(list(range(base+3*n,base+4*n)),uv,style,False)
    def mesh(self,name):
        data=bpy.data.meshes.new(name);data.from_pydata(self.verts,[],self.faces);data.update()
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
        data.materials.append(atlas);uv=data.uv_layers.new(name='Surface')
        for p,style,coords,sm in zip(data.polygons,self.styles,self.uv,self.smooth):
            p.use_smooth=sm
            if isinstance(style,int):
                mat=glass[style]
                if mat.name not in data.materials:data.materials.append(mat)
                p.material_index=data.materials.find(mat.name)
            for li,xy in zip(p.loop_indices,coords):uv.data[li].uv=xy
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        return obj

def export(obj,rig=None,output=OUT):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in ([obj,rig] if rig else [obj]):ob.select_set(True)
    bpy.context.view_layer.objects.active=rig or obj
    bpy.ops.export_scene.fbx(filepath=str(output/(obj.name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'} if rig else {'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')

def skinpoint(angle,z,lift=0.):
    d=Vector((math.cos(angle),wave(angle),0))
    center=Vector((.64+.45*z,-.015,z))
    point,_,_,_=grip_tree.ray_cast(center+d*9,-d,14)
    if point is None:raise ValueError(('Missing native grip surface',angle,z))
    return point+d*lift

def lip(g,z,style,radius):
    g.tube([skinpoint(TAU*i/80,z,.045) for i in range(80)],radius,style,8,True)

def make_grip(style,label):
    g=Surface();n=64
    z0,z1=-3.94,4.23
    def outline(z,a):
        t=(z-z0)/(z1-z0);fade=min(1,max(0,min(t,1-t)*18))
        relief=.066
        if style=='pad':
            # Low, segmented cushion lobes fade before reaching the native end fittings.
            relief+=.11*(.5+.5*math.cos(TAU*(t*4.2+.08*math.sin(a))))**.6*(.65+.35*math.cos(2*a))
        elif style=='wax':relief+=.034*(.5+.5*math.cos(7*TAU*t-a))**2
        elif style=='weave':relief+=.023*(.5+.5*math.cos(10*a+TAU*8*t))*(.5+.5*math.cos(10*a-TAU*8*t))
        return skinpoint(a,z,.022+fade*relief)
    rows=52
    g.rings([[outline(z0+(z1-z0)*j/rows,TAU*i/n) for i in range(n)] for j in range(rows+1)],style)
    if style=='wax':
        for q in (0,.16):
            pts=[skinpoint(TAU*(6.25*i/420+q/6.25),z0+.19+(z1-z0-.38)*i/420,.097) for i in range(421)]
            g.tube(pts,.025 if q==0 else .012,'thin' if q==0 else 'thread',6)
    elif style=='weave':
        for sign in (-1,1):
            for start in range(6):
                pts=[]
                for i in range(101):
                    t=i/100;a=TAU*(start/6+sign*.85*t);z=z0+.22+(z1-z0-.44)*t
                    pts.append(skinpoint(a,z,.094+.014*math.cos(12*a-sign*t*TAU*10)))
                g.tube(pts,.025,'weave' if start%3 else 'twist',6)
    elif style=='thin':
        for a in (1.24,1.41):
            for i in range(21):
                z=z0+.32+i*.365
                g.tube([skinpoint(a+.032*t,z+.19*t,.092+.018*wave(t*math.pi)) for t in (0,.33,.66,1)],.022,'thread',6)
    else:
        for i in range(4):
            z=z0+1.03+i*1.79
            g.tube([skinpoint(TAU*j/96,z+.13*math.cos(TAU*j/96),.095) for j in range(96)],.027,'recess',7,True)
        for a in (1.1,1.95):
            for i in range(15):
                z=z0+.40+i*.5
                g.tube([outline(z+.24*t,a+.022*t)+Vector((0,.029,0)) for t in (0,.5,1)],.028,'thread',6)
    for z in (z0+.08,z1-.08):lip(g,z,'rubber' if style in ('weave','pad') else style,.055)
    obj=g.mesh(label)
    core=grip_src.copy();core.data=grip_src.data.copy();scene.collection.objects.link(core)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);core.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    export(obj)
    return obj

AIM=Vector((-1.325,4.186,16.179))
def riser_side(x,z):
    p,_,_,_=riser_tree.ray_cast(Vector((x,12,z)),Vector((0,-1,0)),18)
    if p is None:raise ValueError(('Missing native sight surface',x,z))
    return p

def screw(g,center,axis,r):
    # Machined head, recessed dark hex well and its physical floor.
    g.lathe(center,axis,[(-.035,r*.9,0),(0,r,0),(.10,r*.87,0),(.10,r*.45,0),(.04,r*.40,0),(.04,.002,0),(-.035,.002,0)],
            ['graphite','steel','graphite','recess','recess','recess','graphite'],12)

def make_optic(power,name,aim=AIM,yaw=0.,output=OUT):
    turn=Matrix.Rotation(math.radians(yaw),3,'Z')
    g=Surface();accent='cyan' if power==2 else 'bronze';r=1.76 if power==2 else 1.94
    # Conform the back of the shoe to the side of the saved R2 riser.
    seat=[riser_side(x,z) for x,z in [(-.15,14.42),(1.24,14.35),(1.47,14.55),(1.48,15.40),(1.26,15.64),(-.06,15.63),(-.25,15.41),(-.28,14.68)]]
    seat=[p-Vector((0,.075,0)) for p in seat];g.solid(seat,(0,.54,0),'graphite')
    for x,z in ((.03,14.62),(1.19,15.43)):
        p=riser_side(x,z);screw(g,p+Vector((0,.48,0)),(0,1,0),.195)
    # Two distinct rails make a visible opening below the optic rather than a solid slab.
    y=1.90
    for front in (False,True):
        shift=.91 if front else 0
        foot=Vector((.13+shift,y,14.83+.23*front))
        end=aim+turn@Vector((-.42+shift,-.22,-r+.04))
        mid=foot.lerp(end,.51)+Vector((.10,.16,-.26))
        points=[foot,mid,end]; width=.27 if front else .33
        side=Vector((width,0,0))
        g.solid([p-side for p in points]+[p+side for p in reversed(points)],(0,0,.34),'graphite')
    barrel_start=len(g.verts)
    half=.42 if power==2 else 1.12
    profile=[(-half-.09,r-.19,0),(-half-.09,r-.04,0),(-half+.03,r+.06,1),(half-.10,r+.06,1),
             (half+.06,r-.03,0),(half+.06,r-.18,0),(half-.05,r-.23,0),(-half+.04,r-.23,0)]
    g.lathe(aim,(1,0,0),profile,['recess','steel','graphite','graphite','graphite','recess','recess','recess'],
            sides=120,flutes=12 if power==4 else 6,depth=.085 if power==4 else .037)
    g.lathe(aim,(1,0,0),[(-half+.10,r+.067,0),(-half+.14,r+.084,0),(-half+.20,r+.084,0),(-half+.23,r+.06,0)],accent)
    if power==4:
        g.lathe(aim,(1,0,0),[(.37,r+.065,0),(.42,r+.12,1),(.70,r+.12,1),(.76,r+.06,0)],'rubber',120,30,.07)
    knob=aim+Vector((.10,r,0))
    g.lathe(knob,(0,1,0),[(0,.35,0),(.12,.39,1),(.37,.39,1),(.45,.30,0),(.45,.008,0),(0,.008,0)],
            ['graphite','graphite','steel','graphite','recess','recess'],60,15,.037)
    for i in range(7):
        a=math.radians(40+9*i);d=Vector((0,math.cos(a),wave(a)))
        p=aim+Vector((-half-.094,0,0))
        g.tube([p+d*(r-.075),p+d*(r-(.15 if i%3 else .20))],.013,'mark',6)
    # Single lens with radial UVs matching the common glass/reticle material.
    n=72; rings=7;clear=r-.195;base=len(g.verts)
    def lensuv(p):return (.5-(p.y-aim.y)/(2*clear),.5+(p.z-aim.z)/(2*clear))
    for side in (-1,1):
        center=len(g.verts);g.verts.append(aim+Vector((side*.095,0,0)))
        for j in range(1,rings+1):
            f=j/rings
            for i in range(n):
                a=TAU*i/n
                g.verts.append(aim+Vector((side*(.035+.06*(1-f*f)),clear*f*math.cos(a),clear*f*wave(a))))
        for i in range(n):
            k=(i+1)%n
            ids=[center,center+1+i,center+1+k];g.face(ids,[lensuv(g.verts[ii]) for ii in ids],power)
        for j in range(1,rings):
            first=center+1+(j-1)*n
            for i in range(n):
                k=(i+1)%n;ids=[first+i,first+i+n,first+k+n,first+k];g.face(ids,[lensuv(g.verts[ii]) for ii in ids],power)
    a=base+1+(rings-1)*n;b=a+1+rings*n
    for i in range(n):
        k=(i+1)%n;ids=[a+i,a+k,b+k,b+i];g.face(ids,[lensuv(g.verts[ii]) for ii in ids],power)
    if yaw:
        # Glass, reticle UVs, bezel and turret rotate as one rigid piece.
        for i in range(barrel_start,len(g.verts)):
            g.verts[i]=aim+turn@(g.verts[i]-aim)
    obj=g.mesh(name);export(obj,output=output);return obj

anchors=json.loads((HERE.parent/'RigContactR2/anchors.json').read_text())
def anchor(key):
    x,y,z=anchors[key];return Vector((x,-y,z))
upper,mid,lower=(anchor(k) for k in ('upper','brace','lower'))
def string_rig():
    if bpy.data.objects.get('Armature'):bpy.data.objects['Armature'].name='R2_ReferenceRig'
    data=bpy.data.armatures.new('Frontier string');rig=bpy.data.objects.new('Armature',data);scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    root=data.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,1,0)
    for name,p in [('upper',upper),('nock',mid),('lower',lower)]:
        b=data.edit_bones.new('string_'+name);b.head=p;b.tail=p+Vector((0,1,0));b.parent=root
    bpy.ops.object.mode_set(mode='OBJECT');return rig

def make_string(style,name,rig,count,radius,pitch):
    g=Surface()
    for tip in (upper,lower):
        axis=unit(tip-mid);side=Vector((0,1,0));cross=unit(axis.cross(side));length=(tip-mid).length
        def path(t): return mid.lerp(tip,t)
        steps=math.ceil(length/pitch*9)
        # Interlocking tracer bundles taper into the same contact at both ends.
        for strand in range(count):
            points=[]
            for i in range(steps+1):
                t=i/steps;a=TAU*(t*length/pitch+strand/count)
                points.append(path(t)+radius*.47*(side*math.cos(a)+cross*wave(a)))
            g.tube(points,radius*.57,style if strand==0 or (count==4 and strand==2) else 'serving',5)
        for start,end in ((0,3.05 if style=='soft' else 2.25),(length-1.5,length)):
            turns=max(8,round((end-start)/.13))
            g.tube([path(start/length),path(end/length)],radius*1.08,'serving',12)
            pts=[]
            for j in range(turns*8+1):
                t=j/(turns*8);a=TAU*turns*t
                pts.append(path((start+(end-start)*t)/length)+radius*1.055*(side*math.cos(a)+cross*wave(a)))
            g.tube(pts,.012,'rubber' if style!='soft' else 'soft',5)
        for gap in ([2.55] if style=='fast' else [3.38,3.64] if style=='soft' else [2.62,2.92]):
            g.tube([path(gap/length),path((gap+.10)/length)],radius*1.10,style,10)
    obj=g.mesh(name);obj.parent=rig;m=obj.modifiers.new('Draw contacts','ARMATURE');m.object=rig
    groups={k:obj.vertex_groups.new(name='string_'+k) for k in ('upper','nock','lower')}
    for v in obj.data.vertices:
        up=v.co.z>=mid.z;point=upper if up else lower
        t=min(1,max(0,(v.co.z-mid.z)/(point.z-mid.z)))
        if t>0:groups['upper' if up else 'lower'].add([v.index],t,'REPLACE')
        if t<1:groups['nock'].add([v.index],1-t,'REPLACE')
    export(obj,rig);return obj

if __name__ == '__main__':
    built=[]
    for style,label in [('wax','WaxWrap'),('weave','WovenWrap'),('thin','SlimHide'),('pad','PaddedHide')]:
        built.append(make_grip(style,'SM_Frontier_'+label))
    for power,label in [(2,'Clearfield2x'),(4,'Farwatch4x')]:built.append(make_optic(power,'SM_Frontier_'+label))
    rig=string_rig()
    for style,label,count,r,pitch in [('fast','FastLine',2,.075,2.6),('twist','LockTwist',3,.099,1.64),('soft','Softcore',4,.106,3.2)]:
        built.append(make_string(style,'SK_Frontier_'+label,rig,count,r,pitch))
    for obj in (grip_src,riser_src):bpy.data.objects.remove(obj,do_unlink=True)
    for mesh in built:
        mesh.hide_set(mesh.name not in ('SM_Frontier_WovenWrap','SM_Frontier_Clearfield2x','SK_Frontier_LockTwist'))
        mesh.hide_render=mesh.hide_get()
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file and Path(bpy.path.abspath(im.filepath)).is_file():im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Frontier_CommonMods.blend'))
    manifest={'meshes':{o.name:{'triangles':len(o.data.polygons),'materials':[m.name for m in o.data.materials if m]} for o in built},
              'aim_cm':[AIM.x,-AIM.y,AIM.z],'anchors':anchors}
    (HERE/'parts.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
