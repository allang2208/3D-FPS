"""Quantify the requested throw/garment inspection from the authoring sources."""
import bpy,bmesh,json,math
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Polish20260922'
data={}
for label,path in [('before',OUT/'Before/WitchRebuilt_ThrowPoisonBottle.blend'),('after',ROOT/'Authoring/WitchRebuilt_ThrowPoisonBottle.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE')
    rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
    lengths=[(rest[b].translation-rest[a].translation).length for a,b in [('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]]
    errors=[];samples=[];segment_lengths=[]
    for frame in range(s.frame_start,s.frame_end+1):
        s.frame_set(frame);p={n:(r.matrix_world@r.pose.bones[n].matrix).translation for n in ['upperarm_r','lowerarm_r','hand_r']}
        errors.append(max(abs((p[b]-p[a]).length-lengths[i]) for i,(a,b) in enumerate([('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')])))
        segment_lengths.append([(p[b]-p[a]).length for a,b in [('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]])
        samples.append(p['hand_r'].copy())
    data[label]={'max_bone_length_error_cm':max(errors)*100,'frames':s.frame_end-s.frame_start+1,'fps':s.render.fps,
        'end_to_start_hand_distance_cm':(samples[-1]-samples[0]).length*100,
        'max_bone_length_variation_within_clip_cm':max(max(v[j] for v in segment_lengths)-min(v[j] for v in segment_lengths) for j in (0,1))*100}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
for name in ['Witch_UpperRobe','Witch_OriginalRobe_Render']:
    o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    todo=set(bm.verts);count=0
    while todo:
        stack=[todo.pop()];count+=1
        while stack:
            for e in stack.pop().link_edges:
                for v in e.verts:
                    if v in todo:todo.remove(v);stack.append(v)
    data[name]={'connected_components':count,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons)};bm.free()
data['scope']='Authoring geometry and bone trajectories; no gameplay or Chaos simulation test'
(OUT/'inspection_result.json').write_text(json.dumps(data,indent=2));print(json.dumps(data))
