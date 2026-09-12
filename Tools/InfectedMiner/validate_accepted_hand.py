"""Verify the accepted skin/bind and grip survived the motion replacement."""
import bpy,json,hashlib,struct,sys
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912')
def snapshot():
    r=bpy.data.objects['MinerRig'];h=hashlib.sha256()
    for b in r.data.bones:
        h.update(b.name.encode());h.update(struct.pack('16f',*(x for row in b.matrix_local for x in row)))
    for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
        if o.type!='MESH' or not any(m.type=='ARMATURE' and m.object==r for m in o.modifiers):continue
        h.update(o.name.encode())
        for v in o.data.vertices:
            h.update(struct.pack('3f',*v.co))
            for g in v.groups:h.update(struct.pack('if',g.group,g.weight))
        for p in o.data.polygons:h.update(struct.pack(str(len(p.vertices))+'I',*p.vertices))
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(R/'Review/Hand_UserAccepted_20260912/InfectedMiner_Editable.blend'))
accepted=snapshot();r=bpy.data.objects['MinerRig'];a=bpy.data.actions['A_Miner_Idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(1)
grip={b.name:b.matrix_basis.copy() for b in r.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
source=R/('Candidates/CMU02_07' if '--cmu' in sys.argv else 'Delivery')
bpy.ops.wm.open_mainfile(filepath=str(source/'InfectedMiner_Editable.blend'))
current=snapshot();assert current==accepted,(accepted,current)
r=bpy.data.objects['MinerRig'];a=bpy.data.actions['A_Miner_Attack'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];error=0
for f in range(1,round(a.frame_range[1])+1):
    bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
    for n,m in grip.items():error=max(error,max(abs(m[i][j]-r.pose.bones[n].matrix_basis[i][j]) for i in range(4) for j in range(4)))
assert error<1e-5,error
fbxhash=hashlib.sha256((R/'Delivery/SK_InfectedMiner.fbx').read_bytes()).hexdigest()
assert fbxhash=='7d232fdfa032c5c2c3aba24b8e5813c124c1b5f3864c17dc134fec6f41e60aa2'
report={'accepted_mesh_weights_bind_unchanged':True,'geometry_bind_hash':current,'accepted_mesh_fbx_sha256':fbxhash,'attack_samples':round(a.frame_range[1]),'finger_basis_max_error':error}
out=R/('Previews/FBX_CMU' if '--cmu' in sys.argv else 'Previews/FBX');out.mkdir(parents=True,exist_ok=True)
(out/'accepted-hand-validation.json').write_text(json.dumps(report,indent=2));print('ACCEPTED_HAND_LOCK_VERIFIED '+json.dumps(report))
