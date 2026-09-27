"""Original open bow sight, fitted to the retained wooden riser. Dimensions in cm."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=.01
materials=[]
for name,color,metal,rough in [('BowSight_BlackSteel',(.025,.034,.042,1),.82,.34),
        ('BowSight_Brass',(.24,.13,.035,1),.8,.31),('BowSight_Fiber',(.20,.85,.38,1),.0,.26)]:
    m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    materials.append(m)
parts=[]
def finish(o,name,mat=0,bevel=.07):
    o.name=name;o.data.materials.append(materials[mat]);parts.append(o)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('Machined edges','BEVEL');m.width=bevel;m.segments=2
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o
def box(name,p,size,mat=0,bevel=.07):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=size
    return finish(o,name,mat,bevel)
def rod(name,a,b,r,mat=0,sides=16):
    a,b=Vector(a),Vector(b);d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,location=(a+b)/2)
    o=bpy.context.object;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
    return finish(o,name,mat,min(.025,r*.2))
# Two short side plates sit outside the seven-centimetre grip binding. The
# crosspiece stays above the gripping fingers and the arrow-rest corridor.
box('Clamp_left',(-1.1,-3.65,11.5),(4.5,.6,3.8))
box('Clamp_right',(-1.1,3.65,11.5),(4.5,.6,3.8))
for z in (10.1,12.9):
    rod('Clamp_tie',(.9,-4.25,z),(.9,4.25,z),.20,1)
    for y in (-4.2,4.2):rod('Clamp_hex',(.9,y-.18,z),(.9,y+.18,z),.40,0,6)
box('Offset_bracket',(-2.1,-8.8,11.5),(1.1,10.6,.85))
box('Vertical_adjuster',(-2.1,-13.9,12.65),(1.2,1.1,3.1))
for z in (11.65,12.25,12.85):box('Graduation',(-2.73,-13.9,z),(.06,.48,.07),1,.012)
rod('Elevation_knob',(-2.1,-14.6,12),(-2.1,-15.1,12),.65,1,20)
for a in range(16):
    theta=a*math.tau/16
    rod('Knurl',(-2.1+.64*math.cos(theta),-14.65,12+.64*math.sin(theta)),
        (-2.1+.64*math.cos(theta),-15.06,12+.64*math.sin(theta)),.045,0,6)
# Open top U protector. A single slim pin, as in the reference's small
# mechanical bow sight, leaves the target visible without a glass plane.
cx,cy,cz=-3.5,-13.9,14.6
path=[(cy-2.1,cz+1.85),(cy-2.1,cz-1.25),(cy-1.65,cz-2.0),
      (cy+1.65,cz-2.0),(cy+2.1,cz-1.25),(cy+2.1,cz+1.85)]
for (y,z),(ny,nz) in zip(path,path[1:]):rod('Open_guard',(cx,y,z),(cx,ny,nz),.145)
rod('Pin_stem',(cx,cy,cz-2),(cx,cy,cz-.16),.075)
rod('Fiber_bead',(cx-.15,cy,cz),(cx+.18,cy,cz),.095,2,12)
box('Guard_mount',(cx+.65,cy,cz-2.05),(2.15,1.0,.45))
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object
o.name='SM_Bow_OpenMechanicalSight';bpy.context.scene.cursor.location=(0,0,0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
# Convert the UE-native +X forward/+Y right authoring coordinates to Blender.
for v in o.data.vertices:v.co.y=-v.co.y
import bmesh
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
for poly in o.data.polygons:poly.use_smooth=False
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mod=o.modifiers.new('Triangulate','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_OpenMechanicalSight.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
(P/'sight-authoring.json').write_text(json.dumps({'sight_pin_cm':[cx,cy,cz],'material_slots':[m.name for m in o.data.materials],
    'triangles':len(o.data.polygons),'reference':'BV1jGdDBkEkc 39s, open mechanical sight; original fitted geometry',
    'geometry_units':'centimetres, UE +X forward +Y right Z up','runtime_tested':False},indent=2),encoding='utf8')
print('BOW_SIGHT_AUTHORED',len(o.data.polygons))
