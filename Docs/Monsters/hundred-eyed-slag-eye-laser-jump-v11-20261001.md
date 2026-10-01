# 百目炉渣：聚眼激光与跃起下砸 V11

用户要求用原地眼睛汇聚激光替换冲刺，用低伏、向上跳跃下砸替换灰烬爆发。保留横扫 V8、巨臂下劈 V9、现有 V8 网格和蒙皮、移动、受击、眩晕、死亡布娃娃及 F6 原入口。

## 聚眼激光（魔法伤害）

- 原地蓄能 1.2 秒，现有前侧眼区的光汇聚至身前焦点，期间保持四肢支撑。前 80% 可朝向玩家，随后锁定三维发射方向。
- 发射 0.65 秒，再收势 0.5 秒。射程 1200 cm，碰撞半径 12 cm。射线被首个可见阻挡截断；命中额外检查遮挡，每次释放对同一玩家最多结算一次。
- 伤害为当前魔法攻击 ×1.6，通过 `UHandBrainMagicDamage` 使用现有魔法减伤路径。蓄能没有伤害；打断和死亡立即隐藏激光并取消尚未发生的结算。冷却 6 秒。
- 当前骨架没有独立眼骨，眼区锚点按网格坐标转换至 `front_plate` 的参考骨骼空间，随前甲与身体移动，不假设不存在的 `eyes_L/eyes_R`。两个锚点为默认制作位置，尚未经过游戏视觉测试。
- 使用新建的加法、无光照、深度淡化材质；七个无碰撞、无阴影、无 Tick 的球体/圆柱组件复用，两个动态材质缓存。远处隐藏外观，不改变权威伤害。

## 跃起下砸（物理伤害）

- 原地低伏 0.7 秒，然后用 `LaunchCharacter` 和角色胶囊的原生扫掠移动竖直起跳；默认高度 230 cm。到达顶点后加重下落，起跳和腾空没有范围伤害。
- 只由实际 `Landed` 接触步行地面触发伤害，落点为胶囊下方实际地表。落地半径 350 cm，当前物理攻击 ×1.8，通过 `UEnemyMeleeDamage` 使用现有物理减伤路径，墙后目标受遮挡保护，每次跃砸去重。
- 落地压缩 0.4 秒，起身收势 0.65 秒，冷却 7 秒。未落地、被打断或死亡不补发落地伤害；低顶会由原生碰撞缩短实际跳跃。
- 复用世界特效池的冲击环、灰尘、焦黑碎屑、余烬、落地音效和衰减震屏；落地环范围与伤害范围一致。共用落地特效的角度上限扩展到 360 度，原有较小角度调用保持原参数。

## 动画来源与保存路径

实际从已导入的 Epic Paragon Rampage 导出 `Jump_Start`（0.3 秒/19 采样）、`Jump_Mid`（0.3667 秒/23 采样）、`Jump_Fall`（1 秒/61 采样）、`Jump_End`（0.2333 秒/15 采样），包含完整选定关节的 60 Hz 变换，保存在 `SourceMotion/`。按百目炉渣四肢比例和固定骨长重新适配，复用现有巨臂辅助骨、轴向偏移和连续关节平面；未修改网格和权重。

最终八条动作以 60 Hz 导出：EyeLaserWindup / Fire / Recover；JumpWindup / Rise / Fall / Impact / Recover。腾空高度只由角色胶囊产生，动画没有第二份根骨上升。地面动作按可达范围调整身体高度，保持四个支撑点。

- 源文件：`SourceAssets/HundredEyedSlagMeshy20260930/EyeLaserJumpV11/`
- 动画：`/Game/Monsters/HundredEyedSlag/EyeLaserJumpV11/Animations/A_HundredEyedSlag_*`
- 材质：`/Game/Monsters/HundredEyedSlag/EyeLaserJumpV11/Materials/M_EyeLaser`
- 执行代码：`Source/FPSGAME/Monsters/HundredEyedSlagSpecialAttacks.cpp`
- 旧冲锋原生执行文件已移出编译，其备份在本版本 `Before/`；旧枚举数值和旧参数保留序列化兼容，旧冲锋及灰烬爆发不再进入当前攻击选择。

## 当前交付状态

八条动画与激光材质已导入保存，原生源码已完成 FPSGAMEEditor 目标内 FPSGAME 玩法模块的常规编译并落盘基础 DLL。整项目首次构建被共享 AutoFootstep 插件 DLL 占用挡住，因此最终采用普通 UBT 的 `-Module=FPSGAME`；没有替换或重建占用中的插件 DLL。以 `ready_assets.json`、`build_installation.json` 和 `installation_complete.json` 分别记录资产落盘、常规 Editor DLL 构建和接入完成状态。未构建独立游戏可执行文件。未启动测试、PIE、预览渲染或视觉验收，由用户通过 F6 怪物生成面板试玩。
