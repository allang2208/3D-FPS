"""Build one 4.32 m workshop dado using centimetres in the authored UE coordinates."""
from pathlib import Path
import bpy
from mathutils import Vector
r=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
pieces=[]
def prism(name,lo,hi,profile,bevel):
    # Profile is a cross-section (projection from the wall, elevation).
    vertices=[(x/100,-y/100,z/100) for y in (lo,hi) for x,z in profile]
    n=len(profile);faces=[list(range(n)),list(range(n,2*n))[::-1]]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    mod=ob.modifiers.new('Small dressed arris','BEVEL');mod.width=bevel/100;mod.segments=2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    uv=mesh.uv_layers.new(name='StoneInMetres')
    for face in mesh.polygons:
        norm=face.normal;za=abs(norm.z);xa=abs(norm.x);ya=abs(norm.y)
        for loop in face.loop_indices:
            v=mesh.vertices[mesh.loops[loop].vertex_index].co
            if za>max(xa,ya):a,b=-v.y,v.x+3.61
            elif xa>=ya:a,b=-v.y,v.z
            else:a,b=v.x,v.z
            uv.data[loop].uv=(a*.69+.14,b*.69+.32)
    pieces.append(ob);ob.select_set(False)
ends=[-216,-126,-18,88,216]
for i,(lo,hi) in enumerate(zip(ends,ends[1:])):
    offset=[.0,.16,-.11,.07][i]
    depth=4.7+offset
    prism('Dado %d'%i,lo+.17,hi-.17,[(-.65,.02),(depth-.30,.02),(depth,1.35),(depth,79.3),(depth-.42,80),(-.65,80)],.19)
for i,(lo,hi) in enumerate(zip([-216,-70,67],[-70,67,216])):
    prism('Cap %d'%i,lo+.19,hi-.19,[(-.8,80.14),(4.1,80.14),(5.5,81.5),(8.7,81.5),(9.5,82.4),(9.5,87.8),(8.6,88.8),(-.8,89.25)],.23)
for ob in pieces:ob.select_set(True)
bpy.context.view_layer.objects.active=pieces[0]
bpy.ops.object.join()
ob=pieces[0];ob.name='SM_WorkshopDadoBay';ob.data.materials.append(bpy.data.materials.new('Concrete'))
bpy.ops.export_scene.fbx(filepath=str(r/'SM_WorkshopDadoBay.fbx'),use_selection=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
