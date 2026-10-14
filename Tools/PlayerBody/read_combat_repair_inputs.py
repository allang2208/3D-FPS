"""Read the existing laser's transforms and mesh bounds for the reported gap."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BodyCombatRepair20261006V2');OUT.mkdir(parents=True,exist_ok=True)
def vec(v):return list(v.to_tuple())
def tr(t):return dict(location=vec(t.translation),rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=vec(t.scale3d))
cylinder=u.load_asset('/Engine/BasicShapes/Cylinder');bounds=cylinder.get_bounds()
report=dict(cylinder=dict(origin=vec(bounds.origin),extent=vec(bounds.box_extent)),components=[])
for world in u.EditorLevelLibrary.get_pie_worlds(False):
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=comp.get_editor_property('static_mesh')
            if not mesh:continue
            mats=[comp.get_material(i).get_path_name() if comp.get_material(i) else '' for i in range(comp.get_num_materials())]
            if not any('Laser' in s or 'laser' in s for s in mats+[mesh.get_path_name()]):continue
            entry=dict(name=comp.get_path_name(),mesh=mesh.get_path_name(),visible=comp.is_visible(),transform=tr(comp.get_world_transform()),materials=mats)
            for socket in ['Emitter','AimGuide']:
                if comp.does_socket_exist(socket):entry[socket]=tr(comp.get_socket_transform(socket))
            report['components'].append(entry)
(OUT/'laser-inputs.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
