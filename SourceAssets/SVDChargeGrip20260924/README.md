# SVD 空仓换弹：参考当前 AKM 的右手拉栓手势

> 后续状态：用户反馈手势与镜头内手臂仍不合适。此版本已由 `../SVDChargeGrasp20260924/README.md` 所述抓握拉栓修正替代；本目录保留历史制作记录，当前五条正式空仓换弹已指向新版本。

用户于 2026-09-24 确认上一轮 SVD / PKM 快速近战修复成功，随后要求优化 SVD 空仓换弹拉栓手势，参考当前 AKM。本轮范围仅为 SVD 原厂及 vertical / canted / prism / angled 五条 `reload_empty`。

交付状态：2026-09-24 10:34 后台 commandlet 已导入并保存五个目标动画，记录 `SVD_CHARGE_IMPORT_COMPLETE 5`，进程退出码 0。可编辑源、FBX、运行资产和替换前备份均已落盘；尚未进行本轮游戏测试。

## 输入与调整

- 通过已有编辑器读取实际运行资产的导入来源，记录在 `runtime_inputs.json`。SVD 输入为 `SVDThumbUp20260923`；当前 AKM 参考为 `RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload_empty.blend`，不是按旧文件夹名猜测参考版本。
- SVD 旧拉栓手型来自 ASH12 / A762 的跨枪拟合。本轮采用当前 AKM 空仓换弹右手的整组手指姿态，包括接近、勾拉与松手三个阶段，保留手指骨长、局部位移、缩放和蒙皮。
- 按实际 AKM 和 SVD 拉机柄的外侧边缘、前侧受力面及高度配准整只手。没有将枪机骨原点当成拉柄接触点，也没有移动枪上的拉机柄模型来迁就手。
- 右手先离开后握把并沿外侧接近，接触后固定手与拉机柄的关系，随 SVD 原有 75 mm 行程后拉；后止点松指并向外退开，再回到原握姿。右肩肘跟随新腕位，整段大小臂及辅助骨协同旋转，沿用上一轮已接受的腕臂衔接方法。
- 只重写源帧 269–431 内的右臂和右手通道。其余动画通道沿用原 Action；普通换弹、左手装匣/回握、弹匣、整枪和机械轨道、瞄具、快速近战均不改。

## 时序与保存

120 Hz，源帧 0–515，总长约 4.291667 秒。保留原机械与声音合同：268 起势、310 开始后拉、344 后止及脱手、350 枪机闭合、432 回握。原厂和四种握把的末段继续回到各自已有姿态；不修改 C++、补弹业务、声音或游戏时钟。

实际运行路径保持不变：

- 原厂：`/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_reload_empty`
- 四种握把：`/Game/Weapons/SVDDragunov20260922/Accessories20260923/Animations/A_SVD_<family>_reload_empty`

制作与恢复入口：

- `prepare.py` / `pose_inputs.json`：提取当前参考动作和实际拉柄几何。
- `fit_contact.py` / `contact_fit.json`：AKM 手型与 SVD 拉柄接触配准。
- `author.py` / `authoring.json`：五份 `SVD_*_ChargeGrip.blend` 与 `Animations/*.fbx` 的制作及导出记录。
- `import_animations.py` / `run_import.ps1`：目标源版本和未保存状态保护、逐项备份、原路径导入保存。沿用原骨架、压缩和 root-motion 设置。
- `Before/Weapons/`：替换前的五个 UE 动画包。
- `import_receipt.json` / `import_commandlet.log`：实际保存回执和本次后台导入日志。

没有启动编辑器界面、游戏或 PIE，没有追加截图、渲染或运行时测试。最终游戏画面与手感由用户测试；源姿态读取及导入保存不代表视觉验收。
