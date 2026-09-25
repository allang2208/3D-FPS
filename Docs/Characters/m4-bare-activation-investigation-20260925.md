# M4 裸手进游戏仍显示手套：定位中

用户在 V6 落盘后反馈 M4 仍显示原手套。本轮尚未确认最终拦截点，也没有宣布修复完成。

## 已读取的状态

- `modular_outfits.json` 的 M4 原始网格精确路径仍指向 `OriginalShapeBareM4BareArmsV6/SK_M4_OriginalShape_BareHands`；V6 网格文件保存于 2026-09-25 00:54:22。
- MCP 所在编辑器 PID 116000 中 `fps.Outfit.BareArmsCandidate=1`，`fps.body.WorldBodySuppress=0`，角色默认对象包含 `ModularOutfit` 组件。
- 只读查看 `ColdSteelPlayer_A/B.sav` 的物品字段：M4 在装备栏（Place=1，Cell=6），原版战术手套及模块手套／上衣均在背包（Place=0）。没有修改存档或装备状态。
- 原生基础 DLL 中存在 `bare_arms_candidate`、`candidate_active` 与裸手开关字符串；不是只有旧热补丁而完全缺少该分支。

## 两个编辑器实例的区别

MCP 连接的是旧编辑器 PID 116000，其日志是 `Saved/Logs/FPSGAME.log`。用户测试发生在另一编辑器，日志是 `FPSGAME_2.log`；该实例的 MCP 因 8000 端口已占用而绑定失败。

`FPSGAME_2.log` 记录：01:05:24 开始 PIE，01:05:28 加载 M4 原始网格，01:05:59 等待 `SK_M4_OriginalShape_BareHands` 就绪，01:06:28～30 因显存不足崩溃。之前的 `FPSGAME_2-backup-2026.09.24-16.59.42.log` 也记录裸手网格等待和后续显存崩溃。不能据此证明裸手已经替换成功，或把显存不足直接断言为手套仍显示的唯一原因。

因此，在用户回复“已进入”后读取到的 `playing=false` 属于仍存活的旧编辑器，而不是用户测试中的角色。没有结束任何编辑器或自动启动游戏。

## 下一步

已请用户在仍运行的 PID 116000 编辑器窗口中进入 M4 游戏并保持画面，避免再开第二个实例。随后通过已有串行桥执行：

`Tools/ModularOutfit/read_m4_bare_activation.py`

脚本读取当前玩家的 M4／模块手臂组件、可见性、OnlyOwnerSee、OwnerNoSee、父节点、材质和 LOD0 section 显示状态，输出到 `Saved/M4BareActivation20260925/diagnosis.json`；桥输出必须使用新的文件名。已有 read-01～05，不覆盖。

重点区分：没有创建替换组件、候选资源尚未就绪、原手模区没有隐藏、替换组件被隐藏或材质不正确。不要在没有实际角色证据时改模型、存档或第三人称逻辑。
