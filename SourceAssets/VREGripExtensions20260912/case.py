from pathlib import Path
import json
O=Path(__file__).parent;S=O.parent;OUT=O/'Final'
DONOR=S/'MannyGraspDonor20260912'
FAMILIES=[(w,v) for w in ['m4','akm'] for v in ['canted','prism']]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def source_dir(w,v):
 return S/'VerticalGripErgonomic20260911/prism' if (w,v)==('m4','prism') else S/'CantedGripMigration20260911'/w/v
def prefix(w,v):return f'A_{w.upper()}_{v.title() if w=="m4" else v}_'
def metadata(w,v):return read(source_dir(w,v)/('animation_build.json' if w=='m4' else 'build.json'))
def grip_fit(w,v):
 return read(source_dir(w,v)/'fit_final.json') if w=='m4' else read(S/'CantedGripMigration20260911/akm/fits.json')[v]
def asset_dir(w,v,baseline=False):
 if baseline:
  return ('/Game/Weapons/M4CantedErgonomic' if v=='canted' else '/Game/Weapons/M4VerticalGripErgonomic/Prism') if w=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/'+v
 return '/Game/Weapons/M4VREGripExtensions/'+v.title() if w=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/GripVREExtensions/'+v
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def weights(w,clip,f,end):
 if 'reload' not in clip:return 1.,1.
 if w=='m4':
  arm=1-smooth((f-(20 if clip.startswith('drum') else 9))/(8 if clip.startswith('drum') else 7))+smooth((f-(end-24))/8)
  u=max(0,min(1,f/9)) if f<end/2 else 1-max(0,min(1,(f-(end-12))/12))
 else:
  start=380 if 'empty' in clip else 270;finish=start+60
  arm=1-smooth((f-18)/24)+smooth((f-start)/40)
  u=max(0,min(1,f/18)) if f<end/2 else 1-max(0,min(1,(f-(finish-24))/24))
 return arm,arm*(1-smooth(u))
def contact_interval(w,clip,end):
 if 'reload' not in clip:return None
 return [28 if clip.startswith('drum') else 16,end-24] if w=='m4' else [42,380 if 'empty' in clip else 270]
