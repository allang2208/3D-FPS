# 整机死机后的地牢土石恢复记录 / 2026-09-21

用户反馈整台电脑死机，发生步骤不确定。本轮范围是续接已经完成的 Fab 土石改造，暂不重做整套资产，也不据此改动硬件、渲染配置或其他场景。

## 已找到的保存状态

- `Content/GameMaps/L_Dungeon_Prototype.umap` 保存于 15:29:47，文件仍在。
- `SourceAssets/DungeonRuinEarthwork20260921/Receipts/scene-install.json` 为 `map_saved`，包含 40 个新摆放和 5 个保留隐藏的旧摆放。
- 旧编辑器日志 `FPSGAME-backup-2026.09.21-08.32.43.log` 中，15:29:47 存在 `RUIN_EARTHWORK_MAP_SAVED 40 actors; former banks retained hidden`。
- 导入回执中的 40 个网格和 6 个材质实例文件均存在且非空，保存时间为 15:28:14–15:28:29。文件存在不能代替场景内加载结果。
- 未找到今天的项目崩溃目录，也未从今天的 System 事件 41、6008、4101 查询得到事件。现有证据不能确定整机死机原因。

## 当前接入状态

首次尝试接入时已有 UE 编辑器正在运行 `DayNight_Lighting`，当时保留该次运行。用户随后明确授权“结束运行，恢复地牢”。再次接入时运行已结束，恢复脚本于 18:26 将编辑器切回 `/Game/GameMaps/L_Dungeon_Prototype`。

新会话读取到全部 40 个新摆放，网格、材质、可见性及碰撞配置与配方一致。但 5 个应保留隐藏的旧土堆重新可见，Actor 碰撞也重新开启。原安装脚本调用运行时的隐藏/碰撞 setter，未对旧 Actor 及组件调用 `modify()`；既有外部 Actor 包未被标记为需保存。UE 的 `SaveExternalPackages` 会筛选需保存的包，因此仅保存关卡不足以持久化这些修改。这是本次找到的场景状态保存问题，不是已确定的整机死机原因。

18:28 完成以下恢复并成功保存关卡：

- 对 5 个旧土堆及其组件调用 `modify()`，重新隐藏并关闭 Actor 碰撞，保留旧资产作为回退资料。
- 保留原有 40 个新摆放，没有重新导入、生成或运行全量 V2 重建。
- 同步修正 `Scripts/install_earthwork.py`，新旧摆放修改均显式标记 Actor/组件需要保存。
- 将编辑器视角放在遗迹入口。

本次入口为 `Scripts/resume_dungeon_editor.py`、`read_recovery_state.py` 和 `restore_hidden_banks.py`。读取记录为 `Receipts/recovery-state-20260921-182634.json`，保存回执为 `Receipts/recovery-restored.json`，阶段 `map_saved`。

地牢编辑现场已恢复。本轮未启动游戏、未进行性能/碰撞测试、未截图，也未另行重启验证；实际效果由用户测试。
