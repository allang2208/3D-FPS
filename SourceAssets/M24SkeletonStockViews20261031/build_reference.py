"""Exterior-only game-art blockout and orthographic reference views.
Arbitrary art units. No working internals or manufacturing dimensions.
"""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent; (O/'Views').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene; parts=[]
def mat(name,color,metal,rough,grain=False):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if grain:
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=180;noise.inputs['Detail'].default_value=2
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.006
        m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
coat=mat('Graphite satin metal',(.055,.063,.069),.7,.34,True)
dark=mat('Recess dark metal',(.018,.022,.026),.6,.4)
steel=mat('Satin fasteners',(.25,.28,.30),.8,.28)
poly=mat('Cheek-rest black polymer',(.022,.025,.028),0,.43,True)
rubber=mat('Fine rubber',(.012,.014,.017),0,.69,True)
def finish(o,name,m=coat,bevel=.025):
    o.name=name;o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('Soft exterior edges','BEVEL');b.width=bevel;b.segments=4;b.limit_method='ANGLE'
        n=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');n.keep_sharp=True
    for f in o.data.polygons:f.use_smooth=True
    parts.append(o);return o
def cube(name,loc,size,m=coat,b=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,m,b)
def cylinder(name,loc,rad,depth,axis='Y',m=coat,verts=64,b=.01):
    rot={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=rad,depth=depth,location=loc,rotation=rot);o=bpy.context.object
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);return finish(o,name,m,b)
def prism(name,points,depth,m=coat,b=.025,y=0):
    count=len(points);v=[(x,y+side*depth/2,z) for side in (-1,1) for x,z in points]
    f=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);s.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    return finish(o,name,m,b)
def cut(o,cutter):
    bpy.context.view_layer.objects.active=o;b=o.modifiers.new('Exterior negative space','BOOLEAN');b.operation='DIFFERENCE';b.solver='EXACT';b.object=cutter
    # Booleans operate ahead of bevels, preserving continuous outside edges.
    while o.modifiers.find(b.name)>0:bpy.ops.object.modifier_move_up(modifier=b.name)
    bpy.ops.object.modifier_apply(modifier=b.name);parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
def fastener(x,z,y=-.235,r=.075):
    cylinder('Recessed fastener bezel',(x,y,z),r*1.25,.015,m=dark,b=.004)
    head=cylinder('Fastener head',(x,y-.015 if y<0 else y+.015,z),r,.025,m=steel,b=.006)
    # Cosmetic dark hex socket, deliberately shallow, no functional threading.
    cylinder('Hex socket shade',(x,y-.031 if y<0 else y+.031,z),r*.43,.004,m=dark,verts=6,b=.001)

# Silhouette-derived outer chassis; no receiver or pistol grip in this asset.
body=prism('Skeleton outer carriage',[(1.14,2.10),(2.97,2.10),(3.10,1.91),(4.43,1.91),(4.43,1.10),(2.66,1.10),(2.51,.95),(2.51,.44),(2.67,.26),(2.66,.18),(1.29,.18),(1.16,.40)],.43)
cut(body,prism('Lightening window cut',[(3.10,1.47),(3.26,1.72),(3.70,1.72),(3.94,1.55),(3.94,1.32),(3.72,1.18),(3.26,1.18),(3.10,1.32)],.9,b=0))
cut(body,cube('Upper wheel slot',(2.24,0,1.94),(.81,.9,.24),b=0))
cut(body,cube('Lower wheel slot',(2.10,0,.94),(.25,.9,.82),b=0))
# Parallel extension rods remain readable through the rear opening.
for z in (.52,1.77):cylinder('Exposed extension rail',(.99,0,z),.067,.59,'X',steel)
padprofile=[(.02,.02),(-.02,.17),(.03,2.23),(.14,2.35),(.67,2.35),(.80,2.17),(.86,.28),(.76,.08)]
pad=prism('Rubber butt pad',padprofile,.65,rubber,.07)
backplate=prism('Butt pad support',[(.70,.12),(.85,.18),(.91,.40),(.87,2.15),(.76,2.32),(.68,2.32)],.56,coat,.035)
# Subtle molding seams on the pad side, with a restrained tread at the rear.
for side in (-1,1):
    for x in (.25,.55):prism('Rubber molding seam',[(x,.13),(x+.012,.13),(x+.012,2.22),(x,2.22)],.009,dark,.004,side*.328)
    cylinder('Butt pad round insert',(.72,side*.30,1.46),.10,.025,'Y',coat)
for i in range(17):
    cube('Rubber shallow tread',(.012,0,.19+i*.12),(.027,.57,.033),rubber,.013)

# Raised cheek rest: rounded cross-section and bevelled, tapered ends.
stations=[(1.12,.93),(1.16,1),(1.27,1),(3.59,1),(3.74,.96),(3.78,.90)]
section=[(-.33,2.28),(-.37,2.37),(-.36,2.58),(-.27,2.67),(.27,2.67),(.36,2.58),(.37,2.37),(.33,2.28)]
vs=[]
for x,w in stations:
    for y,z in section:vs.append((x,y*w,z-.018*(x-1.12)))
N=len(section);fs=[tuple(range(N-1,-1,-1)),tuple(range((len(stations)-1)*N,len(stations)*N))]
for k in range(len(stations)-1):
    for j in range(N):fs.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
me=bpy.data.meshes.new('Cheek rest shell');me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new('Cheek rest shell',me);s.collection.objects.link(o)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();finish(o,'Contoured cheek rest',poly,.035)
for x in (1.64,2.89):cylinder('Cheek-rest visible support',(x,0,2.20),.054,.23,'Z',steel)
cylinder('Central cheek-rest stem',(2.25,0,2.18),.079,.22,'Z',dark)
# External thumbwheels and grips, only a cosmetic representation.
cylinder('Horizontal adjustment wheel',(2.24,0,1.94),.225,.17,'Z',dark)
for i in range(24):
    a=i*math.tau/24;ob=cube('Wheel flute',(2.24+.223*math.cos(a),.223*math.sin(a),1.94),(.032,.025,.15),coat,.008);ob.rotation_euler.z=a
cylinder('Vertical adjustment wheel',(2.10,0,.94),.36,.12,'X',dark)
for i in range(30):
    a=i*math.tau/30;ob=cube('Vertical wheel flute',(2.10,.357*math.sin(a),.94+.357*math.cos(a)),(.10,.035,.035),coat,.008);ob.rotation_euler.x=-a
cube('Rear underside visual foot',(1.78,0,.12),(.78,.48,.13),dark,.025)
for x in (1.50,1.68,1.86,2.04):cube('Underside short rib',(x,0,.065),(.07,.50,.075),coat,.012)
for side in (-1,1):
    cube('Rear face accent panel',(1.53,side*.228,1.03),(.30,.034,.72),coat,.018)
    for z in (.69,1.39):fastener(1.53,z,side*.255,.065)
    for x,z,rad in ((1.32,1.67,.09),(4.09,1.46,.095),(2.86,1.94,.045)):fastener(x,z,side*.225,rad)
    # Shallow decorative gradations, not technical dimensions.
    for i in range(5):cube('Adjustment tick',(1.78+i*.09,side*.233,1.70),(.025,.006,.012),steel,.001)
    for i in range(5):cube('Vertical tick',(2.31,side*.233,.63+i*.13),(.035,.006,.012),steel,.001)

# Closed exterior collar representation, without functional attachment internals.
cube('Forward collar block',(4.59,0,1.5),(.44,.49,.84),coat,.055)
cylinder('Collar upper cap',(4.61,0,1.95),.26,.10,'Z',dark)
cylinder('Collar lower cap',(4.61,0,1.07),.26,.10,'Z',dark)
cylinder('Collar outside barrel',(4.61,0,1.5),.23,.78,'Z',coat,64)
cube('Front connection silhouette',(4.99,0,1.52),(.42,.38,.55),coat,.04)
for side in (-1,1):
    cube('Collar inset seam',(4.56,side*.248,1.52),(.018,.009,.57),dark,.004)
    fastener(4.98,1.52,side*.197,.06)

# Render setup: studio lighting, orthographic, white and alpha reference outputs.
s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True
s.world=bpy.data.worlds.new('White studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
wn=s.world.node_tree.nodes;wl=s.world.node_tree.links;lp=wn.new('ShaderNodeLightPath');bg=wn.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(1,1,1,1);bg.inputs['Strength'].default_value=100
mix=wn.new('ShaderNodeMixShader');wl.new(lp.outputs['Is Camera Ray'],mix.inputs[0]);wl.new(wn['Background'].outputs[0],mix.inputs[1]);wl.new(bg.outputs[0],mix.inputs[2]);wl.new(mix.outputs[0],wn['World Output'].inputs['Surface'])
s.view_settings.view_transform='AgX';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
def area(name,loc,energy,size,target=(2.5,0,1.4)):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
lights=[area('Large key',(1,-5,7),1100,6),area('Soft fill',(5,4,4),900,5),area('Pad fill',(-4,-2,3),600,4)]
d=bpy.data.cameras.new('Orthographic reference');cam=bpy.data.objects.new('Orthographic reference',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO'
def camera(loc,target,scale,res):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;s.render.resolution_x,s.render.resolution_y=res;s.render.resolution_percentage=100
viewdata=[('side',(2.60,-12,1.35),(2.60,0,1.35),5.8,(2400,1440)),('top',(2.60,0,12),(2.60,0,1.35),5.8,(2400,1440)),('rear',(-12,0,1.35),(2.60,0,1.35),3.35,(1440,2400))]
for name,loc,target,scale,res in viewdata:
    camera(loc,target,scale,res)
    if name=='top':cam.rotation_euler=(0,0,0)
    if '--white-pass' not in sys.argv:
        s.render.filepath=str(O/'Views'/('stock_'+name+'_alpha.png'));bpy.ops.render.render(write_still=True)
    # Keep white standalone views for direct multi-image submission.
    s.render.film_transparent=False;s.render.filepath=str(O/'Views'/('stock_'+name+'.png'));bpy.ops.render.render(write_still=True);s.render.film_transparent=True

# Orthographic sheet from the same 3D exterior, not a drawn reinterpretation.
for light in lights:light.hide_render=True
for o in parts:o.hide_render=True
def copy_group(name,rotation,translation):
    transform=Matrix.Translation(Vector(translation))@rotation
    for obj in parts:
        cp=obj.copy();cp.data=obj.data;cp.name=name+' '+obj.name;s.collection.objects.link(cp);cp.matrix_world=transform@obj.matrix_world;cp.hide_render=False
# A single front-facing scene: side on top, plan below, rear at right.
copy_group('SIDE',Matrix.Identity(4),(-1.4,0,3.1))
copy_group('TOP',Matrix.Rotation(math.pi/2,4,'X'),(-1.4,0,1.35))
rearrot=Matrix(((0,-1,0,0),(1,0,0,0),(0,0,1,0),(0,0,0,1)))
copy_group('REAR',rearrot,(5.5,0,3.1))
area('Sheet key',(0,-6,10),2200,8,(2,0,3));area('Sheet fill',(7,-4,5),1500,7,(2,0,3));area('Sheet edge',(-4,1,7),1700,5,(2,0,3))
labelmat=mat('Sheet text',(.025,.032,.038),0,1)
def text_label(body,loc,size):
    cu=bpy.data.curves.new('Label','FONT');cu.body=body;cu.size=size;cu.space_character=1.15;ob=bpy.data.objects.new(body,cu);s.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(math.pi/2,0,0);ob.data.materials.append(labelmat)
text_label('M24  /  SKELETON STOCK',(-1.45,-.8,6.45),.23)
text_label('SIDE',(-1.45,-.8,6.0),.14);text_label('TOP',(-1.45,-3.2,2.05),.14);text_label('REAR',(5.06,-.8,6.0),.14)
text_label('EXTERIOR CONCEPT  /  ORTHOGRAPHIC VIEWS',(-1.45,-3.2,.45),.115)
camera((2.15,-18,3.35),(2.15,0,3.35),8.5,(2800,2240));s.render.film_transparent=False;s.render.filepath=str(O/'stock_three_views.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Stock_Exterior_Reference.blend'))
bpy.ops.render.render(write_still=True)
(O/'delivery.json').write_text(json.dumps({'type':'Exterior game-art reference; not a game-ready or working mechanical model','source':'User-provided rifle side photograph, isolated rear stock','method':'Blender direct geometry and orthographic rendering','views':['side','top','rear'],'unknown_views':'Top and rear completed consistently from side reference; design inference','meshy_submitted':False,'engine_imported':False,'sheet':'stock_three_views.png','blend':'Stock_Exterior_Reference.blend'},indent=2))
print('STOCK_REFERENCE_RENDERED',flush=True)
