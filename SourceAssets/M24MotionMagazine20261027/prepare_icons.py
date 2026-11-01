"""Generate this batch's deterministic actual-part icon production script."""
from pathlib import Path
O=Path(__file__).resolve().parent
t=(O.parent/'M24Surface20261027/author_icons.py').read_text(encoding='utf-8')
a=t.index("M=json.loads");b=t.index("    keep=[bpy.data.objects",a)
t=t[:a]+'''M={'m24_factory_mag_5':{'objects':['M24_clip']},'m24_extended_mag_10':{'objects':['M24_Magazine10']}}
R={}
for key,row in M.items():
    iron=False
    source=O/'M24_MotionMagazine_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
'''+t[b:]
t=t.replace("for group in ('Body','Scope'):","for group in ('Body',):")
t=t.replace("bpy.data.materials.get('M24_'+group)","bpy.data.materials.get('M24_Magazine5')")
t=t.replace("O/'Textures'","O.parent/'M24Surface20261027/Textures'")
t=t.replace("o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear()","o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear();o.hide_render=False;o.hide_set(False)")
(O/'author_icons.py').write_text(t,encoding='utf-8')
