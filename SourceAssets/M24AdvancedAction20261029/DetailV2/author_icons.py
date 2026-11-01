"""One current-part grayscale catalog icon; original-body icon is preserved."""
import bpy,json,runpy,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_AdvancedAction_DetailV2.blend'),use_scripts=False)
keep=[bpy.data.objects['M24_AdvancedAction_DetailBody']]
for ob in list(bpy.data.objects):
    if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
ob=keep[0];ob.hide_set(False);ob.hide_render=False
pts=[ob.matrix_world@v.co for v in ob.data.vertices]
lo=Vector([min(p[k] for p in pts) for k in range(3)]);hi=Vector([max(p[k] for p in pts) for k in range(3)])
ob.data.transform(Matrix.Scale(1.28/max(hi.y-lo.y,hi.z-lo.z),4)@Matrix.Translation(-(lo+hi)*.5)@ob.matrix_world)
ob.matrix_world=Matrix.Identity(4);ob.location.x=-.17
G['apply_grayscale'](keep);s=bpy.context.scene;key='m24_advanced_action'
frame=(O.parent.parent/'M24Modular20261027/author_icons.py').read_text(encoding='utf-8')
frame=frame[frame.index('    def mat(name'):];frame='\n'.join(x[4:] if x.startswith('    ') else x for x in frame.splitlines())
exec(compile(frame,'Shared M24 gray metal frame production','exec'))
(O/'icon_receipt.json').write_text(json.dumps(dict(complete=True,source='M24_AdvancedAction_DetailV2.blend',
    file=str(O/'Icons/m24_advanced_action.png'),actual_model=True,grayscale=True,gameplay_preview=False),indent=2))
