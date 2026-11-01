# M24 脚架 0.48 秒简化版

已合并重复的无镜选项：保留标准 `none` ID，显示名为「M24 觇孔机械瞄具」。旧存档的 `m24_palma_iron` 选择由原生 Normalize 迁移到 `none`，继续显示原机械瞄具。

左手只抓近侧支腿并一次拉开双腿：0.12 秒接触，0.30 秒展开锁止，0.44 秒回握，0.48 秒完成架设。删除原来的跨枪换腿过程，重新制作连续外下侧手掌轨迹与手指松紧时点；保留 V9 固定臂长 IK、前臂扭转分配及原枪体/右手基准。部署、收起、手部采样与音效使用同一时钟。

`install_receipt.json` 记录已保存的 5 发、10 发动作和配置资产。`Before/` 是本轮修改前的源文件与资产备份。

2026-10-29 16:46:41，现有编辑器 Live Coding 成功；证据为 `Saved/Logs/FPSGAME.log` 中本次 `M24_QUICK048_COMPILE_BEGIN` 到 `M24_QUICK048_COMPILE_RETURNED` 之间的 `Live coding succeeded`。没有启动新编辑器或新的 PIE。

用户保存并关闭编辑器后，使用当前模块响应文件重新编译三个修改单元并链接，已替换项目的基础 DLL、PDB 和对应对象文件。`Build/build-receipt.json` 的 `published: true` 记录本次落盘成功；旧 DLL 保存在 `Build/Backups/`。本次使用 `SourceAssets/M24DualOptic20261029/build_incremental.ps1`，未重新打开编辑器或启动游戏。

本轮未执行运行测试、渲染预览或联机验收；之前 `../Review/` 的检查记录属于旧版 2.40 秒动作。
