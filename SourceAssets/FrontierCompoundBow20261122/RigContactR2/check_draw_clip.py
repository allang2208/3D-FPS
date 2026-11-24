"""Test the in-engine draw clip samples against the revised game meshes in bow space."""
from pathlib import Path
import bpy,sys,os,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
s=Path(__file__).resolve().parent
sys.path.insert(0,str(s))
from wheel_geometry import BRACE,DRAW,SEAT
b=Path(os.environ['FRONTIER_BATCH'])
samples=json.loads((b/'draw-clip-contacts.json').read_bytes())
bpy.ops.wm.open_mainfile(filepath=str(s/'FrontierCompoundBow_R2.blend'))
sc=bpy.context.scene
def from_ue(v):return Vector((v[0],-v[1],v[2]))
result=[]
for sample in samples:
    n=from_ue(sample['nock']);q=min(1.,max(0.,(n-BRACE).dot(DRAW-BRACE)/(DRAW-BRACE).length_squared))
    frame=1.+24.*q;f=int(frame);sc.frame_set(f,subframe=frame-f)
    dep=bpy.context.evaluated_depsgraph_get()
    trees={k:BVHTree.FromObject(sc.objects[k].evaluated_get(dep),dep) for k in (
        'UpperCam','LowerCam','Riser','UpperLimb','LowerLimb','ControlCable1','ControlCable2','Rest','Grip')}
    hits=[]
    def ray(a,b,start,stop,own=None):
        direction=(b-a).normalized();end=(b-a).length-stop
        for k,tree in trees.items():
            pos=start
            while pos<end:
                h=tree.ray_cast(a+pos*direction,direction,end-pos)[0]
                if h is None:break
                d=(h-a).length
                if k!=own or d>=1.75:hits.append([k,d])
                pos=d+.005
    for side in ('upper','lower'):ray(from_ue(sample[side]),n,.02,.12,side.title()+'Cam')
    ray(n,n+(SEAT-n).normalized()*76,.3,.3)
    result.append({'time':sample['time'],'draw':q,'hits':hits})
(b/'draw-clip-clearance.json').write_text(json.dumps(result,indent=1),encoding='utf8')
if any(x['hits'] for x in result):raise RuntimeError('Unexpected path crossing')
