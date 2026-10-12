"""Read production M-series class/mesh bindings; do not save or run gameplay."""
from pathlib import Path
import json
import re
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'Saved/MSeriesGroundingAudit20261012'
OUT.mkdir(parents=True, exist_ok=True)
source = (ROOT / 'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp').read_text(encoding='utf-8-sig')
entries = re.findall(r'Add\(TEXT\("([^"]+)"\), TEXT\("([^"]+)"\), TEXT\("([^"]+)"\)', source)

def path(obj):
    return obj.get_path_name() if obj else None

def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None

def mesh_info(mesh):
    if not mesh:
        return None
    # Transient, unregistered component: read the reference skeleton only.
    component = u.new_object(u.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    return dict(path=path(mesh), skeleton=path(mesh.get_editor_property('skeleton')),
                post_process_anim_blueprint=path(mesh.get_editor_property('post_process_anim_blueprint')),
                bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())])

report = dict(scope='Production spawn-catalog M-series classes and default asset bindings',
              gameplay_run=False, assets_saved=False, monsters=[])
for ident, name, class_path in entries:
    if not re.search(r'M-?\d+', name):
        continue
    row = dict(id=ident, name=name, class_path=class_path)
    report['monsters'].append(row)
    try:
        cls = u.load_class(None, class_path)
        if not cls:
            raise RuntimeError('Class did not load')
        cdo = u.get_default_object(cls)
        mesh = prop(cdo, 'mesh')
        row['component'] = dict(path=path(mesh), anim_class=path(prop(mesh, 'anim_class')),
                                animation_mode=str(prop(mesh, 'animation_mode')),
                                relative_location=str(prop(mesh, 'relative_location')),
                                relative_rotation=str(prop(mesh, 'relative_rotation')),
                                relative_scale=str(prop(mesh, 'relative_scale3d')),
                                disable_post_process_blueprint=prop(mesh, 'disable_post_process_blueprint'),
                                override_post_process_anim_bp=path(prop(mesh,'override_post_process_anim_bp')))
        row['tags'] = [str(tag) for tag in prop(cdo,'tags')]
        row['mesh'] = mesh_info(mesh.get_skeletal_mesh_asset()) if mesh else None
        dataset = prop(cdo, 'animation_set')
        if dataset:
            row['animation_set'] = dict(path=path(dataset),
                                        reference_mesh=mesh_info(prop(dataset, 'reference_mesh')),
                                        actions={str(k):path(prop(v,'sequence')) for k,v in prop(dataset,'actions').items()})
        assets = {}
        for key in ('visual_mesh', 'idle_animation', 'walk_animation', 'run_animation', 'idle_clip', 'walk_clip', 'crawl_clip', 'move_clip'):
            value = prop(cdo,key)
            if value:
                assets[key] = path(value)
                if isinstance(value,u.SkeletalMesh):
                    row[key] = mesh_info(value)
        row['assets'] = assets
        movement = prop(cdo,'character_movement')
        row['movement'] = dict(class_path=path(movement.get_class()), max_step_height=prop(movement,'max_step_height'),
                               walkable_floor_angle=prop(movement,'walkable_floor_angle'),
                               flat_base_floor=prop(movement,'use_flat_base_for_floor_checks')) if movement else None
        row['loaded_class'] = path(cdo.get_class())
    except Exception as exc:
        row['error'] = str(exc)
    print('M_GROUND_AUDIT '+ident+' '+str(row.get('error','read')))

(OUT/'asset-bindings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M_GROUND_AUDIT_DONE '+str(len(report['monsters'])))
