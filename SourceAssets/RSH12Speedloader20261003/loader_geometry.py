"""Five-pocket carrier with the original 715 rear grip and release knob."""
import math,json
from mathutils import Vector,Matrix

def build(ctx):
    fit=ctx['FIT'];rest=ctx['rest'];root=ctx['root'];align=ctx['alignment']
    cx,cz,_=fit['cylinder_axis_xz_radius'];rear=fit['rear_plane_m']
    center=Vector((cx,rear+.0145,cz));donorcenter=Vector((0,0,.03092))
    donor_to_new=Matrix.Translation(center-donorcenter)
    ctx['newrest']['WPN_Loader']=root@align@donor_to_new@root.inverted()@rest['WPN_Loader']
    return donor_to_new

def emit(ctx,donor_to_new):
    import bpy
    make=ctx['make'];fit=ctx['FIT'];rest=ctx['rest'];root=ctx['root'];bone='WPN_Loader'
    polymer=bpy.data.materials.new('M_RSH12_LoaderPolymer');steel=bpy.data.materials.new('M_RSH12_LoaderSteel')
    def part(name,verts,faces,mat):
        normals=[];uv=[]
        for f in faces:
            normal=(Vector(verts[f[1]])-Vector(verts[f[0]])).cross(Vector(verts[f[2]])-Vector(verts[f[0]])).normalized()
            for i in f:normals.append(list(normal));uv.append((verts[i][0]*20,verts[i][2]*20))
        ob=make(dict(name=name,verts=verts,faces=faces,normals=normals,uv=uv),bone)
        ob.data.materials[0]=mat
    def ring(name,x,z,y0,y1,inner,outer,mat,steps=48):
        # Closed annular sleeve; real open pocket rather than a painted circle.
        verts=[]
        for y,radius in ((y0,outer),(y1,outer),(y0,inner),(y1,inner)):
            for j in range(steps):
                a=math.tau*j/steps;verts.append((x+radius*math.cos(a),y,z+radius*math.sin(a)))
        faces=[]
        for j in range(steps):
            k=(j+1)%steps
            faces.extend(((j,k,steps+k,steps+j),(2*steps+k,2*steps+j,3*steps+j,3*steps+k),
                (k,j,2*steps+j,2*steps+k),(steps+j,steps+k,3*steps+k,3*steps+j)))
        part(name,verts,faces,mat)
    # Keep the donor's held rear body/knob at exactly its original size. The
    # wider five-pocket front is ahead of the grasp instead of enlarging fingers.
    donor=json.loads((ctx['O']/'donor_loader_geometry.json').read_text())
    for src in donor:
        transform=root.inverted()@rest[bone]
        old=[transform@Vector(v) for v in src['verts']]
        selected=[f for f in src['faces'] if all(old[i].y>=-.006 for i in f)]
        ids=sorted({i for f in selected for i in f});remap={j:i for i,j in enumerate(ids)}
        part('Native715_GraspAndReleaseKnob',[list(donor_to_new@old[i]) for i in ids],[[remap[i] for i in f] for f in selected],polymer)
    cx,cz,_=fit['cylinder_axis_xz_radius'];rear=fit['rear_plane_m']
    # Five rings at measured (not idealized) centres preserve all chamber spacing.
    ring('CarrierHub',cx,cz,rear+.004,rear+.011,.0023,.0091,polymer)
    for i,chamber in enumerate(fit['chambers']):
        x,z,r=chamber['center_xz_radius']
        ring('Pocket_'+str(i),x,z,rear+.0008,rear+.0085,r+.00045,r+.0018,polymer)
        ring('RimRetainer_'+str(i),x,z,rear+.001,rear+.0024,r+.00030,r+.0007,steel,36)
        axis=Vector((x-cx,0,z-cz)).normalized();tangent=Vector((-axis.z,0,axis.x))*.0022
        a=Vector((cx,rear+.0065,cz))+axis*.006;b=Vector((x,rear+.0065,z))-axis*.004
        vertices=[list(p+tangent*s+Vector((0,dy,0))) for dy in (-.002,.002) for p,s in ((a,-1),(a,1),(b,1),(b,-1))]
        part('Web_'+str(i),vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],polymer)
    ctx['loader_recipe']=dict(capacity=5,grip='715 original rear body and release knob, unchanged size',
        pocket_centers=[c['center_xz_radius'][:2] for c in fit['chambers']],rear_clearance_m=.0008)
