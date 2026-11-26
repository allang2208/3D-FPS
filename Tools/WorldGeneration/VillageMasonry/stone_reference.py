"""Sample the actual stone islands and vertex blends of the Normandy ruined house."""
from collections import defaultdict
from math import sqrt

import unreal as u

Q = u.GeometryScript_MeshQueries
L = u.GeometryScript_List
MI = '/Game/UnrealNormandy/MaterialInstances/'
SOURCE = '/Game/UnrealNormandy/StaticMeshes/'


def require(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing authored asset '+path)
    return obj


def read_mesh(obj):
    dm, result = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(obj,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read source geometry: '+obj.get_path_name())
    return dm


def xyz(v):
    return (v.x,v.y,v.z)


def mesh_data(dm):
    _,v,gap_v = Q.get_all_vertex_positions(dm,False)
    _,f,gap_f = Q.get_all_triangle_indices(dm,False)
    if gap_v or gap_f:
        raise RuntimeError('Expected compact, material-assigned static mesh')
    triangles=[xyz(t) for t in L.convert_triangle_list_to_array(f)]
    mat_ids=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(triangles))]
    return ([xyz(p) for p in L.convert_vector_list_to_array(v)],
            triangles,mat_ids)


def islands(points, triangles, mat_ids):
    # Even hard-normal and UV seams belong to the same stone. Keep different
    # materials separate where the mason has bedded two touching faces.
    roots=list(range(len(triangles)))
    corners={}
    def find(i):
        while roots[i]!=i:
            roots[i]=roots[roots[i]]
            i=roots[i]
        return i
    for i,triangle in enumerate(triangles):
        for vi in triangle:
            key=(mat_ids[i],*(round(a,3) for a in points[vi]))
            old=corners.setdefault(key,i)
            if old!=i:
                roots[find(i)]=find(old)
    groups=defaultdict(list)
    for i in range(len(triangles)):
        groups[find(i)].append(i)
    return list(groups.values())


def limits(points):
    axes=list(zip(*points))
    lo=tuple(min(axis) for axis in axes)
    return lo,tuple(max(axis)-v for axis,v in zip(axes,lo))


def normal(a,b,c):
    # The render buffer's UE front face is clockwise.
    v=[c[i]-a[i] for i in range(3)]
    w=[b[i]-a[i] for i in range(3)]
    n=(v[1]*w[2]-v[2]*w[1],v[2]*w[0]-v[0]*w[2],v[0]*w[1]-v[1]*w[0])
    d=sqrt(sum(k*k for k in n)) or 1.
    return tuple(k/d for k in n)


class StoneReference:
    def __init__(self):
        self.blocks=[]
        self.paint=defaultdict(list)
        for label in ('SM_H_OldWall_00A','SM_H_OldWall_Window_00A','SM_H_OldWall_00A_PieceA'):
            asset=require(SOURCE+label)
            dm=read_mesh(asset)
            pts,tris,ids=mesh_data(dm)
            _,colors,valid,_=u.GeometryScript_VertexColors.get_mesh_per_vertex_colors(dm,True)
            rgba=[(c.r,c.g,c.b,c.a) for c in L.convert_color_list_to_array(colors)] if valid else [(1.,1.,1.,1.)]*len(pts)
            slots=[s.material_interface.get_name() for s in asset.static_materials]
            for group in islands(pts,tris,ids):
                slot=slots[ids[group[0]]]
                indices=sorted({v for t in group for v in tris[t]})
                for k in indices:
                    self.paint[slot].append(rgba[k])
                if 'Mortar' in slot or len(group)<10 or len(group)>780:
                    continue
                lo,sp=limits(pts[v] for v in indices)
                if not (11<sp[0]<115 and 5<sp[1]<82 and 7<sp[2]<66):
                    continue
                # Open relief shells from a flush facade cannot cap a free-standing wall.
                normals=[normal(*(pts[v] for v in tris[t])) for t in group]
                if any(max(n[i] for n in normals)<.42 or min(n[i] for n in normals)>-.42 for i in range(3)):
                    continue
                mapped={v:i for i,v in enumerate(indices)}
                self.blocks.append(([(tuple((a-b)/d for a,b,d in zip(pts[v],lo,sp)),rgba[v]) for v in indices],
                    [tuple(mapped[v] for v in tris[t]) for t in group], sp))
        if not self.paint.get('MI_Main_StoneWall_00A'):
            raise RuntimeError('Could not resolve the original village wall stone slot')
        u.log('VILLAGE_MASONRY_REFERENCE islands=%d paint=%s' % (len(self.blocks),
              {s:(len(v),len(set(v))) for s,v in self.paint.items()}))

    def sample(self, material, point):
        colors=self.paint.get(material) or self.paint['MI_Main_StoneWall_00A']
        # Neighbouring corners within a small block of stone share their paint sample.
        x,y,z=(int(v//19.) for v in point)
        return colors[((x*73856093) ^ (y*19349663) ^ (z*83492791)) % len(colors)]
