import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];results=[]
for ext in ('fbx','glb'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    path=ROOT/'exports'/('TreasureChest_v3.'+ext)
    if ext=='fbx':bpy.ops.import_scene.fbx(filepath=str(path),anim_offset=0)
    else:bpy.ops.import_scene.gltf(filepath=str(path))
    s=bpy.context.scene;s.frame_set(1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();objs=[o for o in s.objects if o.type=='MESH' and o.data.polygons and len(o.data.materials)>0];pts=[]
    for o in objs:pts.extend(o.evaluated_get(dg).matrix_world@Vector(p) for p in o.evaluated_get(dg).bound_box)
    arms=[o for o in s.objects if o.type=='ARMATURE']
    results.append({'file':path.name,'meshes':len(objs),'material_slots':[[m.name for m in o.data.materials] for o in objs],'unit_scale':s.unit_settings.scale_length,'dimensions_scene_units':[max(p[i] for p in pts)-min(p[i] for p in pts) for i in range(3)],'armatures':[{'name':a.name,'bones':[b.name for b in a.data.bones],'actions':a.animation_data.action.name if a.animation_data and a.animation_data.action else None} for a in arms],'actions':[{'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions]})
    s.frame_set(31);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();openpts=[]
    for o in objs:openpts.extend(o.evaluated_get(dg).matrix_world@Vector(p) for p in o.evaluated_get(dg).bound_box)
    results[-1]['open_frame31_bounds_m']={'min':[min(p[i] for p in openpts) for i in range(3)],'max':[max(p[i] for p in openpts) for i in range(3)]}
(ROOT/'reports/roundtrip.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
