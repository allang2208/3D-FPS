import bpy,json,math
from pathlib import Path
root=Path(__file__).resolve().parent
reports={}
for ext,file in [('glb','HandBrain_Animated.glb'),('fbx','SK_HandBrain_Animated.fbx')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    if ext=='glb':bpy.ops.import_scene.gltf(filepath=str(root/'delivery'/file))
    else:bpy.ops.import_scene.fbx(filepath=str(root/'delivery'/file))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    # glTF importer creates a 42-vertex bone display helper. Validate asset meshes.
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
    clips={}
    for action in bpy.data.actions:
        name=next((n for n in ['Idle','Move','Attack_Slam'] if n in action.name),None)
        if not name:continue
        rig.animation_data_create();rig.animation_data.action=action
        if action.slots:rig.animation_data.action_slot=action.slots[0]
        first,last=action.frame_range
        snapshots=[]
        for frame in [first,last]:
            bpy.context.scene.frame_set(round(frame));bpy.context.view_layer.update()
            snapshots.append({p.name:[v for row in p.matrix for v in row] for p in rig.pose.bones})
        seam=max(abs(a-b) for key in snapshots[0] for a,b in zip(snapshots[0][key],snapshots[1][key]))
        clips[name]={'duration_s':float((last-first)/30),'frame_range':[float(first),float(last)],'loop_matrix_error':seam if name!='Attack_Slam' else None}
        if name=='Attack_Slam':
            bpy.context.scene.frame_set(round(first+30));bpy.context.view_layer.update()
            arm=next(o for o in meshes if 'AttackArm' in o.name)
            e=arm.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
            clips[name]['impact_lowest_z_m']=min((e.matrix_world@v.co).z for v in m.vertices);e.to_mesh_clear()
    reports[ext]={'clips':clips,'mesh_count':len(meshes),'bone_count':len(rig.data.bones),'vertices':sum(len(o.data.vertices) for o in meshes),'triangles':sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons),'unweighted':sum(not v.groups for o in meshes for v in o.data.vertices),'max_weights':max(len(v.groups) for o in meshes for v in o.data.vertices),'finite':all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co),'textures':[{'name':i.name,'size':list(i.size),'loaded':i.has_data} for i in bpy.data.images]}
    (root/'delivery_validation.json').write_text(json.dumps(reports,indent=2))
    print(ext,'weights',reports[ext]['unweighted'],reports[ext]['max_weights'],reports[ext]['finite'],flush=True)
    assert set(clips)=={'Idle','Move','Attack_Slam'},clips
    for n,d in [('Idle',2),('Move',1),('Attack_Slam',2)]:assert abs(clips[n]['duration_s']-d)<.002
    for n in ['Idle','Move']:assert clips[n]['loop_matrix_error']<.0001
    assert reports[ext]['unweighted']==0 and reports[ext]['max_weights']<=4 and reports[ext]['finite']
(root/'delivery_validation.json').write_text(json.dumps(reports,indent=2))
print('DELIVERY_VALIDATED',json.dumps({k:{'clips':list(v['clips']),'meshes':v['mesh_count'],'bones':v['bone_count']} for k,v in reports.items()}))
