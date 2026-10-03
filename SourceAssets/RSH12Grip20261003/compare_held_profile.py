"""Compare absolute hand targets to the profile actually authored for UE."""
import bpy,json,sys,ast,math
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O));from pose_geometry import *
rig,D,latest,meta=load();current=json.loads((B/'Single/profile.json').read_text())
before=O/'BeforeAuthored/Integration/Single';original=json.loads((before/'profile.json').read_text());oldmeta=json.loads((before/'authoring.json').read_text())
names=list(rig.data.bones.keys());tree=ast.parse((SA/'author_single_action.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='arm_at');scope=dict(names=names,Matrix=Matrix,Vector=Vector,Quaternion=Quaternion,math=math)
exec(compile(ast.Module(body=[node],type_ignores=[]),'<hand_ik>','exec'),scope)
for kind in ('idle','aim'):
    old=source_pose(rig,D,original,kind);p={n:m.copy() for n,m in old.items()};root=old['WPN_root']@Matrix(oldmeta['alignment']);contract=json.loads((O/('hand_contact_single_'+kind+'.json')).read_text())
    for side,recipe in contract['hands'].items():
        delta=Matrix.Translation(root.to_quaternion()@Vector(recipe['offset_canonical']));scope['arm_at'](p,old,side,delta@old['hand_'+side])
        for n,value in recipe['local_rotation_delta'].items():
            parent=D['parents'][n];local=old[parent].inverted()@old[n];pos,q,scale=local.decompose();p[n]=p[parent]@Matrix.LocRotScale(pos,Quaternion((value[6],*value[3:6]))@q,scale)
    actual=source_pose(rig,D,current,kind)
    differences={n:dict(mm=(p[n].translation-actual[n].translation).length*1000,degrees=math.degrees(p[n].to_quaternion().rotation_difference(actual[n].to_quaternion()).angle)) for n in names if n.startswith(('hand','thumb','index','middle','ring','pinky'))}
    print('HELD_PROFILE_COMPARE',kind,json.dumps({n:v for n,v in differences.items() if v['mm']>.01 or v['degrees']>.01}),flush=True)
