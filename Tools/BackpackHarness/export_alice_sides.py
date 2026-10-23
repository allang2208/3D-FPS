"""Export exact corner attributes using the existing ALICE local-axis contract."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpacksReview20261021'
bpy.ops.wm.open_mainfile(filepath=str(R/'AliceBackpack_side_openings.blend'))
ob=bpy.data.objects['SM_AliceBackpack'];me=ob.data;me.calc_loop_triangles()
original=json.loads((R/'alice_source.json').read_text())['positions']
centre=[(min(v[i] for v in original)+max(v[i] for v in original))*.5 for i in range(3)]
# The existing OBJ importer stored reflected local Z. Keep its mount/pivot
# contract; changing it here would silently rotate the worn pack.
def position(v):return [(v.x-centre[0])*100,(v.y-centre[1])*100,-(v.z-centre[2])*100]
data=dict(positions=[position(v.co) for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[])
layer=me.uv_layers.active
skipped=0;repaired_uv=0
for face in me.loop_triangles:
    loops=list(face.loops)[::-1]
    ids=[me.loops[li].vertex_index for li in loops]
    coords=np.array([data['positions'][vi] for vi in ids])
    pts=[Vector(x) for x in coords]
    cross=np.cross(coords[1]-coords[0],coords[2]-coords[0])
    if np.linalg.norm(cross)<1e-7:
        skipped+=1;continue
    tex=[[layer.data[li].uv.x,1-layer.data[li].uv.y] for li in loops]
    a=Vector(tex[1])-Vector(tex[0]);b=Vector(tex[2])-Vector(tex[0])
    if abs(a.x*b.y-a.y*b.x)<1e-12:
        # The imported buckle has 20 pre-existing collapsed wall triangles.
        # Give each wall its own local planar projection, keeping its atlas centre.
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(cross[i]))]
        uvcentre=sum((Vector(x) for x in tex),Vector((0,0)))/3
        pc=sum(pts,Vector())/3
        tex=[[uvcentre.x+(p[axes[0]]-pc[axes[0]])*.02,uvcentre.y+(p[axes[1]]-pc[axes[1]])*.02] for p in pts]
        repaired_uv+=1
    data['triangles'].append(ids)
    data['uv'].append(tex)
    data['normals'].append([[me.corner_normals[li].vector.x,me.corner_normals[li].vector.y,-me.corner_normals[li].vector.z] for li in loops])
    data['triangle_materials'].append(face.material_index)
data['source_blend_sha256']=hashlib.sha256((R/'AliceBackpack_side_openings.blend').read_bytes()).hexdigest()
data['revision']='AliceUEFrontFaceR2_20261022'
data['geometry_convention']='cross_e1_e2'
data['removed_source_degenerate_triangles']=skipped;data['repaired_source_uv_triangles']=repaired_uv
(R/'alice_authored.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('ALICE_AUTHORED_JSON',len(data['positions']),len(data['triangles']))
