"""Align the two game optics, retain independent pieces and provide an open visual aperture."""
import bpy
import numpy as np
from mathutils import Matrix,Vector

def align_optics(parts,components,rig,bind_rigid,slot):
    # Source positions expressed in the viewmodel's Blender authoring basis, in metres.
    def point(x,y,z):return Vector((.0545+y/100,.286-x/100,z/100-.053))
    rear=point(20.70,.14,9.775)
    front=point(12.59,.17,9.913)
    target_rear=point(20.70,.156,13.696)
    direction=Vector((0,1,0))
    rotation=(front-rear).normalized().rotation_difference(direction)
    transform=Matrix.Translation(target_rear)@rotation.to_matrix().to_4x4()@Matrix.Translation(-rear)
    for key in ("Magnifier","MagnifierYoke","MagnifierGlass"):
        parts[key].data.transform(transform)
    # The source's folded support yoke crosses the optical aperture. Give this
    # visual bracket a clean opening following the measured tube centre.
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.0118,depth=.052,
                                      location=point(11.7,.156,13.696),rotation=(np.pi/2,0,0))
    cutter=bpy.context.object
    yoke=parts["MagnifierYoke"]
    bpy.context.view_layer.objects.active=yoke
    mod=yoke.modifiers.new("Optical clearance","BOOLEAN")
    mod.operation="DIFFERENCE";mod.solver="EXACT";mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    # A dedicated mount joins the raised magnifier's foot to the existing top rail.
    bpy.ops.mesh.primitive_cube_add(size=1,location=point(16.7,.15,8.42))
    block=bpy.context.object;block.name="M249_MagnifierRiser"
    block.dimensions=(.026,.081,.0392)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bevel=block.modifiers.new("Edge bevel","BEVEL");bevel.width=.0013;bevel.segments=2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    slot(block,"M249_Riser")
    bind_rigid(block,"PKM_Cover")
    parts["MagnifierRiser"]=block;components.append(block)
