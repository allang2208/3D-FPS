"""Transfer an authored hand pose through rest frames, preserving target joints."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
OLD=O.parent/'VerticalGripFront20260911'

def anatomical_frame(rest,side):
    wrist=rest['hand_'+side].translation
    forward=(rest['middle_01_'+side].translation-wrist).normalized()
    across=rest['index_01_'+side].translation-rest['pinky_01_'+side].translation
    across=(across-forward*across.dot(forward)).normalized()
    return Matrix((across,forward,across.cross(forward))).transposed()

def transfer(r,donor):
    sr={n:Matrix(v['rest']) for n,v in donor['bones'].items()}
    sp={n:Matrix(v['pose']) for n,v in donor['bones'].items()}
    tr={b.name:b.matrix_local.copy() for b in r.data.bones}
    # Anatomical right-to-left reflection. A reflected rotation remains proper
    # after conjugation; mesh scale and bone locations stay untouched.
    A=anatomical_frame(tr,'l')@Matrix.Diagonal((1,1,-1))@anatomical_frame(sr,'r').transposed()
    hand_delta=r.pose.bones['hand_l'].matrix.to_quaternion().to_matrix()@tr['hand_l'].to_quaternion().to_matrix().transposed()
    source_hand_delta=sp['hand_r'].to_quaternion().to_matrix()@sr['hand_r'].to_quaternion().to_matrix().transposed()
    desired={'hand_l':r.pose.bones['hand_l'].matrix.to_quaternion().to_matrix()}
    bases={}
    for b in r.pose.bones:
        n=b.name
        if not (n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))):continue
        source=n[:-1]+'r'
        delta=source_hand_delta.transposed()@sp[source].to_quaternion().to_matrix()@sr[source].to_quaternion().to_matrix().transposed()
        desired[n]=hand_delta@A@delta@A.inverted()@tr[n].to_quaternion().to_matrix()
        localrest=(tr[b.parent.name].inverted()@tr[n]).to_quaternion().to_matrix()
        q=(localrest.transposed()@desired[b.parent.name].transposed()@desired[n]).to_quaternion()
        loc,oldq,scale=b.matrix_basis.decompose()
        b.matrix_basis=Matrix.LocRotScale(loc,q,scale)
        bases[n]=[list(x) for x in b.matrix_basis]
    bpy.context.view_layer.update()
    return bases

if __name__=='__main__':
    donor=json.loads((O/'vre_pose.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'m4/vertical/A_M4_Vertical_idle.blend'))
    s=bpy.context.scene;s.frame_set(0);r=bpy.data.objects['SK_M4_Infima'];r.animation_data.action=None
    fit=json.loads((OLD/'m4/vertical/fit_final.json').read_text())
    fit['basis']=transfer(r,donor)
    (O/'donor_fit.json').write_text(json.dumps(fit,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Donor_Preview.blend'))
    sys.path.insert(0,str(OLD));import inspect_pose
    inspect_pose.O=O;inspect_pose.render(r,fit,'m4_donor')
    print('DONOR_RETARGET_PREVIEW_PASS',flush=True)
