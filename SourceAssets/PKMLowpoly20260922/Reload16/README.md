# PKM 换弹动作修订 16

2026-09-23：根据用户反馈处理空仓多余的拨链动作、普通换弹左肘扭曲、枪体过于静止、右手拉栓接触不准确。

## 动作制作

- 空仓：保留开盖，1.10–1.40 秒将左手从开盖释放位置直接过渡到支撑位置，跳过旧弹链处理，随后换装弹箱。保留新弹链铺入和关盖、拉栓动作。基础时长由 7.5 秒缩短到 6.6 秒；普通换弹仍为 6.5 秒。
- 普通换弹：拨链区间重新求肩肘支撑，保留手掌及手指原有接触轨迹。前臂轴向旋转使用掌宽投影及骨架 rest-frame，辅助骨按完整 rest-local 关系重建，避免旧解算将腕部折弯叠入肘部扭转。
- 枪体运动：加入装卸弹箱时的缓慢重心偏移，以及接触、扣合、释放时的小幅衰减运动。枪体、双手和机械件使用同一整体变换，保持接触关系；动作首尾回到原位置。这是烘焙的动作反馈，不是刚体物理模拟。
- 右手拉栓：参考工程现有 AKM 装备拉栓动作的手型与朝向，再依据 PKM 拉机柄实际几何和 `PKM_Charge` 轨迹定位。食指／中指弯曲勾住拉机柄，手掌跟随拉动，释放后向外上方退开，再回到握持。
- 默认和 vertical、canted、prism、angled 四组握把均输出普通／空仓两段，共 10 段、120 Hz。战术垂直握把继续复用 vertical。模型、材质、静置骨架及蒙皮权重沿用现有版本。

## 来源与文件

- 默认制作源：`../Feed13/PKM_FiringFeed_Editable.blend` 中的 HandReload10 / Wrist12 换弹动作。
- 改造握把制作源：`../GripContact15/PKM_<family>_Editable.blend`。
- 视频动作参考沿用 `../References/PKM_UserReloadReference.mp4` 及 HandReload10 留存参考图。
- 拉栓手型参考：`SourceAssets/AKMIntegration20260910/EquipCharge/AKM_EquipCharge_Editable.blend` 的 `AKM_EquipCharge`。只借鉴手型与朝向，接触坐标按 PKM 重新求解。
- `author_reload.py`：统一动作制作；`PKM_<family>_Reload_Editable.blend`：本轮可编辑源；`Animations/`：导出 FBX。
- `sources.json`、`charge_fit.json`：制作所需源骨架／几何读数，不是游戏测试报告。
- `view_contacts.py` 与三张局部图：仅用于用户明确要求的肘部、拉栓接触问题排查，不代表完整动作或实机验收。

## 时序接入

空仓 2.30 秒及以后的源事件统一前移 0.90 秒。普通换弹不变。

| 事件 | 普通换弹 | 空仓换弹 |
| --- | ---: | ---: |
| 旧弹箱隐藏 | 3.20 | 2.30 |
| 新弹箱显示 | 3.55 | 2.65 |
| 弹箱装入 | 4.35 | 3.45 |
| 新弹链铺入阶段 | 5.10 | 4.20 |
| 关盖 | 5.72 | 4.82 |
| 拉栓接触 | — | 5.13 |
| 可用阶段 / 拉栓释放 | 5.72 | 5.55 |

空仓移除旧弹链音效，装箱、铺链、关盖、拉栓音效随对应动作前移。PKM 不再套用其他枪械的音效序号式冲击，避免与本轮烘焙枪体运动重复。

代码与数据：`PKMLowpolyWeaponAssets.h`、`WeaponReloadStages.cpp`、`FPSGAMECharacter.cpp`、`Content/ColdSteelData/gunsmith.json` 的 PKM 空仓基础时长。

## 游戏资产

覆盖既有资源路径，保留原枪械与配件路由：

- `/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload[_empty]`
- `/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/<family>/A_PKM_<family>_reload[_empty]`

通过 `Tools/AssetPipeline/mcp_call_codex.ps1` 的互斥队列导入；每个动作保存后记录在 `imported.json`。使用 PKM 私有 Skeleton 和既有 `BC_M4Viewmodel` 压缩设置。

普通换弹修改继续从本目录源文件开始；空仓右手拉栓与装备动作已由 `../EquipCharge31` 在本轮基础上继续精修，后续这两段使用该目录的作者源。不要用 GripContact15 / Accessories14 旧换弹导出覆盖后续修订。其余握持、开火、移动等动作仍以 GripContact15 为基底。

## 交付状态

- 必要原生构建完成：`build.log`，Result: Succeeded。
- 默认及四类握把共 10 段动作已导出并导入保存到既有游戏路径。导出记录为 `animations.json`，保存记录为 `imported.json`；普通动作 6.5 秒，空仓动作约 6.6 秒。
- 导入桥回执：`Saved/pkm16-import-base-02.txt`、`Saved/pkm16-import-vertical-01.txt`、`Saved/pkm16-import-canted-01.txt`、`Saved/pkm16-import-prism-01.txt`、`Saved/pkm16-import-angled-01.txt`。首次 base 请求在提交导入前因 Python 属性访问方式失败，改用现有工作流的 `set_editor_property` 后导入保存完成。
- 未启动 PIE 或执行游戏测试；实机动作效果交由用户测试。
