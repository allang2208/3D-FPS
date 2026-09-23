# PKM 视频装备动作与空仓右手拉栓

后续：空仓右手与拉柄往返已由 `../Charge34/README.md` 的后拉／手动前推版本继续修订；本目录仍是装备动作来源，下文保留第 31 版制作记录。

2026-09-23。范围：装备动作及空仓换弹末段右手，不重新制作其它换弹阶段或模型。制作依据为已保存在本机的用户视频 `../References/PKM_UserReloadReference.mp4`。

## 视频观察与适配

本轮解码并查看 0–4 秒与 23.4–26.4 秒的密集参考帧，记录在 `equip_reference.jpg`、`charge_reference.jpg`。装备实际参考 0–0.85 秒：枪口朝上带入，左手张开接住前部，随后整枪压回待机，末段短暂回稳；此段未见独立拉栓，不额外添加装备拉栓。2.2 秒以后是另一次动作，未混入装备。

空仓末段参考约 23.85–25.4 秒：关盖后右手进入枪侧工作，再释放并回握。拉柄局部被枪体和手遮挡，其深度与指腹接触按当前 PKM 几何适配；不宣称从单视角视频恢复了不可见的三维轨道。

## 动作制作

- 从 `Reload16/PKM_<family>_Reload_Editable.blend` 继续制作，仅输出 equip 与 reload_empty。默认、vertical、canted、prism、angled 共十段；战术垂直握把沿用 vertical 路由。
- 装备：0.90 秒，枪口朝上入场，左手提前张指并从外侧接握，右手保留后握把接触，约 0.86 秒回到本握把的原待机。整枪曲线采用连续速度的 Hermite 插值；末段有限超调并收稳。肩肘按固定骨长求可达姿态，辅助骨跟随完整骨段。
- 空仓拉栓：保持 6.6 秒时长与全部机械件、左手、枪身反馈及补弹时序；只修改 4.82–6.30 秒右臂。沿用现有 AKM 原生右手拉栓指节姿态，再按 PKM 的侧上方接近方向和实际外侧拉柄定位，不复制其它枪的接触坐标。
- 接触锚点来自当前共用手套食指/中指的指腹顶点，取代原来的指骨中心点。保留掌骨及拇指姿态，以整手变换配准，不平移指骨、不缩放手掌。
- 5.13–5.515 秒跟随拉柄；释放时先开指，沿外上方退出，再收回后握把。脱离后手腕以拉柄后止点相对枪根的位置为起点，不跟随已松开的拉柄快速复位。
- 肩、肘、前臂、腕和辅助骨在同一求解中衔接，避免只转腕或让辅助骨分数扭转。四元数保持连续符号，按 120 Hz 导出。

## 游戏接入

- 沿用原有 `/Animations/A_PKM_equip`、`A_PKM_reload_empty` 和 `Accessories14/Animations/<family>/` 对应路径，保留各握把选择与现有 PKM 私有 Skeleton。
- `FPSGAMECharacter.cpp`：PKM 装备使用自身片段时长，不再压缩为通用 M4 的 0.72 秒；从下方入场的装备片段使用完整动作权重，避免混入可见 idle 缩短抬枪轨迹；装备不套用 M4 拉柄专用镜头冲击。
- 现有空仓拉栓音效仍使用 5.13 / 5.55 秒源时钟，普通换弹、弹药结算、空仓省略余链动作保持。
- 本轮不重导枪械/手臂网格，不改手套、AmmoBox30 绿色弹箱、枪钢、雨滴、脚架或模型蒙皮。

## 文件与状态

- `read_reference.py`：用户视频解码；参考帧仅用于本机制作，不再分发。
- `read_authoring.py`、`authoring_inputs.json`：源动作和几何制作输入。
- `author_actions.py`、`PKM_<family>_EquipCharge_Editable.blend`：作者入口与可编辑动作。
- `Animations/`、`animations.json`、`authoring.json`：FBX、片段时间与接触参数。
- `import_actions.py`：后台或已有编辑器桥导入保存；备份现有十段目标动画，仅覆盖这十段。

已完成十段动画的后台导出、正式导入与保存，`import_receipt.json` 记录五类握持的装备 0.90 秒、空仓 6.60 秒片段。后台 Python commandlet 退出码 0，日志为 `import_background.log`、`import_console.log`；此前动画保留于 `BeforeImport/`。

`FPSGAMEEditor Win64 Development` 原生后台构建成功，退出码 0，耗时 10.98 秒；日志为 `build_editor.log`、`build_console.log`。没有执行游戏测试、验收渲染或启动交互式编辑器，动作观感、连续接触和游戏中各握把效果仍由用户确认。
