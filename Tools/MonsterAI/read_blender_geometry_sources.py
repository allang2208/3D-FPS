"""Read authoring inputs before offline reduction; no previews or gameplay."""
import bpy, json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/AlienGeometry20261006/BlenderV2')
ROOT.mkdir(parents=True, exist_ok=True)
SOURCES = {
 'HangingBellM09': 'SourceAssets/HangingBellM09Meshy20261003/ArmContinuityV16/Authoring/M09_ContinuousArms_V16.blend',
 'SpiralPillarM14': 'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Authoring/M14_SupportSkin_v15.blend',
 'M10Mawcrawler': 'SourceAssets/M10ChenXia20261003/SurfaceRigV5/Delivery/M10_SurfaceRigV5_Editable.blend',
 'LurkerM08': 'SourceAssets/Monsters/LurkerM08/CanineRigV03_20261004/M08_CanineRig_Skin_V03.blend',
}
result = {}
for ident, source in SOURCES.items():
    bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/' + source, load_ui=False)
    entry = dict(source=source, units=bpy.context.scene.unit_settings.scale_length, objects=[])
    for obj in bpy.context.scene.objects:
        if obj.type not in {'MESH','ARMATURE'}: continue
        info = dict(name=obj.name, type=obj.type, parent=obj.parent.name if obj.parent else None,
                    matrix=[list(row) for row in obj.matrix_world], hidden=obj.hide_render)
        if obj.type == 'MESH':
            mesh=obj.data
            info.update(vertices=len(mesh.vertices), triangles=sum(len(p.vertices)-2 for p in mesh.polygons),
                materials=[m.name if m else None for m in mesh.materials],
                morphs=[k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
                uv_layers=[v.name for v in mesh.uv_layers],
                modifiers=[dict(name=m.name,type=m.type,viewport=m.show_viewport,render=m.show_render) for m in obj.modifiers])
        else: info.update(bones=[b.name for b in obj.data.bones])
        entry['objects'].append(info)
    result[ident]=entry
    print('BLENDER_SOURCE',ident,flush=True)
    (ROOT/'source_inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
