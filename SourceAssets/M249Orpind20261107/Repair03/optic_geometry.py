"""Keep both optical bodies intact and fold the source cap clear of the bore."""
import bpy,numpy as np
from mathutils import Matrix,Vector

def align_optics(parts,components,rig,bind_rigid,slot):
    def point(x,y,z):return Vector((.0545+y/100,.286-x/100,z/100-.053))
    rear=point(20.70,.14,9.775);front=point(12.59,.17,9.913)
    target=point(20.70,.156,13.696)
    rotation=(front-rear).normalized().rotation_difference(Vector((0,1,0)))
    align=Matrix.Translation(target)@rotation.to_matrix().to_4x4()@Matrix.Translation(-rear)
    for key in ('Magnifier','MagnifierYoke','MagnifierGlass'):parts[key].data.transform(align)
    # This hinged front cap is part of the source art. Cutting a cylindrical
    # aperture through it leaves thin disconnected remnants. Keep the complete
    # piece, swing it aside about its original hinge, and retain the clear lens.
    pivot=align@point(12.7,2.4,7.35)
    axis=(align.to_3x3()@Vector((0,-1,0))).normalized()
    fold=Matrix.Translation(pivot)@Matrix.Rotation(np.radians(-80),4,axis)@Matrix.Translation(-pivot)
    parts['MagnifierYoke'].data.transform(fold)
    bpy.ops.mesh.primitive_cube_add(size=1,location=point(16.7,.15,8.42))
    block=bpy.context.object;block.name='M249_MagnifierRiser';block.dimensions=(.026,.081,.0392)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bevel=block.modifiers.new('Edge bevel','BEVEL');bevel.width=.0013;bevel.segments=2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    slot(block,'M249_Riser');bind_rigid(block,'PKM_Cover')
    parts['MagnifierRiser']=block;components.append(block)
