"""Refine the selected Peakwatch concept into fitted, UV-mapped game meshes."""
from pathlib import Path
import bpy,bmesh,math,json,sys
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;BASE=P.parent;CONCEPT=BASE/'Scope3to6ConceptV10'
(P/'Export').mkdir(exist_ok=True);(P/'Textures').mkdir(exist_ok=True)
# Reuse the selected shape construction, excluding its presentation-only scene.
source=(CONCEPT/'author_concept.py').read_text(encoding='utf-8').split('# One editable source,')[0]
# Micro-knurl ridges retain their silhouette without redundant bevel rings.
source=source.replace('vertices=32,radius=r','vertices=12 if r<.03 else 32,radius=r')
source=source.replace('bevel=min(.012,r*.2)','bevel=0 if r<.03 else min(.012,r*.2)')
scope={'__file__':str(CONCEPT/'author_concept.py')}
exec(compile(source,str(CONCEPT/'author_concept.py'),'exec'),scope)
parts=scope['parts'];ring=scope['ring'];rod=scope['rod'];cube=scope['cube'];text=scope['text']
silver=scope['silver'];dark=scope['dark'];brass=scope['brass'];ink=scope['engraving'];wood=scope['walnut']
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
bpy.context.preferences.filepaths.save_version=0
discard=('Mount lower junction','Offset support','Curved seat block','Walnut seat inlay','Seat screw','Screw slit',
         'Clear circular lens','Fine etched crosshair','Reticle centre dot','Reticle reference tick','Label ')
for o in list(parts):
    if o.name.startswith(discard):parts.remove(o);bpy.data.objects.remove(o,do_unlink=True)
silver.name='M_Peakwatch_Steel';dark.name='M_Peakwatch_DarkSteel';brass.name='M_Peakwatch_Brass'
ink.name='M_Peakwatch_Engraving';wood.name='M_Peakwatch_Walnut'

# Refinement: stepped retaining rings, narrow grooves, seating lips and screw slots.
ring('Front bevel bead',1.287,1.247,-.505,.035,silver)
ring('Lens retaining groove',1.235,1.205,-.448,.025,dark)
ring('Rear recessed retaining bead',1.255,1.205,.495,.035,silver)
ring('Collar edge bead front',1.405,1.375,-.355,.025,brass)
ring('Collar edge bead rear',1.405,1.375,-.115,.025,brass)
ring('Focus separation channel',1.291,1.249,.19,.027,dark)
for a in [math.radians(v) for v in [35,145,215,325]]:
    x,z=1.215*math.cos(a),1.215*math.sin(a)
    rod('Recessed lip screw',(x,-.49,z),(x,-.52,z),.032,dark)
    rod('Lip screw slot',(x-.019,-.526,z),(x+.019,-.526,z),.004,silver)
for i in range(32):
    a=i*math.tau/32;x=.222*math.cos(a);y=.06+.222*math.sin(a)
    rod('Top drum knurl',(x,y,1.48),(x,y,1.59),.009,silver)
for number,angle in zip(['3','4','5','6'],[90,53,16,-21]):
    a=math.radians(angle)
    label=text(number,(1.343*math.cos(a),-.375,1.343*math.sin(a)),.11,ink,True,'CENTER')
    label.data.align_y='CENTER';label.data.extrude=.0015;label.data.resolution_u=8
    # Align each engraving radially; all rotate with the calibrated collar.
    label.rotation_euler.rotate_axis('Z',a-math.pi/2)
rod('Index notch',(0,-.42,1.34),(0,-.42,1.43),.008,dark)
for i in range(25):
    a=math.radians(-25+i*5);x=1.69;y=.04+.26*math.cos(a);z=.26*math.sin(a)
    rod('Side dial fine tick',(x,y,z),(x+.065,y,z),.004,ink)

with bpy.data.libraries.load(str(BASE/'WoodSteelLongbow_Editable.blend'),link=False) as (a,b):
    b.objects=['SK_WoodSteelLongbow_Original','SM_WoodSteelLongbow_Optic4x']
body,donor=b.objects
for obj in [body,donor]:scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=False
info=json.loads((BASE/'authoring.json').read_text())
aim=Vector(info['optic_aim_center_cm']);pin=Vector((aim.x,-aim.y,aim.z))
S=1.75
rot=Matrix.Rotation(-math.pi/2,4,'Z')
# Put the front glass center at the accepted bow ADS optical point.
convert=Matrix.Translation(pin)@Matrix.Scale(S,4)@rot@Matrix.Translation(Vector((0,.31,0)))
moving=[];fixed=[]
zoom_prefix=('Calibrated magnification collar','Magnification grip rib','Scale tick','Label ','Collar edge bead')
for obj in list(parts):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if obj.type!='MESH':bpy.ops.object.convert(target='MESH');obj=bpy.context.object
    for mod in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.transform(convert@obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
    (moving if obj.name.startswith(zoom_prefix) else fixed).append(obj)

# A saddle made against the host surface; no whole-object bounds fitting.
tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
verts=[];faces=[];nx,nz=9,19
for iz in range(nz):
    z=pin.z-2.3+4.6*iz/(nz-1)
    for ix in range(nx):
        x=1+1.1*(ix/(nx-1)*2-1)
        hit,_,_,_=tree.ray_cast(Vector((x,12,z)),Vector((0,-1,0)),24)
        if hit is None:raise RuntimeError('Saddle does not reach the retained upper metal socket')
        verts.append(hit+Vector((0,.025,0)))
# Inner face follows the host; a machined planar outer face carries the inset.
outer_y=max(v.y for v in verts)+.24
verts.extend([Vector((v.x,outer_y,v.z)) for v in list(verts)])
count=nx*nz
for offset in [0,count]:
    for iz in range(nz-1):
        for ix in range(nx-1):
            i=offset+iz*nx+ix;faces.append((i,i+1,i+1+nx,i+nx))
border=list(range(nx))+[z*nx+nx-1 for z in range(1,nz)]+list(range(count-2,count-nx-1,-1))+[z*nx for z in range(nz-2,0,-1)]
for a,b in zip(border,border[1:]+border[:1]):faces.append((a,b,b+count,a+count))
mesh=bpy.data.meshes.new('Fitted closed saddle');mesh.from_pydata(verts,[],faces)
seat=bpy.data.objects.new('Fitted closed saddle',mesh);scene.collection.objects.link(seat);seat.data.materials.append(silver);fixed.append(seat)
bevel=seat.modifiers.new('Machined saddle edges','BEVEL');bevel.width=.045;bevel.segments=3
seat.modifiers.new('Weighted saddle normals','WEIGHTED_NORMAL')
contact=Vector((1,outer_y,pin.z-1.45))
points=[contact+Vector((0,.20,0)),Vector((pin.x+.75,pin.y-3.25,pin.z-1.45)),Vector((pin.x+.55,pin.y-1.72,pin.z-1.72))]
for a,b in zip(points,points[1:]):fixed.append(rod('Fitted silver support',a,b,.16,silver))
woodpiece=cube('Walnut seat accent',contact+Vector((.0,.31,.90)),(1.50,.075,1.00),wood,.10)
fixed.append(woodpiece)
for zoff in [-.55,2.0]:
    pos=contact+Vector((0,.29,zoff));fixed.append(rod('Saddle brass screw',pos,pos+Vector((0,.08,0)),.10,brass))
    fixed.append(rod('Saddle slot',pos+Vector((-.055,.085,0)),pos+Vector((.055,.085,0)),.012,ink))

# Retain the accepted physical lens UV mapping, then resize about its real center.
lens=donor.copy();lens.data=donor.data.copy();scene.collection.objects.link(lens);lens.name='Peakwatch physical lens'
bm=bmesh.new();bm.from_mesh(lens.data)
remove=[f for f in bm.faces if not lens.data.materials[f.material_index].name.startswith('M_BowOptic_Glass')]
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(lens.data);bm.free();lens.data.transform(lens.matrix_world);lens.matrix_world=Matrix.Identity(4)
low=Vector(tuple(min(v.co[i] for v in lens.data.vertices) for i in range(3)))
high=Vector(tuple(max(v.co[i] for v in lens.data.vertices) for i in range(3)));oldcenter=(low+high)/2
radial=(1.115*S)/((high.y-low.y)*.5)
for v in lens.data.vertices:
    p=v.co-oldcenter;v.co=pin+Vector((p.x*.65,p.y*radial,p.z*radial))
glass=scope['glass'];glass.name='M_Peakwatch_Glass';lens.data.materials.clear();lens.data.materials.append(glass)
for f in lens.data.polygons:f.material_index=0
for obj in [body,donor]:bpy.data.objects.remove(obj,do_unlink=True)

def prepare(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    for mod in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.uv_layers.active.name='UVMap'
for obj in fixed+moving:prepare(obj)

# Native procedural walnut baked to a compact color texture for the inset.
nodes=wood.node_tree.nodes;links=wood.node_tree.links;bs=nodes.get('Principled BSDF')
texcoord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(5,5,100)
links.new(texcoord.outputs['Generated'],mapping.inputs[0]);noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1.8;noise.inputs['Detail'].default_value=4
links.new(mapping.outputs[0],noise.inputs['Vector']);ramp=nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=(.028,.007,.003,1)
ramp.color_ramp.elements[1].position=.78;ramp.color_ramp.elements[1].color=(.24,.090,.035,1)
links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bs.inputs['Base Color'])
im=bpy.data.images.new('T_Peakwatch_WalnutBaseColor',width=1024,height=1024,alpha=False)
target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
bpy.ops.object.select_all(action='DESELECT');woodpiece.select_set(True);bpy.context.view_layer.objects.active=woodpiece
bpy.ops.object.bake(type='DIFFUSE');im.filepath_raw=str(P/'Textures/T_Peakwatch_WalnutBaseColor.png');im.file_format='PNG';im.save()
links.new(target.outputs['Color'],bs.inputs['Base Color'])

def combine(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    return obj
body=combine(fixed+[lens],'SM_Highland_Peakwatch3to6')
collar=combine(moving,'SM_Highland_PeakwatchZoomRing');collar.data.transform(Matrix.Translation(-pin))
objects=[body,collar];records=[]
for obj in objects:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    records.append({'mesh':obj.name,'triangles':len(obj.data.polygons),'materials':[m.name for m in obj.data.materials]})
collar.location=pin
scene.render.bake.use_pass_direct=True;scene.render.bake.use_pass_indirect=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_Peakwatch3to6_Production.blend'))
(P/'authoring.json').write_text(json.dumps({'assets':records,'aim_center_cm':list(aim),'ring_mount_cm':list(aim),
 'eye_distance_cm':info['optic_eye_distance_cm'],'degrees_per_power':-37,'min_magnification':3,'max_magnification':6,
 'unit':'cm; retained original bow export axes','source':str(CONCEPT/'Highland_Scope3to6_Concept_v1.blend'),
 'physical_lens_uv_source':str(BASE/'WoodSteelLongbow_Editable.blend'),
 'gameplay_tested':False},indent=2),encoding='utf-8')
print('PEAKWATCH_PRODUCTION_AUTHORED',flush=True)

# Only the needed catalog icon is rendered; no gameplay/acceptance render.
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
for obj in objects:
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
pts=[v.co for obj in objects for v in obj.data.vertices]
low=Vector(tuple(min(p[i] for p in pts) for i in range(3)));high=Vector(tuple(max(p[i] for p in pts) for i in range(3)));center=(low+high)*.5
for obj in objects:obj.data.transform(Matrix.Scale(.20,4)@Matrix.Translation(-center))
apply_grayscale(objects);neutral_output(scene)
# Tiny etched lines for the source icon only; UE glass draws the live reticle in UV.
iconpin=(pin-center)*.20;r=1.115*S*.20
for a,b in [(Vector((0,-r,0)),Vector((0,r,0))),(Vector((0,0,-r)),Vector((0,0,r)))]:
    rod('Icon reticle',iconpin+a+Vector((-.03,0,0)),iconpin+b+Vector((-.03,0,0)),.002,ink)
scene.unit_settings.scale_length=1
camdata=bpy.data.cameras.new('CatalogCamera');camdata.type='ORTHO';camdata.ortho_scale=2.25
cam=bpy.data.objects.new('CatalogCamera',camdata);scene.collection.objects.link(cam);cam.location=(-4,-2.8,0);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
bpy.context.view_layer.update()
local=[cam.matrix_world.inverted()@(obj.matrix_world@v.co) for obj in objects for v in obj.data.vertices]
lo=Vector(tuple(min(v[i] for v in local) for i in range(3)));hi=Vector(tuple(max(v[i] for v in local) for i in range(3)))
cam.location+=cam.rotation_euler.to_matrix()@Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,0))
camdata.ortho_scale=max(hi.x-lo.x,hi.y-lo.y)/.82
for name,location,power,size in [('Key',(-3,-2,3),130,3),('Fill',(-2,3,1),70,2),('Edge',(2,0,3),90,2)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=location;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('IconWorld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.film_transparent=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(P/'peakwatch_actual_part.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Peakwatch_Icon_Input.blend'));bpy.ops.render.render(write_still=True)
print('PEAKWATCH_ICON_INPUT_SAVED',flush=True)
