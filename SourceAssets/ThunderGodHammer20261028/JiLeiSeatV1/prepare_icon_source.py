from pathlib import Path
P=Path(__file__).resolve().parent
old=(P.parent/'GuanLeiRebuildV2/render_icon_source.py').read_text(encoding='utf-8')
head="""import bpy,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P/'JiLeiSeatV1_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_head_mount_ji_lei_seat']
obj=b.objects[0];bpy.context.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
bpy.context.preferences.filepaths.save_version=0
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale
apply_grayscale([obj])
"""
tail=old[old.index("scene=bpy.context.scene"):].replace('GuanLeiSeatV2_IconSource','JiLeiSeat_IconSource')
(P/'render_icon_source.py').write_text(head+tail,encoding='utf-8')
