import bpy,json,math
from pathlib import Path
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\ArmsReplacement')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'SK_ArmsReplacement_Source.blend'))
rig=bpy.data.objects['SK_AKM_Viewmodel'];mesh=bpy.data.objects['SK_ArmsReplacement_WRAD']
missing=[g.name for g in mesh.vertex_groups if g.name not in rig.data.bones]
bad_weights=[]
for v in mesh.data.vertices:
    total=sum(g.weight for g in v.groups)
    if abs(total-1)>.002:bad_weights.append([v.index,total])
clips={}
for a in bpy.data.actions:
    if not a.name.startswith('AKM_'):continue
    rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    mn=[float('inf')]*3;mx=[float('-inf')]*3;nf=0
    for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
        bpy.context.scene.frame_set(f);bpy.context.view_layer.update();ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
        for v in em.vertices:
            p=ev.matrix_world@v.co
            if not all(math.isfinite(c) for c in p):raise RuntimeError(f'Nonfinite {a.name}/{f}')
            for i in range(3):mn[i]=min(mn[i],p[i]);mx[i]=max(mx[i],p[i])
        ev.to_mesh_clear();nf+=1
    clips[a.name]={'frames_sampled':nf,'min_m':mn,'max_m':mx}
assert not missing and not bad_weights
report={'status':'PASS','missing_bones':missing,'bad_weight_sums':bad_weights,'clips':clips,'meaning':'Every-frame finite vertex/weight validation only. Visual previews inspect three source poses; runtime hand/weapon fit is a separate check.'}
(OUT/'arms_replacement_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
rig.animation_data_clear();rig.data.pose_position='REST'
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_ArmsReplacement.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Z',axis_up='Y',apply_scale_options='FBX_SCALE_NONE',use_armature_deform_only=False)
print('ARMS_REPLACEMENT_VALIDATION_PASS',len(clips),sum(c['frames_sampled'] for c in clips.values()))
