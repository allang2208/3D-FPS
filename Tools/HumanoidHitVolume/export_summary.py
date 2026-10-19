"""Keep measured geometry distinct from the confirmed Night Warden configuration failure."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/HumanoidHitVolume20261018'
sources = [OUT / 'baseline.json', OUT / 'nightwarden.json']
monsters = {}
for source in sources:
    report = json.loads(source.read_bytes())
    for monster in report['monsters']:
        monsters[monster['id']] = monster
assert len(monsters) == 17, 'The audit inventory must contain all 17 humanoids.'
configuration_failures = []
for monster in monsters.values():
    assert not monster.get('error'), monster
    assert len(monster['poses']) == 5, monster['id']
    errors = [pose for pose in monster['poses'] if pose.get('error')]
    if errors:
        # This is an observed defect, never a successful head-coverage measurement.
        assert monster['id'] == 'NightWardenRig', monster
        assert monster['mesh_collision_enabled'] == 0 and monster['physics_asset'] == 'None', monster
        assert monster['capsule_visibility_response'] == 0, monster
        configuration_failures.append(dict(id=monster['id'],
            mesh_collision_enabled=0, physics_asset='None', capsule_visibility_response=0,
            unmeasured_poses=errors, reason='Body hit collision disabled and physics asset absent. '
                'Pose sampling also failed its clip/semantic-head precondition. No coverage percentage is claimed.'))
        continue
    for pose in monster['poses']:
        assert not pose.get('error'), (monster['id'], pose)
        assert pose.get('views') or pose.get('skipped'), (monster['id'], pose)

rows = []
for monster in monsters.values():
    if any(pose.get('error') for pose in monster['poses']):
        continue
    for pose in monster['poses']:
        if pose.get('skipped'):
            continue
        counts = {key: sum(view[key] for view in pose['views']) for key in (
            'visible_head_rays', 'complex_head_hits', 'complex_misses',
            'complex_other_hits', 'head_hits_outside_mesh')}
        rows.append(dict(id=monster['id'], name=monster['name'], pose=pose['pose'],
            **counts, head_coverage_pct=round(100 * counts['complex_head_hits'] /
                max(1, counts['visible_head_rays']), 2),
            feedback_rotation_gap_deg=pose['head_body_rotation_error_before_forced_sync_deg'],
            physics_asset=monster['physics_asset']))
with (OUT / 'coverage.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
summary = dict(review_complete=True, geometry_sampling_complete=not configuration_failures,
    inventory_count=17, sampled_monsters=len(monsters)-len(configuration_failures), sampled_poses=len(rows),
    configuration_failures=configuration_failures,
    source_reports=[str(p.relative_to(ROOT)) for p in sources],
    baseline_status_note='The first probe enumerated 17 entries but sampled 16. The separate NightWardenRig '
        'query loaded its actual configuration and confirmed a missing hit setup, but did not yield head-surface percentages. '
        'The raw failure and nonzero commandlet exit are preserved; they are not counted as a passed geometry check.',
    assets_modified=False, gameplay_started=False,
    interpretation='Coverage of sampled, skin-weight-labelled head surfaces, not player accuracy. '
        'Head descendants can include hair, hoods and sensory appendages; these are not automatically flesh weakpoints. '
        'Other mesh surfaces that occlude the head are excluded. Fit queries explicitly synchronize physics first; '
        'the separately recorded feedback rotation gap is measured before that forced synchronization.',
    rows=rows)
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
lines = [
    '人形怪物头部命中排查 — 2026-10-18',
    '范围：F6 当前目录中的 17 类人形；实际保存蓝图构造后的组件、模型和物理资产。',
    '完成情况：16类取得80组姿态量化数据；守寝者完成配置读取并确认命中配置缺失，未取得头部覆盖率。',
    '方法：待机第0帧、待机中段、行走、攻击、受击摆头；4个方向，每方向25×25射线网格。',
    '守寝者的自动姿态采样还被clip/semantic-head前置条件阻断；原始失败和退出码3保留，不记作通过。',
    '先按LOD0蒙皮表面筛出可见头部射线，排除真实身体/手臂遮挡，再查询Visibility复杂射线和要害判定。',
    '百分比是几何采样覆盖率，不是玩家射击命中率。头骨后代权重可能含头发、头罩、感知附肢。',
    '碰撞拟合查询之前显式同步物理；受击旋转差在该同步之前另行记录。',
    '没有调用BeginPlay，没有启动AI、游戏内战斗或联机；没有保存/修改任何怪物资产。',
    '', '初始待机：名称 / 头部判定覆盖率 / 完全打空 / 判到其他部位 / 有效表面射线数',
]
for row in rows:
    if row['pose'] == 'spawn_idle':
        print(row['name'], row['head_coverage_pct'], row['complex_misses'],
              row['complex_other_hits'], '/', row['visible_head_rays'])
        lines.append(f"{row['name']} / {row['head_coverage_pct']}% / {row['complex_misses']} / "
                     f"{row['complex_other_hits']} / {row['visible_head_rays']}")
lines.append('守寝者 M-01 / 未取得覆盖率 / 网格NoCollision / PhysicsAsset=None / 胶囊忽略Visibility')
lines += ['', '已定位：',
    '1. M-01员工三组共享来自PA_ZombieFemale的头部物理形状，与新模型头部外形不完全匹配。',
    '2. 胖子、突变体3、毒液僵尸有模型头部射线先碰到Spine/Spine01/Spine02/上臂碰撞的记录。',
    '3. MonsterIdleBreathingMeshComponent在引擎物理更新之后叠加受击头部旋转；采样测得约4.94–6.85度不同步。',
    '4. 护士、螳螂的头部权重表面也有打空；巫婆头罩、盲祷者感知附肢应与真正的脸部弱点分开解释。',
    '5. 守寝者独立ACharacter的实际保存配置：Mesh NoCollision、Mesh Visibility Ignore、无PhysicsAsset、胶囊Visibility Ignore。',
    '', '修复位置：',
    '员工：PA_FacelessSecurity / PA_FacelessReceptionist / PA_FacelessResearcher；按真实头部校准并处理颈部交界。',
    '胖子/突变体/毒液僵尸：各自PhysicsAsset的躯干、上臂与头部交界；避免通过放大头碰撞补洞。',
    '受击不同步：Source/FPSGAME/Monsters/MonsterIdleBreathingMeshComponent.cpp::FinalizeBoneTransform。',
    '守寝者：Source/FPSGAME/Monsters/NightWardenMonster.cpp的构造碰撞设置及保存的BP_NightWarden。',
    '', '本轮为排查结果；游戏碰撞修复和实战验收尚未执行。',
    '数据：coverage.csv、summary.json、baseline.json、nightwarden.json。',
]
(OUT / 'findings.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
print('Reviewed inventory:', len(monsters), 'sampled poses:', len(rows), 'configuration failures:', len(configuration_failures))
