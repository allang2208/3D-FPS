# 符文战锤、两款传说锤头与能量条整理发布

本次发布属于符文战锤这段制作及随后用户要求的联机修复，不包含工作区其他未提交的枪械、服装、怪物和技能功能。

## 发布内容与边界

- `Source/FPSGAME/Production`：原生苏醒、星誓爆震、镇魂刻印/终律魔伤、双重击时间合同及复制状态；`Development/RuneboundReview*` 为明确启用的审计夹具。
- 原路径发布符文材料应用、按武器寻址的改造表、物理/魔法附伤消费者及第三人称专属动作角色映射。
- 两份独立模块/改造数据直接提交。共享 `items.json`、战斗公式和 `player_body.json` 仅提交本武器与两个专属动作叶字段；Cook 仅新增本武器目录。
- `SourceAssets/RuneboundWarhammer20261022` 发布原创作者脚本、HLSL、标准图标提示词映射和必要的小型规格。完整模型、动作采样、图像和 UE 包按仓库许可规则留本机。
- `skills` 的武器、联机与 UI 对应部分记录可复用方法，个人技能同步更新。

当前共享组件、攻击事务和通用框架仍存在并行未发布差分。相关本次改动保存在 `Integration`，其 `integration-manifest.json` 记录基线 Git blob 或本机修改前 SHA-256。`initial-*` 为从指定 Git 基线挑出的本武器差量；其余 patch 针对本机已具备苏醒/战锤框架的初版镇魂钟前快照。组件 `owned-fragment.txt` 只是所属声明/接线的合并参考，不是可整文件覆盖的补丁。初版和终律差量有重叠，不要整目录盲目应用。

**这次是功能源与接入材料发布，不声明公共仓库干净检出可直接完整编译。** 本地完整工程已有接入并构建成功；独立重建还须合并 `ProductionToolComponent` 的战锤/权威前置、`ColdSteelAuthority` 影子档案、技能命中序号、共用改造字段和审计夹具依赖。未将这些其他任务的在途实现整文件带入本提交。需要独立可运行版本时先恢复相应既有发布批次及合法资产，再按清单合并，并在获授权时构建/测试。

## 本机保留的恢复资料

原始模型：用户提供 `Meshy_AI_Runebound_Warhammer_1022125957_texture.glb`，保存在 `Original`，本次授权推送没有另外核准原资产公开再分发。

- `ModulesV1` 的实际分件 Blend、接口采样和 FBX；`Original`、`Textures`、`Export` 及根可编辑模型。
- `StarOathHammerHeadV1`、`FinalTollHammerHeadV1` 的可编辑制作源、PBR、4K纹理和导出模型。
- `FinalTollIntegrationV1` 的第一人称动作 Blend/FBX、身体动作准备输入及实际 UE 动作包。
- `FactoryFramedIconsV2/Masters` 和两款传说改造正式 PNG；背包整把武器采用 `InventoryIconV2` 目录图。
- `/Game/Weapons/RuneboundWarhammer20261022` 已安装包；现有双手锤手臂/骨架、Jason/Kaitlin 全身供体和通用改造资产。
- V3 HUD 仍使用 `PassiveV1/RuneboundEnergyHud.hlsl` 的 V2 源、`HudMotesV2/install_assets.py`、苍龙 `HudV10` 的布局和纹理；这些不是废案。

恢复时先准备原始模型及手臂/身体供体，再运行分件与各模型作者脚本、材质/动作导入器，最后合并运行配方、共享消费者和精确动作键。导入宿主为可再生临时工程；当前已保存资源不依赖它继续存在。图标母图需要从已许可本机备份恢复，公开提示词不等同于实际图像。

## 归档

`trash/RuneboundWarhammer20261023/manifest.json` 在本机记录543份文件的原路径、目标路径、大小、SHA-256、理由和保留替代物，共1,347,807,282字节。内容是修改前快照、旧错误图标、重复导入宿主、一次性初版改码器/结束PIE脚本和已被成功结果取代的探针/失败日志。移动前后已核对散列，未删除运行资源和当前模型母版。`trash`、完整旧快照及日志不进入 Git。

需要取回补丁基线时，按本机归档清单恢复对应文件到临时位置进行三方合并，不能把旧完整配置或暂存裁剪版本覆盖真实工作文件。

## 已有证据

用户此前明确要求排错时已运行的资源检查73项、隔离服务端用例37项及一次真实本机 UDP Listen Host/Client 测试均通过。`authority-results.json`、`asset-results.json` 与 `wire-results.json` 保存摘要；完整日志在本机 `NetworkReview20261023`。网络夹具使用原始伤害目标、关闭移动和世界身体渲染，验证原生 RPC、接触计时、复制状态和消费回执，不能代替真实怪物护甲或视觉验收。

完整本机 Game / Editor 构建成功。此次整理与技能更新没有重跑游戏、截图、渲染或回归；第三人称观感、粒子亮度/飘散和顶部端帽视觉仍由用户在游戏内确认。详细范围见 [复查报告](../../Weapons/runebound-network-review-20261023.md)。本地资产落盘、Git 提交、远端推送和用户视觉认可分别记录。
