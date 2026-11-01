# M24 装备仅拉栓，2026-10-28

按用户新要求，移除装备的抬枪、握匣和压匣段，只保留上一版源帧 48–106 的拉栓动作及其现有进出衔接，时长 58/30 秒（约 1.93 秒）。开栓／闭栓音效改到 25/30、40/30 秒，删除装备压匣音效。

两种弹匣共用这一装备序列，左手始终扶枪。四种换弹及其抓匣修正保持原样；不改枪械安装位置、模型、ADS、战术冲刺或射击动作。

作者文件为 `M24_EquipBoltOnly_Editable.blend`，导出为 `Export/A_M24_equip.fbx`。正式动画继续使用 `/Game/Weapons/M24/MotionMagazine20261027/Animations/A_M24_equip`；两个当前握持 Profile 仅替换 equip 项的时长并清空旧压匣差量，其他项按当前内容保留。

执行：`run_assets.ps1 -Stage install` 保存目标动画与两个 Profile；`build.ps1` 进行必要构建。实际完成状态见 `install_receipt.json` 和 `build-receipt.json`。未主动运行游戏、渲染或验收，由用户试玩确认。
