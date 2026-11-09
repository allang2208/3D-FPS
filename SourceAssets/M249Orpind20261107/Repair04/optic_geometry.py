"""One factory optical unit at its source rail height, without the paired sight or riser."""
import bpy
import numpy as np
from mathutils import Matrix,Vector
def align_optics(parts,components,rig,bind_rigid,slot):
    def point(x,y,z):return Vector((.0545+y/100,.286-x/100,z/100-.053))
    rear=point(20.70,.14,9.775);front=point(12.59,.17,9.913)
    rotation=(front-rear).normalized().rotation_difference(Vector((0,1,0)))
    align=Matrix.Translation(rear)@rotation.to_matrix().to_4x4()@Matrix.Translation(-rear)
    for key in ('Magnifier','MagnifierGlass'):parts[key].data.transform(align)
    # The factory magnifier now stands alone. Give the game ADS a small, clear
    # aiming reference inside its own lens rather than retaining the removed holo.
    center=point(12.61,.14,9.775);radius=.00025
    coords=[center+Vector((np.cos(a)*radius,0,np.sin(a)*radius)) for a in np.linspace(0,2*np.pi,16,endpoint=False)]
    mesh=bpy.data.meshes.new('M249_MagnifierReticle');mesh.from_pydata(coords,[],[list(range(16))]);mesh.update()
    obj=bpy.data.objects.new('M249_MagnifierReticle',mesh);bpy.context.collection.objects.link(obj)
    slot(obj,'M249_MagnifierReticle');bind_rigid(obj,'PKM_Cover')
    parts['MagnifierReticle']=obj;components.append(obj)
