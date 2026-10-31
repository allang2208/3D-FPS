from pathlib import Path
import json
R=Path(__file__).resolve().parent;ROOT=R.parent;PROJECT=R.parents[3]
installed=json.loads((R/'installed.json').read_text('utf8'));retired=json.loads((R/'retired.json').read_text('utf8'));entries=json.loads((R/'retired-entries.json').read_text('utf8'))
if installed['stage']!='formal_apartment_saved' or retired['stage']!='sample_map_retired':raise RuntimeError('Integration/retirement is not complete')
summary=dict(stage='integrated_and_sample_retired',map=installed['map'],saved_at=installed['saved_at'],new_mesh_actors=len(installed['created']),replaced_mesh_actors=len(installed['updated']),furniture_layout_updates=len(installed['layout']),reading_lights=len(installed['lights']),retired_map=retired['retired_map'],retired_files=retired['files'],retired_entries=len(entries),game_tested=False,new_editor_started=False)
(R/'completed.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
text=f'''# 赛博朋克卧室：正式接入与试点退役

卧室 V3 已接入现有公寓 `{installed['map']}`，保存于 {installed['saved_at']}。
本次在现有公寓内局部替换，不用试点整图覆盖正式关卡。

- 安装 {len(installed['created'])} 组卧室陈设，替换原卧室床体引用；使用已保存的 V3 网格、材质和物理 UV 校准实例。
- 同步 {len(installed['layout'])} 个原有家具/附属 Actor 的已修正布局；储物 ID、柜门、电脑设备关联和床休息配置沿用现有身份。
- 两盏阅读灯接入现有 `AP7_Atmosphere` 的 Bed2 调度；保留其他灯光绑定、V21 时钟、其他房间、海湾和正式出生点。
- 已移除独立试点地图 `/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024`。退役地图归档在 `trash/cyberpunk-bedroom-pilot-retired-20261024/`，不再位于 Content 中，不作为第二套可运行场景。
- 旧试点安装入口已改为正式公寓入口，完整公寓的 V21 恢复链末尾也注册了卧室接入，避免重建后退回旧床或恢复测试地图。
- 保留正式公寓依赖的网格、材质、贴图与 Blender 制作源。目录中的 `BedroomPilot20261024` 是历史资产/制作源标识，不再对应独立测试场景。

当前唯一使用入口：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

## 制作入口与记录

- 局部安装：`SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/Integration20261024/install_level.py`
- 资产制作/发布：`BedroomPilot20261024/publish.py`，使用当前 V3 制作源并接入正式公寓。
- `approved-bedroom.json` 保存迁入的布局、材质、碰撞和灯具配置；不依赖退役地图继续存在。
- `installed.json` 记录正式地图保存；`retired.json` 记录退役文件及 SHA-256；`retired-entries.json` 记录停用的旧安装入口；`completed.json` 为本轮完成汇总。

本次仅完成接入、保存和清理，没有启动游戏或追加测试；实际游戏体验由用户测试。
'''
(PROJECT/'Docs/CyberpunkBedroom-Integration-20261024.md').write_text(text,encoding='utf8')
(R/'README.md').write_text(text,encoding='utf8')
notice='> **已正式接入现有公寓，独立试点已退役。** 当前入口为 `open /Game/GameMaps/L_CyberpunkApartment`；下文保留当时的制作记录。正式接入记录见 `Docs/CyberpunkBedroom-Integration-20261024.md`。\n\n'
for p in [ROOT/'README.md',ROOT/'RefinementV2/README.md',ROOT/'RefinementV3/README.md',PROJECT/'Docs/CyberpunkBedroom-Pilot20261024.md',PROJECT/'Docs/CyberpunkBedroom-PilotV2-20261024.md',PROJECT/'Docs/CyberpunkBedroom-PilotV3-20261024.md']:
    old=p.read_text('utf8');header,body=old.split('\n',1)
    body=body.replace('open /Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024','open /Game/GameMaps/L_CyberpunkApartment')
    if notice.strip() not in body:body='\n'+notice+body.lstrip('\n')
    p.write_text(header+'\n'+body,encoding='utf8')
p=PROJECT/'Docs/CyberpunkApartment-POSITION-AND-TODO.md';old=p.read_text('utf8');header,body=old.split('\n',1)
line='> 卧室 V3 已正式接入此公寓，独立试点已退役；见 [卧室正式接入记录](CyberpunkBedroom-Integration-20261024.md)。\n\n'
if line not in body:p.write_text(header+'\n\n'+line+body.lstrip('\n'),encoding='utf8')
print(json.dumps(summary,ensure_ascii=False))
