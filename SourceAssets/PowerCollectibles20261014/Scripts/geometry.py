"""Editable centimetre-scale manufactured solids, original authoring helpers."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'texture_manifest.json').read_text('utf8'))
PARTS=[];MAT=None;COLLISIONS=[]

def select(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def rect(region):
    x0,y0,x1,y1=SPEC['regions'][region];pad=12
    return ((x0+pad)/4096,1-(y1-pad)/4096,(x1-pad)/4096,1-(y0+pad)/4096)

def uv(o,region):
    if o.get('authored_decal'):return
    m=o.data;m.update();layer=m.uv_layers.active or m.uv_layers.new(name='SurfaceAtlas')
    # Blender primitives start with UVMap; custom solids start without a layer.
    # Joining different layer names would zero-fill the missing channel on each part.
    layer.name='SurfaceAtlas'
    pts=[v.co for v in m.vertices]
    lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
    u0,v0,u1,v1=rect(region)
    for f in m.polygons:
        axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=(0,1) if axis==2 else (0,2) if axis==1 else (1,2)
        # Separate cube-projection charts prevent opposing tangent directions sharing UV corners.
        chart=axis*2+(1 if f.normal[axis]<0 else 0)
        chart_x=(chart%3)/3+.015;chart_y=(chart//3)/2+.015
        for li in f.loop_indices:
            p=m.vertices[m.loops[li].vertex_index].co
            u=(p[a]-lo[a])/max(hi[a]-lo[a],1e-6);v=(p[b]-lo[b])/max(hi[b]-lo[b],1e-6)
            if f.normal[axis]<0:u=1-u
            layer.data[li].uv=(u0+(chart_x+u*.30)*(u1-u0),v0+(chart_y+v*.47)*(v1-v0))

def register(o,name,region):
    o.name=name;o['surface_region']=region;o.data.materials.clear();o.data.materials.append(MAT)
    uv(o,region);PARTS.append(o);return o

def normals(m):
    bm=bmesh.new();bm.from_mesh(m)
    bmesh.ops.dissolve_degenerate(bm,dist=.0001,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free();m.update()

def mesh(name,verts,faces,region='plastic',smooth=False):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);normals(m)
    o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o)
    for f in m.polygons:f.use_smooth=smooth
    return register(o,name,region)

def bevel(o,r=.06,segments=4):
    if r<=0:return o
    m=o.modifiers.new('Manufactured edge radius','BEVEL');m.width=r;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=math.radians(32);m.use_clamp_overlap=True;m.harden_normals=True
    for f in o.data.polygons:f.use_smooth=True
    w=o.modifiers.new('Face weighted workshop normals','WEIGHTED_NORMAL');w.keep_sharp=True;w.weight=45
    return o

def box(name,p,size,region='plastic',r=.06):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    register(o,name,region);return bevel(o,r)

def rr(w,h,r,n=12):
    r=min(r,w*.49,h*.49);pts=[]
    for cx,cy,start in ((w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)):
        for j in range(n):
            t=math.radians(start+90*j/(n-1));pts.append((cx+r*math.cos(t),cy+r*math.sin(t)))
    return pts

def loft(name,sections,region='plastic',n=12):
    # z, width, length, corner radius, x offset, y offset
    verts=[];faces=[]
    for z,w,h,r,x,y in sections:verts.extend((u+x,v+y,z) for u,v in rr(w,h,r,n))
    count=n*4
    for i in range(len(sections)-1):
        for j in range(count):k=(j+1)%count;faces.append((i*count+j,i*count+k,(i+1)*count+k,(i+1)*count+j))
    faces.extend((tuple(reversed(range(count))),tuple((len(sections)-1)*count+j for j in range(count))))
    o=mesh(name,verts,faces,region,True)
    o.data.polygons[-1].use_smooth=False;o.data.polygons[-2].use_smooth=False
    return o

def rounded(name,p,size,region='plastic',r=.4,edge=.05):
    w,h,d=size
    o=loft(name,[(-d/2,w,h,r,0,0),(d/2,w,h,r,0,0)],region)
    o.location=p
    return bevel(o,edge,3)

def frame(name,p,size,wall,region='plastic',r=.6):
    x,y,z=p;w,h,d=size;n=48;verts=[];faces=[]
    for zz,ww,hh,rrr in ((z-d/2,w,h,r),(z+d/2,w,h,r),(z+d/2,w-wall*2,h-wall*2,max(.08,r-wall)),(z-d/2,w-wall*2,h-wall*2,max(.08,r-wall))):
        verts.extend((x+u,y+v,zz) for u,v in rr(ww,hh,rrr,12))
    for i in range(4):
        for j in range(n):k=(j+1)%n;faces.append((i*n+j,i*n+k,((i+1)%4)*n+k,((i+1)%4)*n+j))
    return bevel(mesh(name,verts,faces,region,True),.025,3)

def extrude(name,outline,z,depth,region='steel',r=.04):
    n=len(outline);vs=[(x,y,z+d) for d in (-depth/2,depth/2) for x,y in outline]
    fs=[tuple(reversed(range(n))),tuple(n+j for j in range(n))]
    fs.extend((j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n))
    return bevel(mesh(name,vs,fs,region),r)

def orient(o,axis):
    if axis=='X':o.rotation_euler[1]=math.pi/2
    elif axis=='Y':o.rotation_euler[0]=math.pi/2
    return o

def lathe(name,p,profile,region='steel',axis='Z',segments=72,closed=True):
    # Closed radial profile supports actual bores and recessed sockets.
    vs=[];fs=[]
    for z,r in profile:
        vs.extend((r*math.cos(j*2*math.pi/segments),r*math.sin(j*2*math.pi/segments),z) for j in range(segments))
    for i in range(len(profile) if closed else len(profile)-1):
        k=(i+1)%len(profile)
        for j in range(segments):q=(j+1)%segments;fs.append((i*segments+j,i*segments+q,k*segments+q,k*segments+j))
    o=mesh(name,vs,fs,region,True);o.location=p;orient(o,axis);return o

def cylinder(name,p,r,h,region='steel',axis='Z',sides=64,edge=.025):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=h,location=p)
    o=bpy.context.object;orient(o,axis);register(o,name,region);return bevel(o,min(edge,h*.22,r*.25),3)

def ring(name,p,outer,inner,h,region='steel',axis='Z',sides=72):
    return lathe(name,p,[(-h/2,outer),(h/2,outer),(h/2,inner),(-h/2,inner)],region,axis,sides)

def cut(o,p,size,r=.05):
    tool=rounded('temporary milling cutter',p,size,'plastic',r,0)
    PARTS.remove(tool);select(o);mod=o.modifiers.new('Machined cavity','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
    while o.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True);normals(o.data);uv(o,o['surface_region'])

def screw(name,p,r=.17,axis='Z'):
    # Ring and shaped recessed drive have genuine depth, not a cross painted on a disc.
    o=ring(name+' head',p,r,r*.47,.09,'steel',axis,36)
    q=Vector(p);delta=Vector((0,0,1)) if axis=='Z' else Vector((1,0,0)) if axis=='X' else Vector((0,-1,0))
    cylinder(name+' drive floor',q-delta*.05,r*.47,.025,'blacksteel',axis,12,0)
    return o

def cord(name,points,r=.09,region='rubber',res=8):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=res;c.bevel_depth=r;c.bevel_resolution=4;c.use_fill_caps=True
    s=c.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
    for b,p in zip(s.bezier_points,points):b.co=p;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);select(o);bpy.ops.object.convert(target='MESH');return register(o,name,region)

def panel(name,p,w,h,region,axis='Z'):
    ux=Vector((1,0,0));vy=Vector((0,1,0))
    if axis=='-Y':vy=Vector((0,0,1))
    elif axis=='Y':ux=Vector((-1,0,0));vy=Vector((0,0,1))
    elif axis=='X':ux=Vector((0,1,0));vy=Vector((0,0,1))
    elif axis=='-X':ux=Vector((0,-1,0));vy=Vector((0,0,1))
    elif axis=='-Z':vy=Vector((0,-1,0))
    vs=[tuple(Vector(p)+ux*x+vy*y) for x,y in ((-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2))]
    o=mesh(name,vs,[(0,1,2,3)],region);o['authored_decal']=True
    u0,v0,u1,v1=rect(region)
    coordinates=((u0,v0),(u1,v0),(u1,v1),(u0,v1))
    # BMesh may rotate a face's loop start while recalculating normals.
    for li in o.data.polygons[0].loop_indices:o.data.uv_layers.active.data[li].uv=coordinates[o.data.loops[li].vertex_index]
    return o

def stamp(name,text,p,size=.22,region='white',rot=(0,0,0)):
    c=bpy.data.curves.new(name,'FONT');c.body=text;c.size=size;c.align_x='CENTER';c.align_y='CENTER';c.extrude=.0015;c.resolution_u=5
    o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.location=p;o.rotation_euler=rot
    select(o);bpy.ops.object.convert(target='MESH');return register(o,name,region)

def transform_since(start,matrix):
    bpy.context.view_layer.update()
    for o in PARTS[start:]:o.matrix_world=matrix@o.matrix_world

def material(key):
    spec=SPEC['assets'][key];m=bpy.data.materials.new(spec['material']);m.use_nodes=True
    nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF');textures={}
    for kind,path in spec['textures'].items():
        t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(path);t.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';t.image.pack();textures[kind]=t
    links.new(textures['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(textures['ORM'].outputs['Color'],split.inputs['Color'])
    links.new(split.outputs['Green'],bs.inputs['Roughness']);links.new(split.outputs['Blue'],bs.inputs['Metallic'])
    n=nodes.new('ShaderNodeNormalMap');links.new(textures['Normal'].outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
    return m
