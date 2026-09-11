from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'ReferenceWorkflow/build_akm.py').read_text().replace('O=Path(__file__).parent','O=ROOT').replace('from audit_m4 import support,smooth','from front_pose import solve_arm\ndef smooth(x):\n x=max(0,min(1,x));return x*x*(3-2*x)')
a,b=source.index('def arm('),source.index('def render(')
source=source[:a]+'def arm(p,rest,H,w,delta):return solve_arm(p,rest,H,None,w)\n\n'+source[b:]
source=source.replace("h,digits=opening(u);H=", "h,digits=opening(u);digits['thumb_01_l']=Quaternion(fit.get('thumb_root_delta',[1,0,0,0]))@digits['thumb_01_l'];H=")
exec(compile(source,str(ROOT/'ReferenceWorkflow/build_akm.py'),'exec'))
