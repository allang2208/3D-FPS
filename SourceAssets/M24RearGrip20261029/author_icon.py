"""Produce only the M24 factory icon; shared option and category art is reused."""
import bpy,runpy,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;(O/'Icons').mkdir(exist_ok=True)
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_RearGrip_Editable.blend'),use_scripts=False)
ob=bpy.data.objects['M24_OriginalGripSurface'];ob.hide_set(False);ob.hide_render=False
for x in list(bpy.data.objects):
    if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
pts=[v.co for v in ob.data.vertices];lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
ob.data.transform(Matrix.Scale(1.20/max(hi.y-lo.y,hi.z-lo.z),4)@Matrix.Translation(-(lo+hi)*.5));ob.location.x=-.17
G['apply_grayscale']([ob]);s=bpy.context.scene;key='false'
frame=(O.parent/'M24Modular20261027/author_icons.py').read_text(encoding='utf-8')
frame=frame[frame.index('    def mat(name'):];frame='\n'.join(x[4:] if x.startswith('    ') else x for x in frame.splitlines())
exec(compile(frame,'M24 shared factory icon frame','exec'))
