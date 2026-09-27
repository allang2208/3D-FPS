"""Check winding of the saved UE mesh exports, without rendering or gameplay."""
import bpy,bmesh,json
from pathlib import Path
P=Path(__file__).parent
result=[]
for source in sorted((P/'SavedAssetReadback').glob('SK_Bow_Flex_*.fbx')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    for o in bpy.data.objects:
        if o.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
        bm.normal_update();bm.faces.ensure_lookup_table();before=[f.normal.copy() for f in bm.faces]
        volume=bm.calc_volume(signed=True)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
        reversed_faces=sum(n.dot(f.normal)<-.9 for n,f in zip(before,bm.faces))
        result.append({'asset':source.stem,'faces':len(bm.faces),'signed_volume':volume,'inward_faces':reversed_faces})
        bm.free()
(P/'saved-surface-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
if len(result)!=4 or any(r['signed_volume']<=0 or r['inward_faces'] for r in result):
    raise RuntimeError('Saved mesh surface diagnosis needs attention: '+str(result))
print('BOW_SAVED_SURFACES_OUTWARD',json.dumps(result))
