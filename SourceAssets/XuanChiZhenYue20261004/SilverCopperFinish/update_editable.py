"""Replace the four packed finish maps in the editable sources; no render or export."""
import json
from pathlib import Path
import bpy

P=Path(__file__).resolve().parent;S=P.parent
files=[S/'BladeV3/XuanChi_BladeV3_Editable.blend',S/'SurfaceV2/XuanChi_SurfaceV2_Editable.blend']
maps={str((S/revision/'Textures'/(family+'_'+channel+'.png')).resolve()).lower()
      for revision,family in [('BladeV3','Blade'),('SurfaceV2','Hilt')]
      for channel in ['BaseColor','ORM']}
saved=[]
for file in files:
    bpy.ops.wm.open_mainfile(filepath=str(file))
    replaced=[]
    for im in list(bpy.data.images):
        if not im.filepath:continue
        source=Path(bpy.path.abspath(im.filepath)).resolve()
        if str(source).lower() not in maps:continue
        fresh=bpy.data.images.load(str(source),check_existing=False)
        fresh.colorspace_settings.name=im.colorspace_settings.name
        old_name=im.name
        im.user_remap(fresh);bpy.data.images.remove(im)
        fresh.name=old_name;fresh.pack()
        replaced.append(str(source))
    bpy.ops.wm.save_as_mainfile(filepath=str(file))
    saved.append({'file':str(file),'updated_maps':replaced})
(P/'editable_receipt.json').write_text(json.dumps(saved,indent=2))
print('XUANCHI_EDITABLE_FINISH_SAVED',flush=True)
