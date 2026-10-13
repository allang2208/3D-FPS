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

def usb():
    # Main metal housing ends at +2.55 cm. The bare connector occupies the left 1.25 cm.
    box('Machined aluminum shell',(.28,0,.5),(4.50,1.88,.92),'aluminum',.17,7)
    box('Upper shell inset',(0,0,.977),(3.28,1.38,.038),'plastic',.10,5)
    box('Printed identity plate',(-.12,0,1.003),(2.95,1.13,.018),'aluminum',.055,4)
    panel('Laser identity print',(-.12,0,1.013),2.81,1.04,'primary')
    for y in (-.89,.89):box('Assembly parting seam',(.25,y,.49),(4.18,.032,.032),'rubber',.008,3)
    cap=box('Rear cap with through lanyard eye',(2.56,0,.5),(.76,1.92,.96),'rubber',.16,6)
    cut(cap,(2.77,0,.5),(.27,.90,1.2))
    for x in (1.73,-1.54):screw('Countersunk assembly screw',(x,.67,.952),.077)
    # Folded USB-A metal walls with a physically open mouth.
    box('Connector upper wall',(-2.32,0,.737),(1.35,1.22,.047),'steel',.018,3)
    box('Connector lower wall',(-2.32,0,.263),(1.35,1.22,.047),'steel',.018,3)
    for y in (-.59,.59):box('Connector folded side',(-2.32,y,.5),(1.35,.05,.43),'steel',.014,3)
    for x in (-2.69,-2.13):
        # Locking windows in the upper and lower folded shell.
        for face in [o for o in PARTS if o.name.startswith('Connector upper') or o.name.startswith('Connector lower')]:
            cut(face,(x,0,.5),(.22,.45,1.0))
    box('Insulating tongue',(-2.14,0,.419),(1.37,.98,.18),'plastic',.025,3)
    for y in (-.34,-.113,.113,.34):box('Gold contact pad',(-2.48,y,.518),(.76,.115,.018),'brass',.014,3)
    box('Connector neck gasket',(-1.69,0,.50),(.12,1.33,.61),'rubber',.055,4)
    panel('Underside serial',(.20,0,.035),2.7,.52,'barcode','BOTTOM')

def tape():
    lower=box('Lower injection molded shell',(0,0,.49),(10.9,9.9,.98),'plastic',.22,6)
    # A real underside hub well remains visible from below.
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=2.55,depth=.72,location=(-.35,.35,.10))
    tool=bpy.context.object;select(lower);mod=lower.modifiers.new('Hub recess','BOOLEAN');mod.object=tool;mod.operation='DIFFERENCE';mod.solver='EXACT'
    while lower.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True);project_uv(lower,'plastic')
    box('Case parting gasket',(0,0,1.005),(10.85,9.85,.055),'rubber',.15,4)
    box('Upper injection molded shell',(0,0,1.51),(10.9,9.9,.98),'plastic',.22,6)
    box('Label inset rim',(-.20,.35,2.006),(8.35,6.65,.035),'rubber',.10,5)
    box('Archive label substrate',(-.20,.35,2.028),(8.07,6.36,.018),'paper',.055,4)
    panel('Archive record print',(-.20,.35,2.039),7.94,6.23,'primary')
    ring('Lower spool well rim',(-.35,.35,.41),2.51,2.31,.16,'rubber',sides=64)
    cylinder('Single reel backing',(-.35,.35,.52),2.31,.14,'plastic',sides=64,radius=.012)
    ring('Drive hub ring',(-.35,.35,.27),1.30,.61,.24,'aluminum',sides=48)
    cylinder('Hub centre seat',(-.35,.35,.34),.59,.15,'plastic',sides=40,radius=.01)
    for j in range(12):
        a=2*math.pi*j/12
        o=box('Drive hub tooth',(-.35+1.36*math.cos(a),.35+1.36*math.sin(a),.23),(.20,.32,.16),'plastic',.025,3)
        o.rotation_euler.z=a
    for x,y in ((-4.72,-4.16),(4.64,-4.16),(-4.72,4.15),(4.64,4.15)):
        cylinder('Screw seat',(x,y,1.995),.25,.035,'rubber',sides=32)
        screw('Shell fastening screw',(x,y,2.015),.15)
    box('Front barcode substrate',(-.72,-4.966,1.23),(7.8,.025,.95),'paper',.035,3)
    panel('Front barcode',(-.72,-4.981,1.23),7.62,.80,'barcode','FRONT')
    box('Write protect recessed guide',(4.14,-4.948,.78),(1.12,.08,.80),'rubber',.05,4)
    box('Write protect slider',(4.37,-5.005,.78),(.48,.13,.49),'seal',.06,4)
    for z in (.66,.80,.94):box('Slider grip rib',(4.37,-5.08,z),(.31,.025,.032),'plastic',.005,2)
    box('Sliding tape access door',(5.43,1.98,1.02),(.11,4.54,1.62),'rubber',.10,4)
    for y in (.10,3.86):box('Access door guide tab',(5.49,y,1.03),(.10,.28,1.13),'plastic',.035,3)
    for x in (-4.7,4.7):
        for y in (-2.4,-1.2,0,1.2,2.4):box('Handling grip ridge',(x,y,1.92),(.18,.56,.14),'plastic',.04,4)
    for y in (-3.6,3.6):box('Underside indexing rail',(0,y,.05),(6.8,.28,.10),'plastic',.03,3)

def case():
    body=box('Protective case lower tub',(0,0,2.55),(23.4,17.4,4.5),'plastic',.52,7)
    cut(body,(0,0,3.50),(22.28,16.28,4.45))
    # A complete interior remains editable under the closed lid.
    box('Interior foam bed',(0,0,1.18),(21.7,15.7,.78),'rubber',.32,5)
    foam=box('Cut foam storage insert',(0,0,2.52),(21.5,15.5,1.95),'rubber',.25,5)
    cut(foam,(-5.8,0,3.0),(5.8,12.4,2.3));cut(foam,(4.3,0,3.0),(10.2,12.4,2.3))
    box('Numbered storage medium',(-5.8,0,2.30),(4.7,10.5,.95),'aluminum',.12,4)
    panel('Media serial',(-5.8,0,2.781),4.10,1.28,'barcode')
    box('Sealed interior document wallet',(4.3,0,2.22),(9.6,11.9,.35),'kraft',.12,4)
    panel('Interior custody note',(4.3,0,2.40),8.8,10.5,'secondary')
    # Four independent seal rails form a closed gasket, without a solid plate filling the tub.
    for y in (-8.48,8.48):box('Lid seal long rail',(0,y,4.78),(22.30,.16,.13),'rubber',.055,4)
    for x in (-11.25,11.25):box('Lid seal end rail',(x,0,4.78),(.16,16.65,.13),'rubber',.055,4)
    lid=box('Protective case lid',(0,0,5.43),(23.4,17.4,1.12),'plastic',.46,7)
    cut(lid,(0,0,4.93),(21.8,15.8,.83))
    for x in (-10.4,10.4):
        for y in (-7.4,7.4):box('Lid raised corner',(x,y,5.95),(1.62,1.62,.13),'rubber',.28,6)
    box('Raised label recess',(0,.35,5.98),(16.2,11.7,.09),'rubber',.28,6)
    box('Printed case identity plate',(0,.35,6.035),(15.5,11.12,.035),'paper',.07,4)
    panel('Case identity artwork',(0,.35,6.056),15.25,10.91,'primary')
    for x in (-8.0,8.0):
        # Rear hinge knuckles run along the X axis and are retained as editable parts.
        for dx in (-.76,0,.76):cylinder('Rear hinge knuckle',(x+dx,8.61,4.85),.32,.69,'plastic','X',32,.025)
        cylinder('Rear hinge pin',(x,8.61,4.85),.115,2.34,'steel','X',24,.008)
        for z in (4.34,5.33):box('Rear hinge leaf',(x,8.63,z),(2.38,.21,.62),'plastic',.08,4)
    for x in (-6.8,6.8):
        box('Latch backing',(x,-8.73,4.25),(2.45,.21,2.15),'rubber',.16,5)
        box('Stamped latch clasp',(x,-8.91,4.30),(1.65,.21,1.65),'steel',.12,5)
        box('Latch folded lip',(x,-8.99,4.97),(1.72,.10,.25),'steel',.045,4)
        for dx in (-.72,.72):screw('Latch rivet',(x+dx,-8.93,3.63),.12,'Y')
    # True hollow handle: two supports and a grip, with no solid centre plate.
    for x in (-2.75,2.75):box('Handle pivot support',(x,-8.77,3.13),(.62,.32,.88),'plastic',.13,5)
    for x in (-2.75,2.75):box('Handle arm',(x,-8.99,2.42),(.30,.36,1.1),'rubber',.12,5)
    box('Carry handle grip',(0,-8.99,1.94),(5.7,.43,.40),'rubber',.16,6)
    for x in (-10.35,10.35):
        for y in (-7.45,7.45):box('Rubber protective foot',(x,y,.21),(1.55,1.55,.42),'rubber',.22,6)
    for x in (-11.6,11.6):
        for y in (-5.9,0,5.9):box('Side wall reinforcing rib',(x,y,2.55),(.22,.54,3.75),'plastic',.09,4)
    # The red tamper strip crosses the actual lid/body seam.
    box('Tamper seal paper',(2.95,-8.76,4.86),(1.25,.035,1.67),'seal',.015,3)
    panel('Tamper seal serial',(2.95,-8.782,4.86),1.04,1.43,'secondary','FRONT')
    panel('Bottom inventory serial',(0,0,.296),7.8,1.42,'barcode','BOTTOM')

def archive():
    rng=random.Random(271)
    sheet('Archive sleeve back',(0,0,.10),(32,24,.18),'kraft',.035)
    # Layered packets retain small offsets and an exposed paper edge, not a white block.
    for j in range(23):
        x=rng.uniform(-.065,.065);y=rng.uniform(-.055,.055)
        sheet('Filed paper layer %02d'%j,(x+.15,y,.30+j*.091),(30.3,22.5,.073),'paper',.035+j*.0018)
    sheet('Upper folio sheet',(.13,0,2.48),(30.1,22.45,.045),'paper',.09)
    # A subtle warped cover keeps the cardboard shape and real cut edge.
    cover=sheet('Signed cardboard cover',(-.18,0,2.70),(31.4,23.55,.14),'kraft',.06)
    box('Cloth reinforced spine',(-15.62,0,1.41),(.41,23.75,2.71),'rubber',.09,5)
    box('Spine outer cloth strip',(-15.84,0,1.41),(.13,22.9,2.35),'kraft',.035,4)
    # Paper label is separated from the cover by its own actual stock thickness.
    box('Archive cover label',(1.55,.43,2.813),(25.2,17.45,.024),'paper',.055,3)
    panel('Administrative title and seal',(1.55,.43,2.827),24.98,17.23,'primary')
    # Three index tabs protrude from the packet edge, each with distinct shape and position.
    for j,y in enumerate((-6.8,0,6.6)):
        box('Numbered folio tab %d'%j,(15.43,y,1.0+j*.54),(.90,2.05,.07),'paper' if j!=1 else 'seal',.05,4)
    # Brass string eyelets and cotton lacing remain physical geometry.
    for y in (-7.85,7.85):
        ring('Binding brass eyelet',(-13.5,y,2.85),.36,.17,.07,'brass',sides=40)
        cylinder('Eyelet shadow opening',(-13.5,y,2.795),.16,.035,'rubber',sides=32,radius=0)
    cord('Cotton archive binding',[(-13.5,-7.85,2.87),(-13.62,-4.4,2.91),(-13.48,0,2.96),(-13.39,4.3,2.91),(-13.5,7.85,2.87)],.049,'paper')
    cord('Binding return',[(-13.5,7.85,2.91),(-13.2,7.15,2.94),(-13.20,-6.5,2.96),(-13.5,-7.85,2.92)],.046,'paper')
    cord('Binding knot loop',[(-13.3,.1,2.98),(-12.72,.70,3.02),(-12.30,.22,3.015),(-12.72,-.16,3.03),(-13.3,.1,2.98)],.045,'paper')
    cord('Binding knot end',[(-13.31,.05,2.99),(-12.56,-.95,2.96),(-11.89,-1.68,2.91)],.044,'paper')
    # Folded tamper seal sits over the front sleeve edge; it is not a floating decal.
    box('Archive security paper seal',(7.35,-11.80,2.30),(2.45,.028,1.12),'seal',.01,2)
    panel('Archive seal transfer number',(7.35,-11.818,2.30),2.24,.94,'barcode','FRONT')
    panel('Reverse archive transfer form',(1.2,0,.004),21.2,8.2,'secondary','BOTTOM')
    # Spine label is a physical printed strip with an opaque paper backing.
    panel('Spine sequence label',(0,-11.82,1.48),8.8,.90,'barcode','FRONT')

BUILDERS={'USB':usb,'Tape':tape,'Case':case,'Archive':archive}
receipt={'stage':'authoring','assets':{},'rendered':False,'tested':False}
for key,builder in BUILDERS.items():
    REGIONS=SPEC['assets'][key]['regions']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    scene.world=bpy.data.worlds.new('Neutral studio environment');scene.world.color=(.08,.08,.08)
    PARTS=[];MAT=make_material(key);builder()
    source=MASTER/(SPEC['assets'][key]['mesh']+'_Source.blend')
    # Authored components and unapplied edge modifiers stay editable in the master.
    bpy.ops.object.select_all(action='DESELECT')
    for o in PARTS:o.select_set(True)
    bpy.context.view_layer.objects.active=PARTS[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    dep=bpy.context.evaluated_depsgraph_get();export_parts=[]
    for o in PARTS:
        evaluated=o.evaluated_get(dep)
        mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=dep)
        instance=bpy.data.objects.new(o.name+'_Export',mesh);bpy.context.collection.objects.link(instance)
        instance.matrix_world=o.matrix_world.copy()
        # Bevel interpolation can collapse UVs on the new chamfer strips.
        # Project those evaluated surfaces into their original atlas region.
        # Printed panels keep their explicitly oriented artwork coordinates.
        if o.modifiers:project_uv(instance,o['surface_region'])
        export_parts.append(instance)
    bpy.ops.object.select_all(action='DESELECT')
    for o in export_parts:o.select_set(True)
    bpy.context.view_layer.objects.active=export_parts[0];bpy.ops.object.join();game=bpy.context.object
    game.name=SPEC['assets'][key]['mesh'];game.data.transform(game.matrix_world);game.matrix_world=Matrix.Identity(4)
    # Share the one atlas material and keep copied UVs and weighted split normals.
    game.data.materials.clear();game.data.materials.append(MAT)
    for poly in game.data.polygons:poly.material_index=0
    # FBX tangent export requires triangles/quads rather than boolean n-gons.
    tri=game.modifiers.new('Stable exported triangulation','TRIANGULATE')
    tri.quad_method='FIXED';tri.ngon_method='BEAUTY'
    bpy.ops.object.modifier_apply(modifier=tri.name)
    game.data.calc_loop_triangles();triangles=len(game.data.loop_triangles)
    points=[v.co for v in game.data.vertices]
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    centre=(low+high)/2;extent=high-low
    bpy.ops.mesh.primitive_cube_add(size=1,location=centre);collision=bpy.context.object
    collision.name='UCX_'+game.name+'_00';collision.scale=extent
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    select(game);collision.select_set(True)
    fbx=OUT/(game.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,use_tspace=True,path_mode='STRIP',add_leaf_bones=False)
    select(game);game.scale=(.01,.01,.01);scene.unit_settings.scale_length=1
    glb=OUT/(game.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,
        export_yup=True,export_materials='EXPORT')
    receipt['assets'][key]={**SPEC['assets'][key], 'source':str(source),'fbx':str(fbx),'glb':str(glb),
        'triangles_lod0':triangles,'source_components':len(PARTS),'actual_dimensions_cm':list(extent),
        'pivot':'bottom-centred authoring origin, +Z up','collision':'one closed UCX box',
        'geometry_features':[o.name for o in PARTS]}
    (ROOT/'model_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DOCUMENT_MODEL_EXPORTED',key,'triangles',triangles,'dimensions_cm',list(extent),flush=True)
receipt['stage']='sources_and_exports_saved'
(ROOT/'model_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
