"""Reproduce the controlled material comparison using the mesh saved by UE."""
from pathlib import Path
entry=Path(__file__).parent/'render_ab.py'
code=entry.read_text(encoding='utf-8').split('variants=')[0]
code=code.replace("P/'SourceAssets/M16StockDonor20261015/Final/SM_M16_tactical_telescopic.fbx'","O/'Final/SM_M16_Telescopic_SavedUE.fbx'")
exec(compile(code,str(entry),'exec'))
normal=O/'Final/T_M16_Telescopic_MatchedNormal.png'
plain=material('ControlledPlain',None)
matched=material('ControlledMatchedNormal',normal)
for obj in objects:
 for i,slot in enumerate(obj.data.materials):
  name=slot.name
  obj.data.materials[i]=matched if any(s in name for s in ('Telescopic_Metal','Telescopic_Polymer','Telescopic_Rubber')) else plain
scene.render.filepath=str(V/'I_repaired_saved_mesh.png');bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Final/Controlled_RepairedPreview.blend'))
(O/'saved_mesh_render.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('REPAIRED_SAVED_RENDER',scene.render.filepath,flush=True)
