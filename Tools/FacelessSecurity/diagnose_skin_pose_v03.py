"""Evaluate the actual saved UE pose against its exported skin bind data."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V03/Diagnosis')
j=json.loads((ROOT/'ue_limbs_before.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(ROOT/'SK_Security_Before.fbx'),use_anim=False)
reflect=Matrix(((1,0,0),(0,-1,0),(0,0,1)))
def convert(t):
    x,y,z,w=t['q'];q=(reflect@Quaternion((w,x,y,z)).to_matrix()@reflect).to_quaternion()
    return Matrix.LocRotScale(reflect@Vector(t['p'])*.01,q,Vector(t['s']))
ref={n:convert(t) for n,t in j['reference'].items()}
report={}
for role in ['V02idle','V02attack']:
    pose={n:convert(t) for n,t in j['poses'][role][0]['world'].items()}
    delta={n:pose[n]@ref[n].inverted() for n in ref};row={}
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        groups={g.index:g.name for g in o.vertex_groups}
        for side in ['l','r']:
            points=[]
            for v in o.data.vertices:
                ws={groups[g.group]:g.weight for g in v.groups}
                hand=sum(w for n,w in ws.items() if n.endswith('_'+side) and n.startswith(('hand','thumb','index','middle','ring','pinky')))
                if hand<.8:continue
                points.append(sum((delta[n]@(o.matrix_world@v.co)*w for n,w in ws.items()),Vector()))
            row[side]={'vertices':len(points),'bounds':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]}
    report[role]=row
(ROOT/'saved_ue_skin_pose.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
