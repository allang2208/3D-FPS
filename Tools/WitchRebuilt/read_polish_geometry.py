import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out={}
for label,file in [('old',ROOT.parent/'WitchMeshy20260919/Authoring/CleanRobeV06/Witch_CleanRobeV06.blend'),('rest',ROOT/'Authoring/WitchRebuilt_Master.blend'),('idle',ROOT/'Authoring/WitchRebuilt_Idle.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(file));s=bpy.context.scene;s.frame_set(1);dg=bpy.context.evaluated_depsgraph_get();r=next(o for o in s.objects if o.type=='ARMATURE')
    out[label]={'rig_scale':list(r.scale),'objects':{}}
    for name in ['Witch_UpperRobe','Witch_OriginalRobe_Render','WitchRebuilt_CompleteBody']:
        o=s.objects.get(name)
        if not o:continue
        ev=o.evaluated_get(dg);me=ev.to_mesh();pts=[ev.matrix_world@v.co for v in me.vertices]
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
        out[label]['objects'][name]={'faces':len(o.data.polygons),'area':sum(f.calc_area() for f in bm.faces),
            'bounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],
            'matrix':[list(row) for row in o.matrix_world],'modifiers':[m.type for m in o.modifiers],
            'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
            'shape_keys':[(k.name,k.value) for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],
            'largest_pose_scales':sorted([(b.name,max(b.matrix.to_scale())) for b in r.pose.bones],key=lambda x:-x[1])[:8]}
        ev.to_mesh_clear();bm.free()
    if label=='rest':out[label]['bones']={n:list((r.matrix_world@r.data.bones[n].matrix_local).translation) for n in ['pelvis','spine_01','spine_03','spine_05','clavicle_r','upperarm_r','lowerarm_r','hand_r','middle_01_r']}
(ROOT/'Polish20260922/geometry_inputs.json').write_text(json.dumps(out,indent=2))
