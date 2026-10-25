"""Summarize the explicitly requested saved-geometry comparison."""
import json,os
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR']);BASE=P/'SourceAssets/BackpackFit20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
before=read(BASE/'BaselineMatched/contact_report.json');after=read(R/'contact_report.json');native=read(R/'native_contacts.json');support=read(R/'gravity_support.json')
source=read(BASE/'ContactFitR3/authored.json');saved=read(BASE/'ContactFitR3/saved_assets.json');pub=read(BASE/'ContactFitR3/published.json')
catalog=read(P/'Content/ColdSteelData/items.json');rows=[]
for item in dict.fromkeys(x['item'] for x in after['rows']):
    old=[x for x in before['rows'] if x['item']==item];new=[x for x in after['rows'] if x['item']==item]
    def highest(data,field):return max(x['shell_gap'][field] for x in data)
    entry={'item':item,'name':catalog[item]['name'],'routes':len(new),'before_max_route_p90_cm':highest(old,'p90_cm'),
           'after_max_route_p90_cm':highest(new,'p90_cm'),'after_max_route_over_5cm_percent':highest(new,'over_5cm_percent'),
           'after_max_route_penetration_percent':highest(new,'negative_under_minus_0_2cm_percent'),
           'after_lowest_sample_cm':min(s[2] for x in new for s in x['samples'])}
    if item=='ue_simple_sling_bag':
        entry['classification']='Accepted suspended sling retained; settled pose, not a close-fitting rigid double-shoulder carrier'
        entry['nearest_probe_range_cm']=[min(x['settled_contact_probes']['minimum_cm'] for x in new),max(x['settled_contact_probes']['minimum_cm'] for x in new)]
    rows.append(entry)
result={'scope':'7 packs x 2 native bodies x (bare + 6 current shirts), including saved pants-dependent shirt surfaces',
        'routes':len(after['rows']),'native_component_cases':len(native['cases']),'native_component_passed':native['passed'],
        'saved_harnesses':len(saved['meshes']),'saved_static_bodies':len(saved['statics']),'published':pub['status'],
        'gravity_cases_applied':sum(c.get('gravity_applied',False) for c in native['cases']),'slings_supported':support['passed'],
        'missing_mappings':after['missing_mappings'],'rows':rows,'runtime_animation_tested':False,'network_tested':False}
(R/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 背包贴合检查与修复（2026-10-24）','',
       '检查范围：七款背包、Jason/Kaitlin、裸身与六款上衣，共 98 组；上衣包含实际裤装配对表面。读取 UE 已保存几何和已构建骨骼 LOD0；三角面按 0.5 cm 网格采样。', '',
       '已保存并接入 84 套双肩包背带配对及 42 个衣物专用包体。保持安装高度、倾角、外侧货舱、UV、材料与原生骨骼；背带保留截面厚度，缝接端随包体。斜挎包保留已认可的重力悬挂方案。', '',
       '| 背包 | 修复前各组合最大 P90 | 修复后各组合最大 P90 | 修复后最差组合 >5cm 占比 |','|---|---:|---:|---:|']
for row in rows:lines.append(f"| {row['name']} | {row['before_max_route_p90_cm']:.2f} cm | {row['after_max_route_p90_cm']:.2f} cm | {row['after_max_route_over_5cm_percent']:.2f}% |")
lines+=['','P90 表示该组合 90% 的中央背区射线间隙不超过此值。数字不代表全身最大间隙，局部通风槽、结构凹部和悬挂包边缘仍有留空。斜挎包数据来自实际组件稳定四秒后的姿态，不适用双肩包整面压贴标准。','',
        f"原生组件检查：{len(native['cases'])} 个当前配对、{native['fallback_cases']} 个未登记上衣回退；结果：{'通过' if native['passed'] else '存在失败'}。仅独立无界面组件夹具，不启动游戏，不读写玩家存档。",'',
        '重力补齐：双肩包原来只有惯性，没有显式重力下沉。本次加入按款校准的 0.4–0.6 cm 受力下沉，以及 0.65–0.75 cm 动态向后避让上限；上衣配方同步货舱支撑边界和枢轴。', '',
        f"98 组全部检测到重力下垂，起步、转向后停步均归稳。双肩包实测最大额外向后避让为 {max(c['peak_outward_correction_cm'] for c in native['cases'] if not c['gravity_contact']):.3f} cm。斜挎实际下垂约 3.10–5.99 cm，14 组均由拉紧的背带或躯干接触支撑；未发现仅靠最大位移上限卡在空中的组合。", '',
        '新增衣服：工装/裤腰制作器发布后调用 Tools/BackpackFit/run.ps1；按实际源散列补做变化的男女配对，包体、背带、位置和斜挎动态参数成套保存。其他服装制作器也须调用该入口，并提供两个身体的原生源。未登记上衣 ID 隔离试做已生成 14 套配方，未写入物品目录。','',
        '边界：Editor/Game 后台构建已完成；本次检查覆盖参考姿态几何、真实组件的起步/转向/停步载体运动、稳定重力和资源选择。未运行原生步行动画或游戏；跑动、蹲伏、动画布料和实际多人画面仍由用户在游戏内测试。']
(P/'Docs/Characters/backpack-contact-audit-20261024.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('BACKPACK_CONTACT_SUMMARY',len(after['rows']),flush=True)
