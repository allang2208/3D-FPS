"""Build a body extension from the Viper's actual compound muzzle nose."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

def derive_interface(parts,source_to_part):
    part=next(p for p in parts if p['identity']=='2011pv barrel compensator_2' and p['material']=='h-190')
    vertices=[];lookup={};remap={}
    for i,point in enumerate(part['verts']):
        point=source_to_part@Vector(point);key=tuple(round(c,7) for c in point)
        if key not in lookup:lookup[key]=len(vertices);vertices.append(point)
        remap[i]=lookup[key]
    faces=[tuple(remap[i] for i in face) for face in part['faces']]
    bvh=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
    cap=[];rake=[]
    for face in faces:
        polygon=[vertices[i] for i in face]
        cross=(polygon[1]-polygon[0]).cross(polygon[2]-polygon[0])
        if cross.length<1e-10:continue
        n=cross.normalized()
        # Select the exterior nose, including the side bevels and the LOWER
        # side-elevation rake. Rear roof-port walls are not the mating nose.
        # Near-longitudinal shoulder walls have a tiny positive X normal but
        # belong to the housing sides; extruding them as cap faces folds the rim.
        if n.x<=.25 or min(p.x for p in polygon)<.0079 or max(p.x for p in polygon)<.013:continue
        center=sum(polygon,Vector())/len(polygon)
        hit,_,_,_=bvh.ray_cast(Vector((.080,center.y,center.z)),Vector((-1,0,0)),.15)
        if hit is None or abs(hit.x-center.x)>.000002:continue
        cap.append(face)
        if .8<n.x<.9 and abs(n.y)<.02 and n.z<-.4:rake.append((n,cross.length/2))
    if not cap:raise RuntimeError('The actual exterior Viper muzzle nose could not be constructed')
    edge_counts={}
    for face in cap:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)));edge_counts[key]=edge_counts.get(key,0)+1
    remaining={edge for edge,count in edge_counts.items() if count==1};loops=[]
    while remaining:
        a,b=next(iter(remaining));remaining.remove(tuple(sorted((a,b))));loop=[a,b]
        while loop[-1]!=loop[0]:
            following=next((edge for edge in remaining if loop[-1] in edge),None)
            if following is None:raise RuntimeError('The source nose boundary has an open chain')
            remaining.remove(following);loop.append(following[1] if following[0]==loop[-1] else following[0])
        loops.append(loop[:-1])
    def area(loop):
        return sum(vertices[a].y*vertices[b].z-vertices[b].y*vertices[a].z
            for a,b in zip(loop,loop[1:]+loop[:1]))/2
    outer=max(loops,key=lambda loop:abs(area(loop)))
    if area(outer)<0:outer.reverse()
    # The cap is a piecewise planar surface, so preserve the original triangles.
    # Temporarily fill its barrel/vent holes; dedicated SI passage cutters reopen
    # the required aperture after this exact host surface has been extruded.
    filled=list(cap)
    for loop in loops:
        if loop is outer:continue
        points=[vertices[i] for i in loop]
        for tri in tessellate_polygon([points]):
            indices=tuple(loop[p if isinstance(p,int) else points.index(p)] for p in tri)
            cross=(vertices[indices[1]]-vertices[indices[0]]).cross(vertices[indices[2]]-vertices[indices[0]])
            filled.append(indices if cross.x>0 else indices[::-1])
    used=sorted({i for face in filled for i in face});compact={i:k for k,i in enumerate(used)}
    points=[vertices[i] for i in used]
    nose=max(p.x for p in points);width=max(p.y for p in points)-min(p.y for p in points)
    copper=next(p for p in parts if p['identity']==part['identity'] and p['material']=='copper')
    barrel=[source_to_part@Vector(v) for v in copper['verts']]
    radius=max(math.hypot(p.y,p.z) for p in barrel if p.x>=-.00002)
    rake_normal=sum((n*w for n,w in rake),Vector()).normalized()
    return {'source':'2011pv barrel compensator_2 / h-190: visible exterior factory nose triangles',
        'fit':'native muzzle nose kept; its exact compound face forms the reciprocal rear cap of the SI body extension',
        'cap_vertices_m':[list(p) for p in points],
        'cap_faces':[[compact[i] for i in face] for face in filled],
        'outer_boundary':[compact[i] for i in outer],
        'native_muzzle_x_m':nose,'extension_length_m':.029,'rear_overlap_m':.00004,
        'body_width_m':width,'top_m':max(p.z for p in points),'bottom_m':min(p.z for p in points),
        'side_rake_normal':[float(c) for c in rake_normal],
        'side_rake_from_vertical_deg':math.degrees(math.atan2(-rake_normal.z,rake_normal.x)),
        'barrel_seat_radius_m':radius+.00012,'barrel_seat_front_m':nose+.002,
        'native_geometry_retained':'complete original h-190 muzzle housing and rear sight bridge; original skeletal section remains hidden for this replacement only',
        'width_policy':'exact native nose silhouette extruded along bore axis; no sidewall widening or rear collar flare'}

def shell_loft(contract,length,top):
    rear=[Vector(v) for v in contract['cap_vertices_m']]
    extension=contract['extension_length_m'];overlap=contract['rear_overlap_m']
    vertices=[(p.x-overlap,p.y,p.z) for p in rear]+[(p.x+extension,p.y,p.z) for p in rear]
    count=len(rear);faces=[tuple(reversed(face)) for face in contract['cap_faces']]
    faces.extend(tuple(count+i for i in face) for face in contract['cap_faces'])
    ring=contract['outer_boundary']
    for a,b in zip(ring,ring[1:]+ring[:1]):faces.append((a,b,count+b,count+a))
    return vertices,faces
