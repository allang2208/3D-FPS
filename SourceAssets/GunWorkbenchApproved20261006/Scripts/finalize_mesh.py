import bpy,json
from pathlib import Path
W=Path(__file__).resolve().parent;O=W.parent/'Authored' if W.name=='Scripts' else W/'game_ready';p=O/'manifest.json';d=json.loads(p.read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(O/'GunWorkbench_GameReady.blend'),load_ui=False,use_scripts=False)
o=bpy.data.objects['SM_GunWorkbench'];old=list(o.data.materials);used={poly.material_index for poly in o.data.polygons}
counts={m.name:sum(1 for poly in o.data.polygons if poly.material_index==i) for i,m in enumerate(old)}
print('MATERIAL_FACE_COUNTS',counts,flush=True)
assert not any(m.name.startswith('PROCEDURAL_') and i in used for i,m in enumerate(old)), 'Unbaked used material remains'
# Runtime Configure() overrides slot zero with the palette Surface. Keep bench wood in slot zero.
ordered=sorted([old[i] for i in used],key=lambda m:(m.name!='WSBench_BenchWood',old.index(m)))
remap={i:ordered.index(old[i]) for i in used};indices=[remap[p.material_index] for p in o.data.polygons]
o.data.materials.clear()
for m in ordered:o.data.materials.append(m)
for poly,i in zip(o.data.polygons,indices):poly.material_index=i
bpy.context.view_layer.objects.active=o;o.select_set(True)
tri=o.modifiers.new('Export triangles preserving normals','TRIANGULATE');tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
o.data.calc_loop_triangles();assert len(o.data.loop_triangles)==d['triangles']
bpy.ops.object.make_local(type='ALL');bpy.data.orphans_purge(do_recursive=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'GunWorkbench_GameReady.blend'))
bpy.ops.object.select_all(action='DESELECT');o=bpy.data.objects['SM_GunWorkbench'];o.hide_set(False);o.hide_viewport=False;o.hide_render=False;o.select_set(True);bpy.context.view_layer.objects.active=o
bpy.ops.export_scene.fbx(filepath=str(O/'SM_GunWorkbench.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
assert (O/'SM_GunWorkbench.fbx').stat().st_size>10000000,'FBX export empty'
d.update(materials=[m.name for m in o.data.materials],slot_zero_runtime_surface='WSBench_BenchWood',triangulated=True,game_blend_textures_packed=True,vertices=len(o.data.vertices))
p.write_text(json.dumps(d,indent=2),encoding='utf-8');print('FINALIZE_SUCCESS',d['triangles'],len(d['materials']))
