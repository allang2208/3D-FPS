"""Place selected, unchanged existing FBX references after prepare_revision.py.

No geometry generation or re-export. Config uses Blender metres/right-handed yaw;
UE installer converts location [x,-y,z]*100 and yaw=-yaw_deg as usual.
Run only as part of the coordinated production config/authoring sequence.
"""
import json
import math
import itertools
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPLEMENT = ROOT / 'References/RevisionSupplement'
STAGE = 'revision_supplement'


def rotate(point, yaw):
    a = math.radians(yaw)
    c, s = math.cos(a), math.sin(a)
    return [point[0]*c-point[1]*s, point[0]*s+point[1]*c, point[2]]


def main():
    config_path = ROOT / 'Config/scene.json'
    cfg = json.loads(config_path.read_text('utf8'))
    handoff = json.loads((SUPPLEMENT / 'HANDOFF.json').read_text('utf8'))
    by_name = {a['name']: a for a in handoff['assets']}
    room = next(r for r in cfg['rooms'] if r['id'] == 'AccumulatorControl')
    front = room['control_room']['y_bounds_m'][0]
    # The wall sockets touch the inner face of the 0.24m front wall. This is
    # 0.25m nearer the wall than the earlier simple staff desk's anchor.
    desk = [0, front + .770, 0]
    requests = [
        ('ControlRecordsDesk', 'SM_SW_DispatchDesk', desk, 180, 'control_dispatch'),
        ('ControlRecordsElectronics', 'SM_SW_DispatchElectronics', desk, 180, 'control_dispatch'),
        ('ControlServerRack01', 'SM_Archive_ServerRack_V1', [3.00, front+.714, 0], 180, 'control_server_01'),
        ('ControlServerRack02', 'SM_Archive_ServerRack_V1', [4.10, front+.714, 0], 180, 'control_server_02'),
        ('GalleryPartsRack', 'SM_SW_PartsRack', [-10.40, 18.01, 0], -150, 'gallery_parts'),
        ('GalleryRackSpares', 'SM_SW_RackSpares_0', [-10.40, 18.01, 0], -150, 'gallery_parts'),
        ('GalleryMaintenanceLadder', 'SM_Prop_StepLadder', [-12.20, 17.30, 0], -150, 'gallery_ladder'),
        ('GalleryMotorStand', 'SM_SW_MotorStand', [10.40, 18.01, 0], 150, 'gallery_motor'),
        ('GalleryMotorService', 'SM_SW_MotorService', [10.40, 18.01, 0], 150, 'gallery_motor'),
    ]
    selected = list(dict.fromkeys(row[1] for row in requests))
    # Retain all unrelated declarations and placements, including the older
    # staff desk declaration used in the other rooms.
    declarations = cfg.setdefault('existing_assets', [])
    selected_set = set(selected)
    declarations[:] = [a for a in declarations if a['id'] not in selected_set]
    for name in selected:
        source = by_name[name]
        declarations.append(dict(
            id=name, mesh=source['ue'],
            package_fbx='References/RevisionSupplement/' + source['package_fbx'],
            materials=source['materials'], source_sha256=source['fbx_sha256'],
            source_anchor_blender_m=source['source_anchor_blender_m'],
            source_geometry_bounds_blender_m=source['source_geometry_bounds_blender_m'],
            original_ue_file_sha256=source.get('ue_file_sha256'),
            reuse_stage=STAGE,
        ))
    ids = {r[0] for r in requests} | {'ControlRecordsChair'}
    room['reused_parts'] = [p for p in room.get('reused_parts', [])
                            if p.get('reuse_stage') != STAGE and p['id'] not in ids]
    placed = []
    for ident, name, target, yaw, assembly in requests:
        source = by_name[name]
        offset = rotate(source['source_anchor_blender_m'], yaw)
        actor = [round(target[k] - offset[k], 9) for k in range(3)]
        room['reused_parts'].append(dict(
            id=ident, mesh=source['ue'], source_asset_id=name,
            position_m=actor, target_anchor_m=target,
            source_anchor_blender_m=source['source_anchor_blender_m'],
            yaw_deg=yaw, scale=[1, 1, 1], collision=bool(source['collision']),
            cast_shadow=True, reuse_stage=STAGE, source_assembly_id=assembly,
            source_sha256=source['fbx_sha256'],
        ))
        if name == 'SM_Archive_ServerRack_V1':
            room['reused_parts'][-1]['materials'] = [cfg['ue_base']+'/Materials/M_Power_ServerChinese']
        workshop_roles = {'M_Workshop_Print':'WorkshopPrintCN','M_Workshop_Screen':'WorkshopScreenCN'}
        original_materials = list(source['materials'].values())
        chinese_materials = []
        for value in original_materials:
            role = workshop_roles.get(value.rsplit('/',1)[-1])
            chinese_materials.append(cfg['ue_base']+'/Materials/M_Power_'+role if role else value)
            if role and role not in cfg.setdefault('required_material_roles',[]):cfg['required_material_roles'].append(role)
        if chinese_materials != original_materials:room['reused_parts'][-1]['materials'] = chinese_materials
        bounds = source['source_geometry_bounds_blender_m']
        corners = [rotate(p, yaw) for p in itertools.product(*zip(bounds['min'], bounds['max']))]
        local_bounds = {key: [round(fn(p[k] + actor[k] for p in corners), 7) for k in range(3)]
                        for key, fn in [('min', min), ('max', max)]}
        placed.append(dict(id=ident, source_asset_id=name, mesh=source['ue'],
            target_anchor_m=target, actor_position_m=actor, yaw_blender_deg=yaw,
            source_geometry_bounds_blender_m=bounds, placed_conservative_bounds_room_m=local_bounds,
            source_sha256=source['fbx_sha256']))
    room['revision_supplement'] = dict(
        source='References/RevisionSupplement/HANDOFF.json',
        selected_existing_types=selected,
        omitted_assets={
            'SM_SW_Electrical': 'Whole-room 9.245 x 6.8625m group exceeds cabin depth; never cropped or scaled.',
            'SM_SW_RackSpares_1': 'Alternative state; RackSpares_0 selected.',
            'SM_SW_RackSpares_2': 'Alternative state; RackSpares_0 selected.',
        },
        coordinate_contract='Actor=target_anchor-Rz(yaw)*source_anchor; FBX node/world transform baked exactly once in author preview.',
        source_dimensions_preserved=True,
        step_ladder_height_m=1.1,
        acceptance_tests_run=False, rendered=False, ue_imported=False,
    )
    roles = cfg.setdefault('required_material_roles', [])
    if 'ServerChinese' not in roles:
        roles.append('ServerChinese')
    config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2)+'\n', 'utf8')
    receipt = dict(stage='placement_configured_pending_author_assembly',
        source='References/RevisionSupplement/HANDOFF.json', placements=placed,
        bounds_method='Transform eight corners of handoff original source AABBs; conservative rotated envelopes, not runtime/acceptance collision tests.',
        selected_unique_original_meshes=len(selected), original_mesh_instances=len(requests),
        original_files_modified=False, originals_reexported=False,
        removed_previous_rows=['ControlRecordsDesk (replaced)', 'ControlRecordsChair (omitted for aisle clearance)'],
        omitted_assets=room['revision_supplement']['omitted_assets'],
        tests_run=False, rendered=False, ue_imported=False)
    (ROOT/'Receipts/revision-supplement.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', 'utf8')
    print('REVISION_SUPPLEMENT_PLACED', len(requests), 'instances from', len(selected), 'existing types', flush=True)


if __name__ == '__main__':
    main()
