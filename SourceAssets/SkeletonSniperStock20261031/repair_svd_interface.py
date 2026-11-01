"""Finish the SVD connector's cap triangulation after the FBX tangent warning."""
import bpy,bmesh,json,shutil
from pathlib import Path
O=Path(__file__).resolve().parent
path=O/'SkeletonSniperStock_SVD_Editable.blend'
backup=O/'Before/SkeletonSniperStock_SVD_Editable.blend'
if not backup.exists():shutil.copy2(path,backup)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
parts=[bpy.data.objects['SniperSkeleton_SVD'],bpy.data.objects['SniperStock_SVD_Interface0']]
report={}
for ob in parts:
    ob.data.calc_tangents()
    report[ob.name]={'triangles_before':len(ob.data.polygons),'zero_tangents_before':sum(v.tangent.length<.0001 for v in ob.data.loops)}
    bpy.context.view_layer.objects.active=ob
    weld=ob.modifiers.new('SubpixelSeamCleanup','WELD');weld.merge_threshold=.00001
    bpy.ops.object.modifier_apply(modifier=weld.name)
    report[ob.name]['triangles_after_subpixel_cleanup']=len(ob.data.polygons)
ob=parts[1]
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
bmesh.ops.triangulate(bm,faces=list(bm.faces))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(ob.data);bm.free();ob.data.update()
uv=ob.data.uv_layers.active
for face in ob.data.polygons:
    points=[ob.data.vertices[ob.data.loops[i].vertex_index].co for i in face.loop_indices]
    origin=points[0];axis=(points[1]-origin).normalized();up=face.normal.cross(axis).normalized()
    for i,p in zip(face.loop_indices,points):uv.data[i].uv=((p-origin).dot(axis)*20,(p-origin).dot(up)*20)
ob.data.update();ob.data.calc_tangents()
report[ob.name].update(triangles_after=len(ob.data.polygons),zero_tangents_after=sum(v.tangent.length<.0001 for v in ob.data.loops))
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.wm.save_as_mainfile(filepath=str(path))
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_SniperSkeleton_SVD.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
(O/'svd_interface_finish.json').write_text(json.dumps(report,indent=2))
print('SVD_INTERFACE_FINISHED',json.dumps(report),flush=True)
