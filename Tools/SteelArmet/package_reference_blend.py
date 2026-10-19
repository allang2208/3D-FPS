"""Organize the editable delivery without changing exported geometry."""
import bpy,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/SteelArmet20261019/ReferenceMatchV5')
bpy.ops.wm.open_mainfile(filepath=str(R/'Exports/SteelArmet_Detailed.blend'));S=bpy.context.scene
groups={}
for label in ('01 Skull and crown','02 Folded visor','03 Cheek and rear plates','04 Hinges and fasteners','05 Neck flange','06 Inner leather'):
    col=bpy.data.collections.new(label);S.collection.children.link(col);groups[label]=col
for ob in list(S.objects):
    if ob.type!='MESH' or any(c.name.startswith('REFERENCE_') for c in ob.users_collection):continue
    n=ob.name.lower()
    if any(k in n for k in ('padding','lining','leather','stitch')):label='06 Inner leather'
    elif any(k in n for k in ('hinge','rivet','latch','lifting peg','anchor')):label='04 Hinges and fasteners'
    elif any(k in n for k in ('collar','flange')):label='05 Neck flange'
    elif any(k in n for k in ('visor','eye lip')):label='02 Folded visor'
    elif any(k in n for k in ('cheek','lower return')):label='03 Cheek and rear plates'
    else:label='01 Skull and crown'
    for col in list(ob.users_collection):col.objects.unlink(ob)
    groups[label].objects.link(ob)
for ob in S.objects:ob.select_set(False)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=.60;area.spaces.active.region_3d.view_location=(0,-.01,0)
            area.spaces.active.region_3d.view_rotation=S.camera.rotation_euler.to_quaternion();area.spaces.active.region_3d.view_perspective='ORTHO'
            area.spaces.active.shading.type='MATERIAL'
S['design_reference']='../Design/SteelArmet_Concept.png';S['asset_status']='ReferenceMatchV5; runtime testing remains user-side'
ref=bpy.data.collections.new('REFERENCE_ApprovedConcept');S.collection.children.link(ref);ref.hide_render=True;ref.hide_viewport=True
ob=bpy.data.objects.new('Approved steel armet design',None);ob.empty_display_type='IMAGE';ob.data=bpy.data.images.load(str(R.parent/'Design/SteelArmet_Concept.png'));ob.empty_display_size=.6;ref.objects.link(ob)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports/SteelArmet_Detailed.blend'));print('DETAILED_ARMET_EDITABLE_PACKAGED',flush=True)
