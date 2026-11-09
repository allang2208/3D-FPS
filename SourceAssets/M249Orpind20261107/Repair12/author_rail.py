"""Author a thin forward rail seat for the two long-footprint common optics."""
from pathlib import Path
import bpy,math
r=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.
parts=[]
def prism(name,x0,x1,cross):
    v=[(x*.01,y*.01,z*.01) for x in (x0,x1) for y,z in cross];n=len(cross)
    f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);parts.append(o);return o
prism('Continuous keyed rail base',-7.5,7.5,[(-.72,0.),(.72,0.),(.72,.26),(-.72,.26)])
for i in range(15):
    x=-7.5+i
    prism('Machined rail tooth',x,x+.72,[(-.68,.23),(.68,.23),(1.06,.47),(1.06,.65),(-1.06,.65),(-1.06,.47)])
for x in (-5.,-1.):
    for side in (-1,1):
        prism('Native rail clamp',x-.45,x+.45,[(side*.62,-.15),(side*1.04,-.15),(side*1.04,.25),(side*.62,.25)])
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0023,depth=.0016,location=(x*.01,side*.0108,.0005),rotation=(math.pi/2,0,0));parts.append(bpy.context.object)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='SM_M249_CommonRail'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
b=bpy.context.object.modifiers.new('Fine machined edges','BEVEL');b.width=.00022;b.segments=2;b.affect='EDGES';bpy.ops.object.modifier_apply(modifier=b.name)
for face in o.data.polygons:face.use_smooth=False
mat=bpy.data.materials.new('M249_CommonRail');o.data.materials.clear();o.data.materials.append(mat)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(r/'M249_CommonRail.blend'))
bpy.ops.export_scene.fbx(filepath=str(r/'SM_M249_CommonRail.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True)
print('M249 common rail source exported',flush=True)
