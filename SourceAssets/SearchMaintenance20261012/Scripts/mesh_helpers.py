"""Four original, centimeter-scale collectible models. Author/export only; no render."""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'texture_manifest.json').read_text('utf-8'))
REGIONS=SPEC['regions'];PARTS=[];MAT=None
OUT=ROOT/'Export';OUT.mkdir(exist_ok=True)
MASTER=ROOT/'Authored';MASTER.mkdir(exist_ok=True)

def select(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def uv_rect(region):
    x0,y0,x1,y1=REGIONS[region];pad=8
    return ((x0+pad)/4096,1-(y1-pad)/4096,(x1-pad)/4096,1-(y0+pad)/4096)

def project_uv(o,region):
    if o.type!='MESH':return
    mesh=o.data;mesh.update()
    layer=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
    points=[v.co for v in mesh.vertices]
    low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
    u0,v0,u1,v1=uv_rect(region)
    for face in mesh.polygons:
        axis=max(range(3),key=lambda k:abs(face.normal[k]))
        a,b=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            u=(p[a]-low[a])/max(high[a]-low[a],1e-6)
            v=(p[b]-low[b])/max(high[b]-low[b],1e-6)
            if face.normal[axis]<0:u=1-u
            layer.data[li].uv=(u0+u*(u1-u0),v0+v*(v1-v0))

def register(o,name,region):
    o.name=name;o.data.materials.clear();o.data.materials.append(MAT)
    o['surface_region']=region;project_uv(o,region);PARTS.append(o)
    return o

def bevel(o,width,segments=4):
    if width<=0:return o
    mod=o.modifiers.new('Manufactured edge radii','BEVEL');mod.width=width;mod.segments=segments
    mod.limit_method='ANGLE';mod.angle_limit=math.radians(35);mod.use_clamp_overlap=True;mod.harden_normals=True
    for p in o.data.polygons:p.use_smooth=True
    normal=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=40
    return o

def box(name,p,size,region='plastic',radius=.03,segments=4):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p)
    o=bpy.context.object;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    register(o,name,region);bevel(o,radius,segments)
    return o

def cut(o,p,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);tool=bpy.context.object;tool.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    select(o);mod=o.modifiers.new('Real opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
    while o.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
    project_uv(o,o['surface_region'])

def cylinder(name,p,r,depth,region='steel',axis='Z',sides=40,radius=.01):
    rotation=(0,math.pi/2,0) if axis=='X' else (math.pi/2,0,0) if axis=='Y' else (0,0,0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=depth,location=p,rotation=rotation)
    o=bpy.context.object;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    register(o,name,region);bevel(o,radius,3)
    return o

def ring(name,p,outer,inner,depth,region='steel',axis='Z',sides=48):
    verts=[];faces=[]
    for z,r in ((-depth/2,outer),(depth/2,outer),(-depth/2,inner),(depth/2,inner)):
        for j in range(sides):
            t=2*math.pi*j/sides;point=(r*math.cos(t),r*math.sin(t),z)
            if axis=='X':point=(point[2],point[1],-point[0])
            if axis=='Y':point=(point[0],point[2],-point[1])
            verts.append(point)
    for j in range(sides):
        k=(j+1)%sides
        faces += [(j,k,sides+k,sides+j),(2*sides+k,2*sides+j,3*sides+j,3*sides+k),
                  (sides+j,sides+k,3*sides+k,3*sides+j),(k,j,2*sides+j,2*sides+k)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);o.location=p
    register(o,name,region);bevel(o,.008,2)
    return o

def panel(name,p,w,h,region='primary',axis='Z'):
    ux=Vector((1,0,0));vy=Vector((0,1,0))
    if axis=='FRONT':vy=Vector((0,0,1))
    elif axis=='BACK':ux=Vector((-1,0,0));vy=Vector((0,0,1))
    elif axis=='BOTTOM':vy=Vector((0,-1,0))
    vertices=[tuple(Vector(p)+ux*x+vy*y) for x,y in ((-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2))]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],[(0,1,2,3)]);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);register(o,name,region)
    u0,v0,u1,v1=uv_rect(region)
    for li,co in zip(mesh.polygons[0].loop_indices,((u0,v0),(u1,v0),(u1,v1),(u0,v1))):mesh.uv_layers.active.data[li].uv=co
    return o

def screw(name,p,r=.12,axis='Z'):
    head=cylinder(name,p,r,.06,'steel',axis,28,.007)
    if axis=='Z':
        cut(head,(p[0],p[1],p[2]+.04),(r*1.5,r*.20,.045))
        cut(head,(p[0],p[1],p[2]+.04),(r*.20,r*1.5,.045))
    elif axis=='Y':
        cut(head,(p[0],p[1]-.04,p[2]),(r*1.5,.045,r*.20))
        cut(head,(p[0],p[1]-.04,p[2]),(r*.20,.045,r*1.5))
    return head

def cord(name,points,thickness=.045,region='kraft'):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=12
    spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for b,p in zip(spline.bezier_points,points):b.co=p;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
    curve.bevel_depth=thickness;curve.bevel_resolution=3;curve.resolution_u=12
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o)
    select(o);bpy.ops.object.convert(target='MESH');register(o,name,region)
    return o

def sheet(name,p,size,region='paper',curl=0):
    nx,ny=14,10;verts=[];faces=[];w,h,t=size
    for layer in (0,1):
        for y in range(ny+1):
            for x in range(nx+1):
                u=x/nx;v=y/ny
                lift=curl*max(0,(u-.58)/.42)**2*max(0,(.5-v)/.5)**2
                lift+=curl*.10*math.sin(u*math.pi)*math.sin(v*math.pi)
                verts.append((p[0]+(u-.5)*w,p[1]+(v-.5)*h,p[2]+lift+(layer-.5)*t))
    n=(nx+1)*(ny+1)
    for y in range(ny):
        for x in range(nx):
            a=y*(nx+1)+x;b=a+1;c=b+nx+1;d=a+nx+1
            faces.extend(((d,c,b,a),(a+n,b+n,c+n,d+n)))
    perimeter=list(range(nx+1))+[y*(nx+1)+nx for y in range(1,ny+1)]+[ny*(nx+1)+x for x in range(nx-1,-1,-1)]+[y*(nx+1) for y in range(ny-1,0,-1)]
    for i,a in enumerate(perimeter):
        b=perimeter[(i+1)%len(perimeter)];faces.append((a,b,b+n,a+n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);register(o,name,region)
    for poly in mesh.polygons:poly.use_smooth=True
    return o

def make_material(key):
    spec=SPEC['assets'][key]
    m=bpy.data.materials.new(spec['material']);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');nodes=m.node_tree.nodes;links=m.node_tree.links
    images={}
    for kind,path in spec['textures'].items():
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(path);tex.image.pack()
        tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';images[kind]=tex
    links.new(images['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(images['ORM'].outputs['Color'],split.inputs['Color'])
    links.new(split.outputs['Green'],bs.inputs['Roughness']);links.new(split.outputs['Blue'],bs.inputs['Metallic'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.65
    links.new(images['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    return m
