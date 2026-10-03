"""Save explicit leaf IDs and optional disabled cloth authoring bindings."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).parent))
import author_original_surfaces_v08 as support
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV09')
source=OUT/'M07_Original_Skinned_Master_V09.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
saved_action=rig.animation_data.action if rig.animation_data else None
rig.animation_data_clear(); rig.data.pose_position='REST'
bpy.context.scene.frame_set(0)
display=[bpy.data.objects['M07_OriginalBody_Display']]
proxies=[]; bindings=[]
manifest_path=OUT/'cloth_ue_manifest_original_v09.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
skin=np.load(OUT/'gill_skin_weights_v09.npz')
palette=[(1.,0.,0.,1.),(0.,1.,0.,1.),(0.,0.,1.,1.),(1.,1.,0.,1.),(1.,0.,1.,1.),(0.,1.,1.,1.)]
for label in range(1,7):
    game=bpy.data.objects[f'M07_OriginalGill_{label:02d}_Display']
    proxy=bpy.data.objects[f'M07_OriginalGill_{label:02d}_Simulation']
    for old in list(game.modifiers):
        if old.type=='SURFACE_DEFORM': game.modifiers.remove(old)
    if not manifest.get('shared_fold_pinning',False):
        panel=manifest['panels'][label-1]
        distances=skin['fold_source_distance_cm'][np.asarray(panel['source_original_vertices']),label]
        free=np.clip((distances-2.)/12.,0,1); free=free*free*(3-2*free)
        maximum=np.asarray(panel['max_distance_cm'])*free
        pin=np.maximum(np.asarray(panel['pin_weights']),1-free)
        panel['max_distance_cm']=maximum.tolist(); panel['pin_weights']=pin.tolist()
        group=proxy.vertex_groups.get('M07_Pin') or proxy.vertex_groups.new(name='M07_Pin')
        group.remove(list(range(len(proxy.data.vertices))))
        for i,value in enumerate(pin):
            if value>0: group.add([i],float(value),'REPLACE')
    # Binary endpoint colors are immune to linear/sRGB conversions. The
    # gill material does not read them; native authoring uses anatomical IDs.
    for old in list(game.data.color_attributes): game.data.color_attributes.remove(old)
    colors=game.data.color_attributes.new(name='M07LeafIdentity',type='BYTE_COLOR',domain='CORNER')
    colors.data.foreach_set('color',list(palette[label-1])*len(game.data.loops))
    game.data.color_attributes.active_color=colors
    proxy.hide_set(False); game.hide_set(False)
    bpy.context.view_layer.objects.active=game
    surface=game.modifiers.new('M07_ProxyAuthoring_Disabled','SURFACE_DEFORM')
    surface.target=proxy
    bpy.ops.object.surfacedeform_bind(modifier=surface.name)
    surface.show_viewport=surface.show_render=False
    bindings.append({'panel':label,'bound':bool(surface.is_bound)})
    proxy.hide_set(True)
    display.append(game); proxies.append(proxy)
manifest['shared_fold_pinning']=True
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
support.export(OUT/'SK_M07_Display_OriginalV09.fbx',rig,display)
support.export(OUT/'SK_M07_ClothBuildSource_OriginalV09.fbx',rig,[*display,*proxies])
rig.data.pose_position='POSE'
if saved_action:
    rig.animation_data_create(); rig.animation_data.action=saved_action
    if saved_action.slots: rig.animation_data.action_slot=saved_action.slots[0]
bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
record=json.loads((OUT/'gill_delivery_v09.json').read_text(encoding='utf-8'))
record.update({'render_leaf_ids':'Six exact binary RGB endpoint identities; independent of shared gill bone weights',
    'blender_proxy_bindings':bindings,'blender_proxy_deformation_enabled':False,
    'shared_fold_cloth_pin':'Fixed within 2 cm of original shared/body fold; 12 cm geodesic transition to free original proxy',
    'tested':False})
(OUT/'gill_delivery_v09.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('M07_V09_LEAF_IDENTITIES_AND_SOURCE_BINDINGS_SAVED',flush=True)
