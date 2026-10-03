"""Closed-hand authoring in cumulative palm directions (Blender metres)."""
import math
from mathutils import Matrix, Vector, Quaternion


def frame(forward, normal):
    x=forward.normalized(); z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,x.cross(z),z)).transposed()


def closed_locals(rest, parents, profile):
    origin=rest['hand_l'].translation
    normal=(rest['pinky_01_l'].translation-origin).cross(rest['index_01_l'].translation-origin).normalized()
    palm=frame(rest['middle_01_l'].translation-origin,normal)
    pose={n:m.copy() for n,m in rest.items()}; result={}
    for n in rest:
        if not n.endswith('_l') or n.split('_')[0] not in profile: continue
        parent=parents[n]; local=rest[parent].inverted()@rest[n]
        m=pose[parent]@local; parts=n.split('_')
        if len(parts)==3 and parts[1].isdigit():
            k=int(parts[1])-1; digit=profile[parts[0]]
            nxt=f'{parts[0]}_{k+2:02d}_l'
            rd=rest[nxt].translation-rest[n].translation if nxt in rest else rest[n].to_quaternion()@(rest[parent].to_quaternion().inverted()@(rest[n].translation-rest[parent].translation))
            spread=digit['spread'][k] if isinstance(digit['spread'],list) else digit['spread']
            angle=math.radians(spread)
            neutral=frame(palm@Vector((math.cos(angle),math.sin(angle),0)),normal)
            target=Quaternion(neutral.col[1],math.radians(digit['flex'][k])).to_matrix()@neutral
            q=(target@frame(rd,normal).inverted()@rest[n].to_3x3()).to_quaternion()
            m=Matrix.LocRotScale(m.translation,q,Vector((1,1,1)))
        pose[n]=m; result[n]=(pose[parent].inverted()@m).to_quaternion()
    return result
