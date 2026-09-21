"""Remove simulation cage from the render deliverable without remaking assets."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import layered_v04 as common
OUT=ROOT/'Authoring/OriginalRobeV05'
DEL=ROOT/'Delivery/OriginalRobeV05'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Witch_OriginalRobeV05.blend'))
rig=common.rig();common.neutral(rig)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
cage=bpy.data.objects['Witch_Robe_SimProxy']
cage.hide_render=False
common.export(DEL/'SK_Witch_OriginalRobeV05_ClothBuildSource.fbx',[rig]+meshes)
cage.hide_render=True
render=[o for o in meshes if o!=cage]
common.export(DEL/'SK_Witch_OriginalRobeV05.fbx',[rig]+render)
report={'render_objects':[o.name for o in render],
        'excluded_objects':[cage.name],
        'cloth_build_source':'SK_Witch_OriginalRobeV05_ClothBuildSource.fbx',
        'render_fbx':'SK_Witch_OriginalRobeV05.fbx',
        'geometry_changed':False,'animations_changed':False}
(OUT/'render_only_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
