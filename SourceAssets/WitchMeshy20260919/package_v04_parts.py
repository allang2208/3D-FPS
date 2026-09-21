"""Add explicit scenes to the split authoring libraries for direct opening."""
import bpy,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Authoring/LayeredV04'
for file in list((OUT/'Preserved').glob('*.blend'))+list((OUT/'Fitted').glob('*.blend')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=src.objects
    scene=bpy.context.scene;scene.name=file.stem;scene.unit_settings.system='METRIC';scene.render.fps=60
    for obj in dst.objects:
        if obj and obj.name not in scene.collection.objects:scene.collection.objects.link(obj)
    scene['source_layer']=file.parent.name;scene['runtime_tested']=False
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.make_local(type='ALL')
    bpy.ops.file.pack_all()
    staging=file.with_name(file.stem+'_packaging.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(staging))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.replace(staging,file)
shutil.copy2(Path('D:/FPS3D/FPSGAME/Saved/NurseZombie/ANMS_ZombieFemaleWalk01Forward.fbx'),OUT/'Sources/Nurse_SourceSkinWalk.fbx')
print('V04_PART_SCENES_PACKAGED')
