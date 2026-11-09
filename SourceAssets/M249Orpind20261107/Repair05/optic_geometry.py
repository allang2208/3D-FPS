"""Seat the retained factory magnifier directly on the existing cover rail."""
from pathlib import Path
import bpy,json,numpy as np
from mathutils import Matrix,Vector
from rail_contract import transform,fit_sole,sights,SOURCE_FRONT,SOURCE_FRAME,ROTATION,SOLE_ANCHOR,SEAT

def align_optics(parts,components,rig,bind_rigid,slot):
    # Original raw cm -> the native Blender metre bind frame used by author_mesh.
    def point(p):return Vector((.0545+p[1]/100,.286-p[0]/100,p[2]/100-.053))
    def raw(v):return np.array([(.286-v[1])*100,(v[0]-.0545)*100,(v[2]+.053)*100])
    base=np.array([[0,1,0],[-1,0,0],[0,0,1.]])
    for key in ('Magnifier','MagnifierGlass'):
        mesh=parts[key].data
        old=np.array([raw(v.co) for v in mesh.vertices])
        q=fit_sole(old) if key=='Magnifier' else transform(old)
        # Keep the original UV atlas and rotate its split normals with the body.
        normals=np.array([n.vector[:] for n in mesh.corner_normals])
        for v,p in zip(mesh.vertices,q):v.co=point(p)
        mesh.update()
        normals=normals@(base@ROTATION@base.T).T
        mesh.normals_split_custom_set(normals.tolist())
    center=transform(SOURCE_FRONT+SOURCE_FRAME[:,0]*.02)
    right,up=ROTATION@SOURCE_FRAME[:,1],ROTATION@SOURCE_FRAME[:,2]
    # At 20 cm eye relief, the old 0.025 cm radius fell between pixel samples
    # at 720p. Keep a small but reliably covered dot without shifting its axis.
    coords=[point(center+.055*(np.cos(a)*right+np.sin(a)*up)) for a in np.linspace(0,2*np.pi,16,endpoint=False)]
    mesh=bpy.data.meshes.new('M249_MagnifierReticle');mesh.from_pydata(coords,[],[list(range(16))]);mesh.update()
    obj=bpy.data.objects.new('M249_MagnifierReticle',mesh);bpy.context.collection.objects.link(obj)
    slot(obj,'M249_MagnifierReticle');bind_rigid(obj,'PKM_Cover')
    parts['MagnifierReticle']=obj;components.append(obj)
    report={'contact_source_cm':SOLE_ANCHOR.tolist(),'rail_seat_cm':SEAT.tolist(),'sight_points_raw_cm':sights(),
            'attachment_bone':'PKM_Cover','mount':'original shoe conformed to existing rail; no added riser'}
    (Path(__file__).parent/'mount_authored.json').write_text(json.dumps(report,indent=2),encoding='utf8')
