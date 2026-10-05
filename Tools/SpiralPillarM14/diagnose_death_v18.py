"""Read current V17 bindings and materials for the reported launch/black defect."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004/ProductionV18/Records')
out.mkdir(parents=True,exist_ok=True)
root='/Game/Monsters/SpiralPillarM14/'
def xyz(v): return [v.x,v.y,v.z]
def transform(t):
    return dict(translation=xyz(t.translation),rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=xyz(t.scale3d))
def prop(o,n): return o.get_editor_property(n)
d=u.load_asset(root+'DA_M14_XPBDCorpse_v17')
r={}
export=u.AssetExportTask()
export.object=d;export.filename=str(out/'data.t3d');export.automated=True
export.exporter=u.ObjectExporterT3D()
r['data_exported']=u.Exporter.run_asset_export_task(export)
mesh=prop(d,'corpse_mesh')
p=u.PoseableMeshComponent()
p.set_skinned_asset_and_update(mesh)
r['corpse_bones']=[dict(name=str(p.get_bone_name(i)),transform=transform(p.get_bone_transform_by_name(p.get_bone_name(i),u.BoneSpaces.COMPONENT_SPACE))) for i in range(p.get_num_bones())]
r['materials']=[]
L=u.MaterialEditingLibrary
for slot in mesh.materials:
    m=slot.material_interface
    nodes=L.get_material_expressions(m)
    normal=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
    entry=dict(path=m.get_path_name(),tangent=prop(m,'tangent_space_normal'),normal=str(normal),expressions=[])
    for n in nodes:
        info=dict(type=n.get_class().get_name(),name=n.get_name())
        if isinstance(n,u.MaterialExpressionCustom):
            info.update(code=prop(n,'code'),inputs=[str(i) for i in prop(n,'inputs')])
        if isinstance(n,u.MaterialExpressionTextureSample): info['texture']=str(prop(n,'texture'))
        entry['expressions'].append(info)
    r['materials'].append(entry)
r['worlds']=[]
for w in u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(),u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world():
    if not w: continue
    actors=u.GameplayStatics.get_all_actors_of_class(w,u.SpiralPillarM14)
    r['worlds'].append(dict(name=w.get_path_name(),actors=[dict(name=a.get_name(),transform=transform(a.get_actor_transform()),components=[str(c) for c in a.get_components_by_class(u.PoseableMeshComponent)]) for a in actors]))
(out/'diagnosis_asset.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print('M14_V18_DIAGNOSED',r['data_exported'],len(r['corpse_bones']),r['worlds'])
