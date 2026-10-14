import bpy,bmesh,pathlib,json
R=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(R/'output/Incinerator_Game.blend'))
o=bpy.data.objects['SM_Incinerator'];bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bad=[f for f in bm.faces if f.calc_area()<1e-13];n=len(bad);bmesh.ops.delete(bm,geom=bad,context='FACES');bm.to_mesh(o.data);bm.free();o.data.update()
m=json.loads((R/'output/material_and_geometry_manifest.json').read_text());m['removed_degenerate_triangles']=n
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
for level,ratio in [(0,1),(1,.5),(2,.2)]:
 if level:dec=o.modifiers.new('LOD simplification','DECIMATE');dec.ratio=ratio
 dg=bpy.context.evaluated_depsgraph_get();eo=o.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles();m['triangles_lod'+str(level)]=len(me.loop_triangles);eo.to_mesh_clear()
 bpy.ops.export_scene.fbx(filepath=str(R/f'output/SM_Incinerator_LOD{level}.fbx'),use_selection=True,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False)
 if level:o.modifiers.remove(dec)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'output/Incinerator_Game.blend'));(R/'output/material_and_geometry_manifest.json').write_text(json.dumps(m,indent=2));print('CLEAN',n)
