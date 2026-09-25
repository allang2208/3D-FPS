"""Author a 76 cm wooden arrow with a nock, three vanes and a steel point."""
import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
(P/'Export').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
materials=[]
for name,colour,metal,rough in [('ArrowWood',(.13,.055,.018,1),0,.61),('ArrowSteel',(.17,.19,.21,1),.85,.28),('ArrowFeather',(.19,.20,.16,1),0,.8),('ArrowNock',(.09,.075,.05,1),0,.52)]:
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=colour
    bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=colour
    bsdf.inputs['Metallic'].default_value=metal;bsdf.inputs['Roughness'].default_value=rough;materials.append(m)
def cylinder(name,radius,depth,x,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=depth,location=(x,0,0),rotation=(0,math.pi/2,0))
    o=bpy.context.object;o.name=name;o.data.materials.append(materials[mat]);return o
objects=[cylinder('StraightWoodShaft',.003,.70,-.01,0),cylinder('NockCollar',.004,.017,-.3635,3)]
vertices=[(.333,-.009,0),(.333,0,.0025),(.333,.009,0),(.333,0,-.0025),(.38,0,0)]
m=bpy.data.meshes.new('SteelPoint');m.from_pydata(vertices,[],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)]);m.materials.append(materials[1])
o=bpy.data.objects.new('SteelPoint',m);bpy.context.collection.objects.link(o);objects.append(o)
for a in (0,2*math.pi/3,4*math.pi/3):
    vertices=[]
    for x,r,z in [(-.34,.003,-.0005),(-.335,.014,-.0005),(-.267,.005,-.0005),(-.26,.003,-.0005),
                  (-.34,.003,.0005),(-.335,.014,.0005),(-.267,.005,.0005),(-.26,.003,.0005)]:
        vertices.append((x,r*math.cos(a)-z*math.sin(a),r*math.sin(a)+z*math.cos(a)))
    m=bpy.data.meshes.new('Feather');m.from_pydata(vertices,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);m.materials.append(materials[2])
    o=bpy.data.objects.new('Feather',m);bpy.context.collection.objects.link(o);objects.append(o)
# Split nock ears leave an actual string slot at the rear, not a solid cylinder.
for y in (-.0028,.0028):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(-.377,y,0));o=bpy.context.object;o.scale=(.006,.002,.007)
    o.data.materials.append(materials[3]);objects.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();arrow=bpy.context.object;arrow.name='SM_Bow_WoodArrow'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WoodArrow_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'Export/SM_Bow_WoodArrow.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
print('BOW_WOOD_ARROW_EXPORTED',flush=True)
