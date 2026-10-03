"""Record successful necessary builds and actual saves without testing flags."""
import argparse
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'BodyMotionV18'
REPORT = OUT / 'ue_body_motion_delivery_v18.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authoring-editor-log', required=True)
    parser.add_argument('--import-log', required=True)
    parser.add_argument('--editor-log', required=True)
    parser.add_argument('--game-log', required=True)
    args = parser.parse_args()
    report = json.loads(REPORT.read_text(encoding='utf-8-sig'))
    if not report.get('saved') or not report.get('native_defaults_updated'):
        raise RuntimeError('Actual V18 saves and native activation are required before finalization.')
    report.update(native_editor_and_game_built=True,
                  build_logs={key: str(Path(value).resolve()) for key, value in vars(args).items()},
                  stage='Original mesh, contact proxy/cloth, four full-body clips and AI/F6 saved; Editor/Game builds completed',
                  tested=False, runtime_tested=False, visual_tested=False, user_review_pending=True)
    # The authoring helper's nested receipt predates save(mesh); its objects
    # are subobjects of the display package that the importer actually saved.
    report['cloth']['saved_with_display_package'] = True
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name in ('production_status.json', 'gameplay_delivery.json'):
        file = ROOT / name
        record = json.loads(file.read_text(encoding='utf-8-sig'))
        record.update(revision='BodyMotionV18', stage=report['stage'], mesh=report['mesh'],
                      ue_save_receipt=str(REPORT), native_editor_and_game_built=True,
                      body_motion_v18_build_logs=report['build_logs'],
                      tested=False, runtime_tested=False, visual_tested=False, user_review_pending=True)
        file.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for manifest in report['manifests']:
        file = Path(manifest)
        record = json.loads(file.read_text(encoding='utf-8-sig'))
        record.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT),
                      tested=False, runtime_tested=False, rendered=False, user_review_pending=True)
        if 'clips' in record:
            for role, clip in record['clips'].items():
                clip['asset'] = report['clips'][role]['asset']
                clip['ue_duration_seconds'] = report['clips'][role]['duration_s']
        else:
            record['ue_display_asset'] = report['mesh']
            record['ue_simulation_asset'] = report['simulation_source']
        file.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    source_report = json.loads((OUT / 'source_delivery_v18.json').read_text(encoding='utf-8-sig'))
    source_report.update(saved=True, native_editor_and_game_built=True,
                         ue_save_receipt=str(REPORT), stage=report['stage'], build_logs=report['build_logs'])
    source_report['initial_authoring_editor_build_attempt'] = source_report.pop('authoring_editor_build_attempt', None)
    source_report['initial_authoring_editor_build_result'] = source_report.pop('authoring_editor_build_result', None)
    source_report['authoring_editor_build_result'] = 'Succeeded; see successful build logs'
    source_report.pop('editor_occupancy', None)
    (OUT / 'source_delivery_v18.json').write_text(json.dumps(source_report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    doc = PROJECT / 'Docs/Monsters/BlindSupplicantM07BodyMotionV18.md'
    text = doc.read_text(encoding='utf-8')
    old = '当前阶段：动作与原表面接触层后台制作，原生实现及导入脚本已完成，正在必要构建与资产接入。此阶段不代表资产已经保存；最终保存结果以 '
    text = text.replace(old, '当前阶段：四段全身动作、原模型与背膜接触代理、布料／LOD 和现有 AI/F6 引用已实际保存，原生默认引用及 Editor/Game 构建均已完成。未运行或测试；实际保存结果以 ')
    cloth = report['cloth']
    text += '\n实际保存布料：{} 个模拟顶点、{} 个三角形、{} 个固定点、{} 个胶囊，{} 次迭代／{} 子步。显示捕获 {} 点、完全蒙皮 {} 点；完全蒙皮包括真实根和稳定回退，不能全部视为错误。\n'.format(
        cloth['simulation_vertices'], cloth['simulation_triangles'], cloth['pinned_vertices'], cloth['collision_capsules'],
        cloth['solver_iterations'], cloth['solver_substeps'], cloth['cloth_captured_display_vertices'], cloth['skin_only_display_vertices'])
    text += '\n构建与导入日志：\n\n' + '\n'.join('- `' + value + '`' for value in report['build_logs'].values()) + '\n'
    doc.write_text(text, encoding='utf-8')
    doc = PROJECT / 'Docs/Monsters/BlindSupplicantM07Meshy.md'
    text = doc.read_text(encoding='utf-8')
    old_para = next(line for line in text.splitlines() if line.startswith('**2026-10-02 当前显示模型及移动为'))
    text = text.replace(old_para, '**2026-10-02 当前为 [V18 全身动作与低成本背膜接触](BlindSupplicantM07BodyMotionV18.md)：左右横扫让非攻击手保持自然下垂，加入骨盆向前压重与胸肩跟进；重新制作慢走／追击的支撑、步频和全身配合。保留 V17 原显示几何、UV、83 骨参考、V16 手臂及 V17 腿部权重，重做原背膜臂侧接触代理，采用有限鳃骨避让与近距低密度布料。新版模型、代理／布料／LOD、四段动作及 AI/F6 蓝图已实际保存，原生默认引用与最终 Editor/Game 构建均已完成。未运行游戏或性能测试，由用户从 F6 重新生成测试。**')
    text = text.replace('的手臂权重和两段横扫继续沿用：', '的手臂权重继续沿用，横扫由 V18 接替：')
    text = text.replace('移动的骨盆、分段脊柱、胸肩及对侧摆臂编排保留于 V17，腿关节旋转由 V17 接替；', '移动已由 V18 重新编排，V17 的共同膝铰链与局部腿权重继续沿用；')
    text = text.replace('观察新保存的 V13 膝部、攻击姿态、鳃膜碰撞、跑姿及运行流畅度', '观察新保存的 V18 全身横扫、步态、鳃膜避让及运行流畅度')
    doc.write_text(text, encoding='utf-8')
    print('M07 V18 actual packages and Editor/Game binaries delivered; user testing pending.', flush=True)


if __name__ == '__main__':
    main()
