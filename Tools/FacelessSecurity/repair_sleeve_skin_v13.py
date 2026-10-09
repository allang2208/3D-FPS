"""Long-sleeve coverage and a common native wrist binding, retaining full anatomy."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');ROOT=BASE/'V13'
for d in ['Authoring','Delivery','Diagnosis','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V11/Authoring/FacelessSecurity_V11.blend'))
rig=bpy.data.objects['root'];rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
body=bpy.data.objects['Security_CompleteBody'];display=bpy.data.objects['Security_OutfitBody']
shirt=bpy.data.objects['Security_Uniform_SewnNeck_V11']
heads={n:rig.matrix_world@rig.data.bones[n].head_local for n in ['lowerarm_l','lowerarm_r','hand_l','hand_r']}
def arm(p):
    side='l' if p.x>0 else 'r';w=heads['hand_'+side];axis=(w-heads['lowerarm_'+side]).normalized()
    return side,(p-w).dot(axis),axis
def ease(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def weights(o,v):return {o.vertex_groups[g.group].name:g.weight for g in v.groups}
def set_weights(o,v,row):
    for g in o.vertex_groups:g.remove([v.index])
    total=sum(row.values())
    for n,w in row.items():
        if w<1e-7:continue
        group=o.vertex_groups.get(n) or o.vertex_groups.new(name=n);group.add([v.index],w/total,'REPLACE')
report={'revision':'V13','source':'V11','cause':'Display skin retained the covered elbow/forearm while the continuous sleeve used a different weight field',
        'complete_body_preserved':True,'motions_preserved':'V06 idle/walk, V10 attack, V12 reactions',
        'game_tested':False,'rendered':False,'coverage':{},'wrist_binding':{}}
# Runtime outfit coverage follows the real cuff axis. Keep 48 mm of forearm
# inside the 68 mm cuff, not the whole elbow. The full body is never trimmed.
bm=bmesh.new();bm.from_mesh(display.data)
removed=[]
for f in bm.faces:
    p=f.calc_center_median()
    if abs(p.x)>.27 and p.z>.60:
        side,q,axis=arm(p)
        if q<-.048:removed.append(f)
report['coverage']['removed_covered_faces']=len(removed)
bmesh.ops.delete(bm,geom=removed,context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(display.data);bm.free();display.data.update()
report['coverage'].update(retained_wrist_overlap_mm=46,cut_plane_from_wrist_mm=-48,
                         display_vertices=len(display.data.vertices),complete_vertices=len(body.data.vertices))
# A tailored cuff belongs to the forearm. The old cuff followed the hand bend
# and folded back into its own wrist overlap during the attack/get-up poses.
# Keep the whole cuff and covered skin forearm-bound. The hand blend occurs
# beyond the cuff opening, with the original palm/finger weights retained.
for o in [display,shirt,bpy.data.objects['Security_Cuff_l'],bpy.data.objects['Security_Cuff_r']]:
    changed=0
    count=len(o.data.vertices) if o==display else len(o.data.vertices)//2
    for v in list(o.data.vertices)[:count]:
        p=o.matrix_world@v.co
        if abs(p.x)<.45 or p.z<.70:continue
        side,q,axis=arm(p)
        if q<-.12 or (q>=.025 if o==display else q>=0):continue
        old=weights(o,v);amount=ease(-.12,-.085,q)
        if o==display:amount*=1-ease(-.002,.025,q)
        target={'lowerarm_'+side:1.}
        row={n:w*(1-amount) for n,w in old.items()}
        for n,w in target.items():row[n]=row.get(n,0)+amount*w
        set_weights(o,v,row);changed+=1
        if o!=display:set_weights(o,o.data.vertices[v.index+count],row);changed+=1
    report['wrist_binding'][o.name]=changed
body.hide_render=True;body.hide_set(True);display.hide_render=False;display.hide_set(False)
report['wrist_binding_method']='Forearm-only cuff and covered wrist; transition to original palm/finger weights beyond cuff opening'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V13.blend'))
(ROOT/'sleeve_recipe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_V13_SLEEVE_AUTHORED '+json.dumps(report),flush=True)
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V13')
exec(compile(export,'security_v13_export','exec'),{})
