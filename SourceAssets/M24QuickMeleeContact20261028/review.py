from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'inspect.py').read_text()
injection='''
original_pose=pose
edited={family:[{n:Matrix(m) for n,m in row.items()} for row in rows] for family,rows in json.loads((O/'final_poses.json').read_text()).items()}
def pose(role,t,family='base',layer=True):
 if role!='quick_melee' or not layer:return original_pose(role,t,family,layer)
 rows=edited[family];f=max(0,min(108,t*120));i=min(int(f),107);w=f-i;out={};local={}
 for n in names:
  a=rows[i][parents[n]].inverted()@rows[i][n] if parents[n] else rows[i][n];b=rows[i+1][parents[n]].inverted()@rows[i+1][n] if parents[n] else rows[i+1][n]
  p,q,sc=a.decompose();pp,qq,ss=b.decompose();local[n]=Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w));out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
 return out,local
'''
code=code.replace("folder=O/'Before'",injection+"\nfolder=O/'After'").replace("O/'before_geometry.json'","O/'after_geometry.json'")
exec(compile(code,'review','exec'))
