# 焚化炉接入状态（2026-10-06）

本轮已完成模型资产导入和功能/UI 源码接入。**完整编译被另一处角色代码阻塞，销毁事务及面板运行测试尚未执行；不能视为游戏功能验收通过。**

## 已保存的资产

- 独立构件 ID：`incinerator`；网格：`/Game/Building/Incinerator20261006/SM_Incinerator`。
- 云端源包和可编辑 Blender、三级 FBX 保存在 `SourceAssets/Incinerator20261006/CloudModel/`。
- UE 实测包围盒尺寸 119.30 × 110.1911 × 207.90 cm，占位 6 × 6 × 11 个 20 cm 格；垂直偏移 -6.050003 cm，底面贴地。
- LOD0/1/2 三角面 40152 / 20076 / 8029；屏幕阈值 1.0 / 0.45 / 0.18；Nanite 关闭，仅对本资产设置。
- 13 个显式 PBR 材质、13 个材质槽；每级 LOD 的 13 个 section 重新加载后分别引用 0–12。LOD 导入产生的同名重复槽已按名称映射归并。
- 1 个 26-DOP 凸包碰撞，`UseSimpleAndComplex`。UE 的 `get_simple_collision_count` 不含凸包，故回执分别记录普通原语数量 0 和凸包数量 1。
- 调色板只新增焚化炉条目，`Surface=None` 保留槽 0 的黑色底脚；重载核对原有全部条目一致，含枪械工作台偏移。
- 新增隔离测试图 `/Game/Tests/Incinerator20261006/L_IncineratorAudit`，仅含地面、出生点和灯光等 6 个 Actor。测试代码运行时通过建造 API 放置炉体；未改默认地图，也未保存现有地图。

## 已写入、未编译验证的实现

- `ColdSteelIncineration.*`：按物品实例或弹药袋条目选择数量，先生成确认快照，再检查存档代次和完整实例内容，最后通过既有双槽持久化事务扣除。重复确认、过期状态、无效数量和失败保存不会继续扣除。
- `ColdSteelIncineratorWidget.*`：Cold Steel 玻璃面板、4 类来源筛选、搜索、数量调整、确认清单和不可恢复提示；列表虚拟化、库存事件刷新、无每帧 JSON 解析。
- 通过既有工作台 E 交互与 HUD 动画流程打开/关闭，恢复鼠标和移动/视角输入；关闭或炉体失效时丢弃待确认内容。
- 可处理随身、装备、主仓库、背包夹层以及弹药袋中的物品；箱内物品须先取出，未领取工件须先领取。背包仍装有夹层或扩展格物品时阻止销毁，列出阻塞物品，不级联销毁。
- 已装填弹药、配件、强化和附魔随选中实例消失；确认页列明，不返还材料或弹药。没有配方、产出或返还系统。
- 显式开关控制的事务 commandlet 与 UI 自动化已写入，使用独立档案和重定向 Saved 路径。未启动这些运行测试。

## 实际验证与阻塞

2026-10-06 10:27 UTC 后执行完整 `FPSGAMEEditor Win64 Development` 构建，UHT 报错：

```text
Source/FPSGAME/FPSGAMECharacter.h(850): Error: Replicated sets are not supported.
UPROPERTY(Replicated) TSet<FName> DoorKeys;
```

这处钥匙环字段不在焚化炉改动范围，本轮未改动。编译在新代码进入编译器前失败，故没有复用旧二进制声称功能通过。未运行 PIE/游戏、未产生真实焚化炉 UI 截图，也没有截图 Library 文件 ID。

资产导入与新进程重载核对通过；这证明保存结构与引用，不代表实际渲染或交互验收。源码范围 `git diff --check` 通过。任务前后的 1648 个已有 `.sav`、112 个已有 `.umap`、6 个默认 `.ini` 全部哈希一致；原枪械工作台网格 SHA256 仍为 `32dce97e44ed9c187ce50347881ff48dc4a2019a69675200952747db914697a1`。

## 继续测试的入口

先由相关代码处理上述编译错误，再完整构建焚化炉改动。不要关闭/覆盖其他任务的编辑器或把旧二进制当作本次验证。

本机工作记录目录：`C:/Users/allan/Documents/Codex/2026-10-04/task-2/incinerator_20261006/`。

1. `build.ps1`：完整构建，拒绝与现有编辑器/编译进程并行。
2. `run_isolated_tests.ps1 -Stage Transactions`：独立 Saved 根与唯一档案，检查取消、部分扣除、重复点击、存档失败、过期快照、弹药、枪械附属内容、背包限制等；必须先有本轮成功构建回执。
3. 上一步通过后执行 `run_isolated_tests.ps1 -Stage UI`：仅进入新隔离图，测试 E 打开、确认/取消、重复操作、关闭恢复，并请求真实运行截图。它驱动实际 UI 回调，不能冒称人工鼠标验收。
4. 检查运行日志、报告、截图和真实存档前后哈希；实际通过后再更新本记录。

备份与证据：`Before/`、`BeforeAssets/`、`asset_backup.json`、`published_code.json`、`build.log`、`import_attempt1.log`、`import.log`、`verify_map.log`、`ue_import_receipt.json`、`fixture_receipt.json`、`completion_audit.json`。没有提交或推送 Git。
