"""Scoped surface diagnosis for the reported hollow bow workbench previews."""
import bpy,bmesh,json
from pathlib import Path
P=Path(__file__).parent
cases=[
 ('BowModular20260926/Bow_ModularParts.blend',('SM_Bow_BodyModular','SM_Bow_GripWrap','SM_Bow_ArrowRestWood','SM_Bow_ArrowRestLined')),
 ('BowFlex20260927/Bow_ElasticBodies.blend',('SK_Bow_Flex_',)),
 ('BowGripContact20260927/Bow_GripContact.blend',('SM_Bow_GripWrap_Fitted',)),
 ('BowGripSeries20260927/Bow_GripSeries.blend',('SM_Bow_Grip_',)),
 ('BowWoodBracket20260927/Bow_WoodBracketSight.blend',('SM_Bow_WoodBracketSight',))]
result=[]
for file,prefixes in cases:
    bpy.ops.wm.open_mainfile(filepath=str(P.parent/file))
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not any(obj.name.startswith(p) for p in prefixes):continue
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
        bm.normal_update();bm.faces.ensure_lookup_table()
        old=[f.normal.copy() for f in bm.faces]
        volume=bm.calc_volume(signed=True)
        boundary=sum(e.is_boundary for e in bm.edges)
        nonmanifold=sum(not e.is_manifold for e in bm.edges)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
        flipped=sum(n.dot(f.normal)<-.9 for n,f in zip(old,bm.faces))
        result.append({'file':file,'object':obj.name,'faces':len(bm.faces),'reoriented_faces':flipped,
                       'signed_volume_before':volume,'signed_volume_outward':bm.calc_volume(signed=True),
                       'boundary_edges_after_seam_weld':boundary,'nonmanifold_edges':nonmanifold,
                       'transform_determinant':obj.matrix_world.determinant(),'custom_normals':obj.data.has_custom_normals})
        bm.free()
(P/'source-surfaces.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('BOW_SURFACE_DIAGNOSIS',json.dumps(result))
