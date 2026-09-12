import bpy,json,sys,runpy
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent
for closure in [.90,.80]:
 D=O/'Opening'/str(closure);D.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Donor_Preview.blend'));r=bpy.data.objects['SK_M4_Infima'];fit=json.loads((O/'donor_fit.json').read_text())
 for n,m in fit['basis'].items():
  loc,q,scale=Matrix(m).decompose();q=Quaternion().slerp(q,closure);r.pose.bones[n].matrix_basis=Matrix.LocRotScale(loc,q,scale)
  fit['basis'][n]=[list(x) for x in r.pose.bones[n].matrix_basis]
 fit['donor_closure']=closure;bpy.context.view_layer.update()
 (D/'donor_fit.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(D/'M4_Donor_Preview.blend'))
 sys.argv=['fit_rigid.py','--case',str(D)];runpy.run_path(str(O/'fit_rigid.py'),run_name='__main__')
