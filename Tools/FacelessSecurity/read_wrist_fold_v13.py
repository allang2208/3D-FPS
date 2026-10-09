import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
B=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
bpy.ops.wm.open_mainfile(filepath=str(B/'V13/Authoring/FacelessSecurity_V13.blend'))
r=bpy.data.objects['root'];r.animation_data_create();o=bpy.data.objects['Security_OutfitBody'];c=bpy.data.objects['Security_Cuff_l'];s=bpy.context.scene
with bpy.data.libraries.load(str(B/'V12/Authoring/FacelessSecurity_States_V12.blend'),link=False) as (a,b):b.actions=['Security_V12_prone_get_up']
r.animation_data.action=b.actions[0];r.animation_data.action_slot=b.actions[0].slots[0];s.frame_set(87);bpy.context.view_layer.update()
def ep(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=[ev.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear();return p
sp=ep(o);cp=ep(c);w=r.matrix_world@r.data.bones['hand_l'].head_local;e=r.matrix_world@r.data.bones['lowerarm_l'].head_local;axis=(w-e).normalized()
def row(obj,i):
    p=obj.matrix_world@obj.data.vertices[i].co
    return {'id':i,'rest':list(p),'q':(p-w).dot(axis),'weights':{obj.vertex_groups[g.group].name:g.weight for g in obj.data.vertices[i].groups}}
idx=4132;report={'skin':row(o,idx),'posed_skin':list(sp[idx]),'rings':[]}
for ring in range(12):
    center=sum(cp[ring*64:(ring+1)*64],Vector())/64
    report['rings'].append({'center':list(center),'first':row(c,ring*64),'mean_radius':sum((p-center).length for p in cp[ring*64:(ring+1)*64])/64,
                            'skin_center_distance':(sp[idx]-center).length})
c.data.calc_loop_triangles();t=[tuple(f.vertices) for f in c.data.loop_triangles if max(f.vertices)<768];tree=BVHTree.FromPolygons(cp,t,all_triangles=True);h=tree.find_nearest(sp[idx])
report['nearest']={'p':list(h[0]),'n':list(h[1]),'tri':t[h[2]],'rest':[row(c,i) for i in t[h[2]]],'signed':(sp[idx]-h[0]).dot(h[1])}
(B/'V13/Diagnosis/wrist_fold.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
