# RSH-12 握持与拨锤制作源（暂停）

2026-10-03 用户暂停。最新源码与 UE 已保存资产不同版，先读工程 `Docs/Weapons/rsh12-grip-cock-fix-20261003.md`、`Docs/Weapons/rsh12-pause-publication-20261003.md` 和 `Docs/Backlog.md`。

`native_{single,r,l}.json` 与 `BeforeAuthored/Integration` 的原始绑定／profile 是绝对拟合所需输入，保留本机。`hand_contact_*`、`cock_contact_*`、`trigger_contact_*` 是当前候选参数；完整原生蒙皮、供体动作和模型不公开。

持枪源入口为相邻 `RSH12Integration20261003/author_rsh12.py`，专用开火源为 `RSH12SingleAction20261003/author_single_action.py`。最新静态候选已导出，最新开火源尚未全部烘焙；过时四条 FBX／Blend 和三个单动 profile 已移入 trash，继续制作后需重新生成。

`import_receipt.json` 是初版十个资产的历史保存回执，没有最新 revision。`import_grip_assets.py` 中 `registered-mechanical-axes-v3-full-skin` 只是当前脚本标识，不代表已经保存。先完成制作再进行下一次导入。

`BeforeAssets`、`BeforeAuthored`、`BeforeSource` 及历史导入回执保留恢复边界。构建日志 02／03 仅说明原生源码构建状态。暂停整理不启动 UE 或游戏，不追加动作测试。
