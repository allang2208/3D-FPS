# M24 装备直接拉栓

按用户 2026-10-31 要求，去除装备时拉栓前侧向调整枪械的多余动作。

当前装备仍使用 `MotionMagazine20261027/Animations/A_M24_equip`。旧 EquipBoltOnly 源保留了原 cycle 的整枪侧摆与抬转；本轮读取当前序列与当前两套握持 Profile 后，在装备条目中将枪根固定到本枪的当前腰射待机位置和朝向。

双手相对枪身的原有握栓、拉栓和回握关系一起迁移。肩部沿当前待机锚点，使用原生上臂/前臂长度重新解算腕肘，twist_01 / twist_02 依现有 100% / 50% 分配；不通过缩放手臂完成接触。手指局部轨道保留当前版本。整枪不再先侧摆，拉栓过程结束后衔接当前待机。

仅修改两份生产 Profile 的 equip 条目，保留它们最新的其他动作与并行修改：

- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip`
- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_Mag10`

总时长仍为 58/30 秒；后拉/闭锁音效仍为 25/30、40/30 秒。枪栓、弹匣等局部机械行程及其他动作不重定时。没有重新导入枪械/手臂网格，不需要 C++ 构建。

`before.json` 是当前运行资产读取的制作输入，`source_motion.json` 是定位整枪侧摆所用的动作曲线；`author.py` 以 120 Hz 制作本轮差量，`equip_patch.json` 为交付数据，`M24_EquipDirect_Editable.blend` 为完整可编辑姿态源。`install.py` 在现有互斥下合并并保存两份 Profile；`Before/` 保留修改前副本，实际保存结果见 `install_receipt.json`。

本轮未渲染预览、启动游戏或进行额外验收，实机表现由用户测试。
