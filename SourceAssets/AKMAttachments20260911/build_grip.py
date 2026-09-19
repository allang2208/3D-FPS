import bpy,math,json,sys,runpy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).parent
variant=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'prism'
O=ROOT/variant;O.mkdir(exist_ok=True);BASE=ROOT
fit=json.loads((ROOT/'fits.json').read_text())[variant]
specs=[(n,'','AKM_EquipCharge' if n=='equip' else 'AKM_Native_'+n.replace('drum_',''),end,120) for n,end in [('idle',5),('aim',5),('fire',12),('aim_fire',12),('equip',204),('reload',400),('reload_empty',515),('drum_reload',400),('drum_reload_empty',515)]]
requested=sys.argv[sys.argv.index('--')+2:] if '--' in sys.argv else []
if requested:specs=[x for x in specs if x[0] in requested]
sys.argv=['build_grip.py']
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def weight(clip,f,end):
 return 1-smooth((f-18)/24)+smooth((f-(end-48))/36) if 'reload' in clip else 1
code=(ROOT/'Reference/build_animation.py').read_text();code=code[code.index('report='):]
code=code.replace("source=BASE/folder/('M4_DrumContact_Editable.blend' if clip.startswith('drum') else 'M4_Hand_MAT_Editable.blend')","source=ROOT/'AKM_Attachments_Editable.blend'")
code=code.replace('end*hz/60','end*hz/120').replace('k*60/hz','k*120/hz').replace('s.render.fps=60','s.render.fps=120').replace('bake_anim_step=60/hz','bake_anim_step=120/hz').replace('end/60','end/120')
code=code.replace("'A_M4_Foregrip_'","'A_AKM_'+variant+'_' ")
code=code.replace("if f<end/2:opening=smooth(f/4);retreat=smooth((f-4)/5)\n    else:opening=1-smooth((f-(end-6))/6);retreat=1-smooth((f-(end-16))/10)","if f<end/2:opening=smooth(f/18);retreat=smooth((f-8)/26)\n    else:opening=1-smooth((f-(end-20))/20);retreat=1-smooth((f-(end-48))/36)")
if variant=='prism':
 code=code.replace("H.translation+=grip.to_3x3().col[1].normalized()*(.11*retreat)","H.translation+=grip.to_3x3()@Vector(fit['release_vector'])*retreat")
 code=code.replace("grip.to_3x3().col[1].normalized()*(.08*math.sin(math.pi*w))","(grip.to_3x3()@Vector(fit['release_vector']))*math.sin(math.pi*w)")
start=code.index(' with bpy.data.libraries.load(');end=code.index(' bpy.ops.wm.save_as_mainfile',start)
code=code[:start]+" runpy.run_path(str(ROOT/'preview_visibility.py'))['configure_preview'](clip.startswith('drum'),variant)\n"+code[end:]
exec(compile(code,str(ROOT/'Reference/build_animation.py'),'exec'))
