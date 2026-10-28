# 截顶拼接立体狼头

按用户最新截图修改：切掉原上方尖顶和旧狼纹，保留原玻璃柱下段、底部尖锥与红色流光。螺旋符文带后续改为同轨迹的红色螺旋粒子流。活动源是本目录；`RuneRelief/` 的原线稿浮雕方案已被替代。

## 苍龙参考

读取 `ue5-weapon-workflow/references/azure-dragon-pending.md`、`asset-model-workflow/references/visual-cases.md` 和工程 `Docs/Combat/enchant-azure-dragon-v10-20261006.md`。采用最终 `HudV10` 的参考图分层法：保留原设计图中的体积明暗，通过 UI 半透明材质和覆盖率遮挡亮场景背景。历史 `ReferenceV7` 只作经验参考，不恢复已退役方案。

## 设计与接入

- `Art/WolfHead_Crown.png`：内置 imagegen 生成的透明设计图／生产素材；暗血红水晶狼头，明确的吻部、眼窝、獠牙和高光。原图直接接入，不再重绘成细线。
- `prompts.json`：完整设计提示词和接座局部调整提示词，工具为 built-in imagegen。
- 按接座实际横截面定比例，等比缩放；柱身截点位于 HUD 像素 Y=480，狼头接座与柱体重叠约19像素，原尖顶完全裁去。
- 狼头耳尖位于现有 HUD 可见顶部之内；不改全局 HUD 摆位，不影响苍龙、符文战锤或狂战士数值。
- 保留狼头的原 RGB 明暗，用实际 Alpha 接入，暗面能够遮住场景；充能只加强原红色脉络，不把整张图压成单色发光轮廓。
- 这是一张带立体明暗的设计图拼接到屏幕 HUD，属于2.5D呈现，不是新增世界空间狼头网格。

`compose_head.py` 生成 HLSL 与 `head-layout.json`；`install_head.py` 实际保存纹理与现用 `M_BerserkerEnergyHud`。`install-receipt.json` 的 `complete:true` 表示完成导入保存。未主动运行游戏验收，实机观感由用户确认。

## 用户要求的游戏截图

后续已按用户“看一下游戏中效果图”启动 PIE，进入原有角色与场景截图，未更换装备或修改存档字段。实际画面为 `Preview/berserker-in-game.png`，可看到截顶后的狼头、原玻璃柱和螺旋符文。截图后结束本次 PIE，保留编辑器及非本任务的未保存资产。该预览同时发现并修复六款刀身材质的顶点／像素阶段连接错误；不是完整战斗或联机验收。

## 同轨迹螺旋粒子

- `HelixParticles.hlsl` 替换原实体符文带：保持半径160、每圈高度384、2.72圈和每秒0.45弧度旋转；两条紧邻原中心线的错列粒子流带有亮核、短尾、轻微浮动与明暗呼吸。
- 每像素只计算12个邻近候选，复用现有HUD材质；没有新增世界粒子组件、纹理或角色Tick。
- `HelixDrift.hlsl` 复用原32枚环境粒子中的22枚，从螺旋轨迹出生，向外飘散、上浮并淡出；其余10枚狼头聚光粒子保留。前后层明暗区分保留缠绕感。
- `compose_head.py` 同时生成狼头拼接与粒子版本；完整导入仍使用 `install_head.py`。仅更新此次材质可运行 `install-queued.ps1 -PythonName install_particles.py -CompileShaders`，后台使用桌面渲染RHI完成材质编译，不启动游戏。
- 增量落盘回执为 `particle-install-receipt.json`，只有 `complete:true` 表示实际保存。上述旧游戏截图不包含这次粒子更新；本轮不另行启动游戏或截图，由用户确认实机效果。
