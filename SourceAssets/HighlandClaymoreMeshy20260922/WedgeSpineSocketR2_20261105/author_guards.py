"""Prepare an assembly scene and export just the fitted variants of the five live guards."""
import json
import sys
from pathlib import Path
import bpy

P=Path(__file__).resolve().parent
BASE=P.parent
WORK=BASE.parents[1]/'Saved'/'RidgeLowSeat'
sys.path.insert(0,str(P))
from guard_seat import cut_guard

(P/'Export').mkdir(exist_ok=True)
WORK.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'RidgePiercerRootV2_20260927/Highland_RidgePiercer_RootV2_Editable.blend'))
for o in list(bpy.context.scene.objects):
    if o.name not in ('SM_Highland_Grip_factory','SM_Highland_Pommel_factory'):
        bpy.data.objects.remove(o,do_unlink=True)
junction=BASE/'JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend'
cloven=BASE/'ClovenSurface20261002/BladeMetal20261002/Highland_ClovenGuard_BladeMetal20261002_Editable.blend'
for kind in ('factory','bastion_guard','riposte_guard','light_guard','Cloven'):
    name='SM_Highland_Guard_'+kind
    with bpy.data.libraries.load(str(cloven if kind=='Cloven' else junction)) as (src,dst):
        dst.objects=[name+'_JunctionV5']
    obj=dst.objects[0]
    bpy.context.scene.collection.objects.link(obj)
    seam=cut_guard(obj)
    if kind=='factory':
        (WORK/'socket_ring.json').write_text(json.dumps(seam),encoding='utf-8')
    obj.name=name+'_SurfaceV4'
    obj.hide_set(False)
    obj.hide_render=False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
                             axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
    obj.hide_set(kind!='factory')
    obj.hide_render=kind!='factory'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'FittedGuardAssembly.blend'))
