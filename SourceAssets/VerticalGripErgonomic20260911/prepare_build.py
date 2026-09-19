import json,shutil
from pathlib import Path
O=Path(__file__).parent;SRC=O.parent
source=(SRC/'VerticalGripRaised20260911/build_family.py').read_text()
source=source.replace("fit['basis']=json.loads((O.parent/'common_hand_pose.json').read_text())\nfit['basis'].update(json.loads((O/'contact_overrides.json').read_text()))", "sys.path.insert(0,str(O.parent))\nfrom fit_pose import solve_arm")
start=source.index('   support_offset=');end=source.index('   p[hn]=H',start)+len('   p[hn]=H')
source=source[:start]+"   grip=old['WPN_root']@Matrix(fit['grip_in_root'])\n   solve_arm(p,rest,H,grip,w)"+source[end:]
source=source.replace("local=Matrix(fit['grip_matrix']).inverted()@ob.matrix_basis.copy();", "local=Matrix(fit['attachment_local'][ob.name]);")
source=source.replace("retreat=smooth(u);opening=", "retreat=smooth((u-fit.get('retreat_start',0))/(1-fit.get('retreat_start',0)));opening=")
(O/'build_family.py').write_text(source)
for variant,title,oldpath in [('vertical','Vertical',SRC/'VerticalGripRaised20260911/vertical'),('prism','Prism',SRC/'PrismGripContact20260911/prism')]:
 d=O/variant;profile=json.loads((oldpath/'profile.json').read_text());profile={k:profile[k] for k in ['family','variant','animation_prefix','mesh_prefix','source']};profile['fitted_mesh']='FinalFit.blend';profile['arm_profile']='../arm_profile.json';profile['revision']='ergonomic-photo-reference';(d/'profile.json').write_text(json.dumps(profile,indent=2))
 (d/'build_animation.py').write_text("from pathlib import Path\nexec(compile((Path(__file__).parent.parent/'build_family.py').read_text(),str(Path(__file__).parent.parent/'build_family.py'),'exec'))\n")
 for name in ['validate_source.py','check_geometry.py','review_animation.py','run_validation.ps1','assemble_editable.py']:
  shutil.copy2(oldpath/name,d/name)
 if not (d/'ReferenceWorkflow').exists():shutil.copytree(oldpath/'ReferenceWorkflow',d/'ReferenceWorkflow')
 text=(oldpath/'import_assets.py').read_text();a=text.index("DEST='");b=text.index("'",a+6);text=text[:a]+"DEST='/Game/Weapons/M4VerticalGripErgonomic/"+title+"'"+text[b+1:];(d/'import_assets.py').write_text(text)
