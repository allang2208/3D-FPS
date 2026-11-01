"""Apply the same bounded thumb-only fit to the retained native rear grip."""
from pathlib import Path
code=(Path(__file__).parent/'thumb.py').read_text()
code=code.replace("'thumb_01_l','thumb_02_l','thumb_03_l'","'thumb_01_r','thumb_02_r','thumb_03_r'")
code=code.replace("tree=BVHTree.FromPolygons([rt@advanced_rest@v.co for v in advanced.data.vertices],[tuple(p.vertices) for p in advanced.data.polygons])", """ev=bpy.data.objects['M24_base'].evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons]);ev.to_mesh_clear()""")
code=code.replace("target_tip=rt@Vector((-.033,.354,.100));target_ip=rt@Vector((-.040,.342,.086))","target_tip=rt@Vector((-.028,.009,.058));target_ip=rt@Vector((-.023,-.008,.075))")
code=code.replace("tip_local=Vector((.020,0,0))","tip_local=Vector((-.020,0,0))")
code=code.replace("thumb_deltas.json","right_thumb_deltas.json").replace("thumb_fit.json","right_thumb_fit.json")
code=code.replace("view(fixed,folder/'thumb.png','thumb');view(fixed,folder/'idle.png')","""set_pose(fixed);advanced.matrix_world=rt@advanced_rest
target=fixed['thumb_02_r'].translation;cam.location=target+rt.to_3x3()@Vector((-.22,-.13,.12));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.20
s.render.filepath=str(folder/'right_thumb.png');bpy.ops.render.render(write_still=True)
view(fixed,folder/'right_idle.png')""")
exec(compile(code,'right_thumb_fit','exec'))
