"""Angle-limited gun shading; topology, UVs, weights and rig stay unchanged."""
import math
from collections import defaultdict
from mathutils import Vector

def repair_gun_normals(objects):
    result={}
    for obj in objects:
        mesh=obj.data
        if obj.name not in ('Super90_body','Super90_bolt','Super90_loading_gate','Super90_trigger'):
            continue
        mesh.update()
        # Weld positions for shading only, including UV seam duplicates. Faces
        # beyond 45 degrees retain their hard edge, as do material boundaries.
        corners=defaultdict(list)
        for face in mesh.polygons:
            for li in face.loop_indices:
                p=mesh.vertices[mesh.loops[li].vertex_index].co
                corners[(tuple(round(v,6) for v in p),face.material_index)].append((li,face))
        normals=[n.vector.copy() for n in mesh.corner_normals]
        limit=math.cos(math.radians(45))
        for cluster in corners.values():
            for li,face in cluster:
                value=Vector()
                for other_li,other in cluster:
                    if face.normal.dot(other.normal)>=limit:
                        # Area weighting keeps broad receiver faces planar
                        # while joining the small facets around tubes/stock.
                        value+=other.normal*other.area
                if value.length_squared>1.e-20:normals[li]=value.normalized()
        for face in mesh.polygons:face.use_smooth=True
        mesh.normals_split_custom_set(normals)
        mesh.update()
        result[obj.name]={'vertices':len(mesh.vertices),'triangles':len(mesh.polygons),'smooth_angle_degrees':45}
    return result
