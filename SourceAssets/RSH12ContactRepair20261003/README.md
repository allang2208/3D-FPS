# RSH-12 弹巢与逐发持弹接触

修复 Native715 第一版的估算吊臂轴心、被轴向投影抹掉的子弹轨迹、子弹与手分开插值的问题。保持原生 V7 手型、持枪侧动作、715 接触时钟和当前开巢镜头抖动。

制作顺序：

1. 后台 Blender 执行 `prepare_contacts.py -- single`，从完整混合蒙皮提取单持装填手的接触点。双持原生网格没有另一只装填手，不使用该提取步骤。
2. `mechanical_contract.json` 保存 `4_l` 下端实际圆形铰链的拟合轴心；`grip_registration.json` 沿用当前枪体握把配准。
3. 后台 Blender 执行 `author_contact.py -- single`、`-- r`、`-- l`，产生三套网格、可编辑 Blend 和 profile。
4. 使用现有桥／后台 commandlet 执行 `import_assets.py`，保存到当前 Native715 资产路径。没有 C++ 改动，不需要编译。

实际保存由 `import_receipt.json` 的 `revision=native-715-contact-v2`、`complete=true` 和 `saved` 列表记录；不是用 FBX 导出成功代替 UE 保存。旧源和资产保存在 `BeforeSource`、`BeforeAssets`，不要整目录覆盖并行修改。

制作阶段没有运行游戏、测试、试听或验收渲染。手部与机械观感由用户测试。
