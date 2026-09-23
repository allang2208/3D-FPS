"""Precisely authored, editable maintenance switch cabinet; no generated geometry."""
import bpy,bmesh,math,json,random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'Config/cabinet.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
R=random.Random(922111);objects=[]
recipes={
 'Enamel':dict(color=[.065,.082,.066],roughness=.57,metallic=0),
 'Interior':dict(color=[.14,.155,.14],roughness=.66,metallic=0),
 'Steel':dict(color=[.16,.18,.19],roughness=.38,metallic=.86),
 'Bakelite':dict(color=[.025,.021,.016],roughness=.43,metallic=0),
 'Cable':dict(color=[.011,.014,.016],roughness=.75,metallic=0),
 'Copper':dict(color=[.36,.14,.056],roughness=.50,metallic=.90),
 'Ceramic':dict(color=[.52,.49,.40],roughness=.41,metallic=0),
 'Blue':dict(color=[.024,.074,.11],roughness=.64,metallic=0),
 'Red':dict(color=[.14,.023,.009],roughness=.62,metallic=0),
 'Text':dict(color=[.016,.021,.018],roughness=.81,metallic=0),
 'Amber':dict(color=[.41,.13,.012],roughness=.28,metallic=0,emission=[.28,.071,.002])}
materials={}
for key,r in recipes.items():
    m=bpy.data.materials.new('Maintenance_'+key);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*r['color'],1);p.inputs['Roughness'].default_value=r['roughness'];p.inputs['Metallic'].default_value=r['metallic']
    if r.get('emission'):p.inputs['Emission Color'].default_value=(*r['emission'],1);p.inputs['Emission Strength'].default_value=.6
    materials[key]=m
    if key in ('Enamel','Interior','Steel','Bakelite'):
        nt=m.node_tree;folder=ROOT.parent/'DungeonServices20260922/Authored/Textures'
        texture=nt.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(folder/'ServicePaint_AgeMask.png'),check_existing=True);texture.image.colorspace_settings.name='Non-Color'
        vc=nt.nodes.new('ShaderNodeVertexColor');vc.layer_name='Wear';sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(vc.outputs['Color'],sep.inputs['Color'])
        sub=nt.nodes.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=.62;nt.links.new(texture.outputs['Color'],sub.inputs[0])
        scale=nt.nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=6;scale.use_clamp=True;nt.links.new(sub.outputs[0],scale.inputs[0])
        mask=nt.nodes.new('ShaderNodeMath');mask.operation='MULTIPLY';nt.links.new(scale.outputs[0],mask.inputs[0]);nt.links.new(sep.outputs[0],mask.inputs[1])
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(*r['color'],1);mix.inputs[2].default_value=(*([.11,.118,.11] if key in ('Enamel','Interior') else [v*.6 for v in r['color']]),1);nt.links.new(mask.outputs[0],mix.inputs[0])
        dirt=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mix.outputs[0],dirt.inputs[1]);dirt.inputs[2].default_value=(*[v*.6 for v in r['color']],1);nt.links.new(sep.outputs[1],dirt.inputs[0]);nt.links.new(dirt.outputs[0],p.inputs['Base Color'])
        for output,first,last in [('Roughness',r['roughness'],.44 if key in ('Enamel','Interior') else .70),('Metallic',r['metallic'],.78 if key in ('Enamel','Interior') else r['metallic'])]:
            q=nt.nodes.new('ShaderNodeMixRGB');q.inputs[1].default_value=(first,first,first,1);q.inputs[2].default_value=(last,last,last,1);nt.links.new(mask.outputs[0],q.inputs[0]);nt.links.new(q.outputs[0],p.inputs[output])
        texn=nt.nodes.new('ShaderNodeTexImage');texn.image=bpy.data.images.load(str(folder/'ServicePaint_Normal.png'),check_existing=True);texn.image.colorspace_settings.name='Non-Color'
        normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(texn.outputs[0],normal.inputs['Color']);nt.links.new(normal.outputs[0],p.inputs['Normal'])
def finish(ob,mat,bevel=0):
    ob.data.materials.append(materials[mat]);objects.append(ob)
    if bevel:
        mod=ob.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=3
        bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob
def box(name,c,size,mat='Enamel',bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,mat,bevel)
def cyl(name,c,r,depth,mat='Steel',axis=(0,-1,0),sides=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=depth,location=c);o=bpy.context.object;o.name=name
    o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler();finish(o,mat,.0007)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o
def wire(name,pts,r=.003,mat='Cable'):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=12;curve.bevel_depth=r;curve.bevel_resolution=3
    spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(pts)-1)
    for p,co in zip(spline.bezier_points,pts):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);bpy.context.view_layer.objects.active=o;o.select_set(True)
    bpy.ops.object.convert(target='MESH');return finish(bpy.context.object,mat)
def text(name,words,location,size=.014,mat='Text'):
    bpy.ops.object.text_add(location=location,rotation=(math.pi/2,0,0));o=bpy.context.object;o.name=name
    o.data.body=words;o.data.size=size;o.data.extrude=0;o.data.align_x='CENTER';o.data.align_y='CENTER'
    bpy.ops.object.convert(target='MESH');return finish(bpy.context.object,mat)
def screw(c):
    cyl('Washer',c,.006,.0015)
    o=cyl('Hex fastener',(c[0],c[1]-.003,c[2]),.0042,.004,sides=6)
    box('Screw slot',(c[0],c[1]-.0052,c[2]),(.005,.0005,.0008),'Cable',0)

# Cabinet thickness, return lips, ventilation and a real recessed interior.
box('Cabinet back',(0,.155,1.08),(1.14,.01,1.58),'Enamel')
for x in (-.565,.565):box('Folded side',(x,0,1.08),(.01,.32,1.58),'Enamel')
for z in (.295,1.865):box('Folded top bottom',(0,0,z),(1.14,.32,.01),'Enamel')
for x in (-.555,.555):box('Front return',(x,-.153,1.08),(.027,.015,1.56),'Enamel',.001)
box('Partition',(.04,.004,1.08),(.012,.294,1.56),'Interior')
box('DIN backplate',(-.25,.130,1.10),(.50,.015,1.39),'Interior')
for x in (-.39,.39):
    box('Mounting channel',(x,.19,1.02),(.085,.052,1.67),'Steel')
    for z in (.41,1.72):
        box('Wall standoff',(x,.232,z),(.12,.036,.09),'Steel')
        cyl('Mount stud',(x,.184,z),.011,.014,'Steel',sides=6)
box('Kick plinth',(0,.0,.15),(1.075,.28,.30),'Enamel',.009)
box('Plinth recess',(0,-.144,.16),(.91,.01,.095),'Cable')
for x in (-.41,.41):screw((x,-.155,.15))

# Right sealed door: slightly crowned lip, distinct gap, vent slots, latch.
box('Right door',(.305,-.175,1.079),(.492,.025,1.537),'Enamel',.004)
for z in (.45,.76,1.38,1.69):cyl('Right hinge',(.558,-.18,z),.012,.085,'Steel',axis=(0,0,1))
for z in (1.21,1.26):cyl('Latch escutcheon',(.097,-.195,z),.018,.010,'Steel')
box('Latch grip',(.097,-.212,1.235),(.018,.027,.12),'Bakelite',.005)
for z in [.47+i*.032 for i in range(8)]:
    box('Vent opening',(.34,-.189,z),(.30,.002,.010),'Cable',.001)
    box('Vent rain lip',(.34,-.194,z+.009),(.32,.012,.009),'Enamel',.001)
box('Main circuit plate',(.305,-.192,1.68),(.30,.002,.092),'Ceramic',.001)
text('Panel designation','SERVICE  /  02',(.305,-.194,1.685),.025)
text('Panel rating','400 V   -   50 Hz',(.305,-.194,1.655),.012)
for x in (.176,.434):screw((x,-.196,1.68))
box('Warning plate',(.305,-.192,1.00),(.17,.002,.115),'Ceramic',.002)
text('Warning','ISOLATE',(.305,-.194,1.025),.022)
text('Warning small','BEFORE SERVICE',(.305,-.194,.994),.013)

# Left open door has a physical gasket, inner stiffeners and a restrained hinge angle.
start=len(objects)
box('Open left door',(-.255,-.177,1.079),(.56,.018,1.537),'Enamel',.003)
for x in (-.50,-.010):box('Door gasket',(x,-.163,1.079),(.012,.006,1.48),'Cable',.001)
for z in (.346,1.812):box('Door gasket',(-.255,-.163,z),(.50,.006,.012),'Cable',.001)
for z in (.48,1.67):box('Door inner stiffener',(-.255,-.151,z),(.46,.024,.025),'Interior',.002)
box('Door handle',(-.025,-.210,1.17),(.018,.055,.115),'Bakelite',.004)
box('Inspection plaque',(-.26,-.19,1.62),(.31,.002,.075),'Ceramic',.001)
text('Inspection ID','FEED  /  MAINT.',(-.26,-.192,1.625),.020)
text('Inspection year','INSPECTED  07 - 84',(-.26,-.192,1.600),.010)
hinge=Vector((-.539,-.177,0));angle=math.radians(-CFG['open_door_degrees'])
from mathutils import Matrix
rot=Matrix.Rotation(angle,4,'Z')
for o in objects[start:]:o.matrix_world=Matrix.Translation(hinge)@rot@Matrix.Translation(-hinge)@o.matrix_world
for z in (.44,.84,1.39,1.73):cyl('Left hinge',(-.541,-.171,z),.014,.088,'Steel',axis=(0,0,1))

# Visible electrical layers sit ahead of the backplate, with routes entering glands.
for row,z in enumerate((.72,1.04,1.37)):
    box('DIN rail',(-.255,.088,z),(.48,.025,.033),'Steel',.001)
    for j in range(5):
        x=-.433+j*.090
        box('Breaker', (x,.029,z),(.077,.111,.135),'Ceramic',.004)
        box('Breaker switch',(x,-.033,z+.012),(.038,.024,.060),'Bakelite',.003)
        box('Switch ridge',(x,-.049,z+.022),(.035,.008,.010),'Cable',.001)
        for zz in (z-.046,z+.046):cyl('Breaker screw',(x,-.031,zz),.004,.002,'Steel',sides=6)
        # Unequal conductor curves, separated at terminals, attached to rail wiring ducts.
        color=('Red','Blue','Cable')[j%3]
        wire('Insulated conductor',[(x,.04,z+.074),(x,.017,z+.125),(x-.013,.05,z+.18),(-.485,.065,z+.18)],.0032,color)
        wire('Return conductor',[(x,.05,z-.069),(x+.01,.041,z-.102),(-.49,.06,z-.105)],.0028,'Cable')
    text('Circuit strip','F%02d  F%02d  F%02d  F%02d  F%02d'%tuple(row*5+i+1 for i in range(5)),(-.255,-.036,z-.093),.015,'Ceramic')
for z in (.55,.89,1.21,1.57):
    box('Slotted wire duct',(-.252,.06,z),(.50,.040,.029),'Bakelite',.001)
    for j in range(18):box('Duct slot',(-.488+j*.027,.037,z),(.008,.003,.023),'Cable',0)
box('Bus mount',(-.25,.047,1.68),(.46,.063,.068),'Bakelite',.002)
box('Copper bus',(-.25,.008,1.68),(.41,.01,.035),'Copper',.001)
for j in range(7):screw((-.43+j*.061,-.001,1.68))
for j in range(4):
    x=-.43+j*.113
    cyl('Cable gland',(x,.015,.283),.018,.052,'Bakelite',axis=(0,0,1),sides=6)
    wire('Incoming cable',[(x,.015,.29),(x,.035,.22),(x-.02,.10,.14),(x,.12,.04)],.010,'Cable')
wire('Door earth strap',[(-.47,.07,.54),(-.48,-.045,.54),(-.53,-.21,.49),(-.51,-.30,.53)],.004,'Copper')

# Real dial bezel and needle rather than an unreadable generated patch.
cyl('Gauge bezel',(.305,-.204,1.42),.073,.032,'Steel',sides=64)
cyl('Gauge inset',(.305,-.224,1.42),.063,.005,'Cable',sides=64)
cyl('Gauge face',(.305,-.228,1.42),.057,.002,'Ceramic',sides=64)
for i in range(13):
    a=math.radians(-135+i*22.5);x=.305+math.sin(a)*.047;z=1.42+math.cos(a)*.047
    o=box('Gauge tick',(x,-.23,z),(.0015,.0007,.006 if i%3 else .010),'Text',0);o.rotation_euler[1]=a
wire('Gauge needle',[(.305,-.232,1.42),(.281,-.232,1.451)],.0012,'Text')
cyl('Gauge pivot',(.305,-.234,1.42),.005,.003,'Bakelite')
text('Gauge unit','A',(.305,-.232,1.395),.013)
cyl('Amber bezel',(.455,-.202,1.19),.016,.018,'Steel')
cyl('Amber indicator',(.455,-.216,1.19),.012,.011,'Amber')

# Actual object-space UV scale and edge/handling wear attributes survive joining.
for o in objects:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    mesh=o.data
    if o.data.materials[0].name in ('Maintenance_Enamel','Maintenance_Interior') and max(o.dimensions)>.25:
        # Broad painted faces need interior vertices for edge masks. Without
        # these, four worn corners interpolate into an entirely worn flat panel.
        bm=bmesh.new();bm.from_mesh(mesh)
        edges=[e for e in bm.edges if e.calc_length()>.035]
        if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=min(16,max(2,int(max(o.dimensions)/.075))),use_grid_fill=True)
        bm.to_mesh(mesh);bm.free();mesh.update()
    uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
    colors=mesh.color_attributes.new(name='Wear',type='BYTE_COLOR',domain='CORNER')
    low=[min(v.co[i] for v in mesh.vertices) for i in range(3)];high=[max(v.co[i] for v in mesh.vertices) for i in range(3)]
    for p in mesh.polygons:
        axes=sorted(range(3),key=lambda i:abs(p.normal[i]))[:2]
        for li in p.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;wp=o.matrix_world@v
            uv.data[li].uv=(wp[axes[0]]/.45,wp[axes[1]]/.45)
            d=sorted(min(abs(v[i]-low[i]),abs(high[i]-v[i])) for i in range(3))
            edge=max(0,1-d[1]/.010);grime=max(0,1-wp.z/.55)*.33
            colors.data[li].color=(edge,grime,0,1)
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name='SM_MaintenanceCabinet'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
tri=o.modifiers.new('Export triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MaintenanceCabinet_Source.blend'))
fbx=OUT/(o.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR')
manifest=dict(name=o.name,fbx=str(fbx),source_blend=str(OUT/'MaintenanceCabinet_Source.blend'),materials=recipes,config=CFG)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('MAINTENANCE_CABINET_AUTHORED')
