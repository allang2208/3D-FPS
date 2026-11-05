"""M24 local-front grip authoring, using the accepted SVD finger arc as guidance."""
from pathlib import Path
import bpy, json, gzip, math, copy, struct, hashlib
from mathutils import Matrix, Quaternion, Vector
TASKOUT=Path(__file__).resolve().parent
LOCAL_TASK_DIR=TASKOUT
svd_source=TASKOUT.parent/'SVDThumbUp20260923/SVD_base_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(svd_source),use_scripts=False)
svd_rig=bpy.data.objects['SK_M4_Infima'];svd_action=bpy.data.actions['A_SVD_reload']
svd_rig.animation_data.action=svd_action;svd_rig.animation_data.action_slot=svd_action.slots[0]
bpy.context.scene.frame_set(120);bpy.context.view_layer.update()
svd_local={b.name:(svd_rig.pose.bones[b.parent.name].matrix.inverted()@b.matrix).copy() for b in svd_rig.pose.bones if b.parent}
__file__=str(TASKOUT.parent/'M24SurfaceGrip20261103/fit.py')
exec(compile(Path(__file__).read_text().split("if __name__=='__main__':")[0],'native surface authoring helpers','exec'))
TASKOUT=LOCAL_TASK_DIR
D['profiles']=json.load(gzip.open(TASKOUT/'input_profiles.json.gz','rt'))
if (TASKOUT/'input_clips.json.gz').exists():
    current_clips=json.load(gzip.open(TASKOUT/'input_clips.json.gz','rt'))
    D['clips'].update(current_clips)
donors=json.load(gzip.open(TASKOUT.parent/'M24ReloadDonor20261101/donors.json.gz','rt'))
digits=[n for n in names if n.endswith('_l') and n.startswith(('index_','middle_','ring_','pinky_')) and 'metacarpal' not in n]
def quat(v):return Quaternion((v[6],*v[3:6]))
T={n:quat(v) for n,v in donors['m24_native_rest'].items()};S={n:quat(v) for n,v in donors['rest']['m4'].items()}
alignment=T['hand_l']@S['hand_l'].inverted()
basis_map={n:S[n].inverted()@alignment.inverted()@T[n] for n in T if n in S}
mapped={}
for n in digits:
    ue_q=(K@svd_local[n]@K).to_quaternion()
    q=basis_map[parents[n]].inverted()@ue_q@basis_map[n]
    mapped[n]=(K@q.to_matrix().to_4x4()@K).to_quaternion()

# Keep native metacarpal spacing and the accepted thumb. Blend only finger curl,
# not the donor palm/arm or a whole-hand rigid transform.
anchors={}
for family in ('base','mag10'):
    anchors[family]={}
    for stage,f in [('old',18),('new',38)]:
        row,local=compose(entry(family,'reload'),f/30)
        qs={}
        for n in digits:
            amount=.10 if '_01_' in n else .25
            qs[n]=local[n].to_quaternion().slerp(mapped[n],amount)
        anchors[family][stage]={'relative':row['WPN_Magazine'].inverted()@row['hand_l'],'digits':qs}

class LocalGripFrame(SurfaceFrame):
    def __init__(self,family,f,stage,role='reload'):
        super().__init__(family,f,role)
        a=anchors['mag10' if 'mag10' in family else 'base'][stage]
        self.seed['hand_l']=self.row['WPN_Magazine']@a['relative']
        for n in names:
            if n!='hand_l' and n in handbones:
                p,q,sc=self.local[n].decompose()
                self.seed[n]=self.seed[parents[n]]@Matrix.LocRotScale(p,a['digits'].get(n,q),sc)
        self.H=self.seed['hand_l'].translation
        self.basis=self.row['WPN_Magazine'].to_quaternion().to_matrix()
        vs,fs=self.geo['magazine'];forward=(self.row['WPN_FrontSight'].translation-self.row['WPN_RearSight'].translation).normalized()
        values=vs@np.array(forward);center=(values.max()+values.min())*.5
        frontfaces=[face for face in fs if float(values[list(face)].mean())>=center]
        self.front=BVHTree.FromPolygons(vs.tolist(),frontfaces,all_triangles=True)
    def features(self,p):
        residual=[];terms=[];info={}
        for d,target,w in [('index',1.5,1.),('middle',2.5,.8),('ring',6.,.25),('pinky',10.,.12)]:
            rows=[]
            for i in PARTS[d]:
                pos=Vector(p[i]);near,no,_,dist=self.front.find_nearest(pos)
                rows.append((dist,i,np.array((pos-near).normalized())))
            rows.sort(key=lambda v:v[0]);rows=rows[:16]
            info[d]=float(np.mean([v[0] for v in rows])*1000)
            for dist,i,n in rows:
                residual.append((dist*1000-target)*w/4);terms.append((i,n,w/4))
        return np.array(residual),terms,info

def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
