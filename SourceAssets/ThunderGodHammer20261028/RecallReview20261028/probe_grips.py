import ast,math,json
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).resolve().parent;src=P.parent/'ThunderThrowV1/author_motion.py';tree=ast.parse(src.read_text());nodes=[]
for n in tree.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='charge' for t in n.targets):break
    nodes.append(n)
s={'__file__':str(src)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(src),'exec'),s)
idle,rest,grips=[s[k] for k in ['idle','rest','grips']];rows={}
for label,wpn in [('top',s['top']),('front',s['front']),('receive',s['weapon']((.19,.43,-.13),(0,-.10,.995)))]:
    rows[label]={}
    for side in ('l','r'):
        out=[]
        for deg in range(-180,181,15):
            hand=wpn@Quaternion((0,0,1),math.radians(deg)).to_matrix().to_4x4()@grips[side]
            shoulder=idle['upperarm_'+side].translation;v=hand.translation-shoulder;d=v.length;axis=v.normalized()
            upper=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length;fore=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
            center=shoulder+axis*((upper**2-fore**2+d*d)/(2*d));radius=math.sqrt(max(0,upper**2-(center-shoulder).length_squared))
            neutral=hand.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
            ideal=hand.translation-neutral*fore-center;guide=(ideal-axis*ideal.dot(axis)).normalized();elbow=center+guide*radius
            angle=math.degrees(neutral.angle((hand.translation-elbow).normalized()))
            out.append({'roll':deg,'angle':round(angle,1),'elbow':[round(x,3) for x in elbow]})
        rows[label][side]=out
(P/'grip-probe.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
