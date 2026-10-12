# 鼓囊投掷者：危险提示与爆裂表现 V04

2026-10-12，用户批准方向提示、倒计时、爆裂声、压力波、碎滴和近场镜头反馈，并要求提高导入音效的听感响度。保持 V03 管道动画和现有攻击时钟、0.65 秒引信、140 cm 伤害半径及伤害数值。

后续用户认为 V04 危险提示不够明显；当前 HUD 已改为 [V05 双层方向与位置提示](../UI/explosive-warning-v05-plan-20261012.md)。下方 HUD 小节保留 V04 历史说明；声音、压力波和爆裂表现继续沿用本版。

## HUD 与数据范围

- 归属冷钢 HUD 的 Slate 绘制层，使用现有 NumberFont 和视口几何，不创建输入控件、不抢焦点。
- 投射物 BeginPlay 注册到 `UExplosiveWarningSubsystem`，EndPlay 注销。世界停止后清理弱引用；没有活跃投射物时停止调度。
- 仅本地玩家、胶囊最近点 6 米以内的活跃囊弹；约 10 Hz 更新距离、遮挡和紧迫性，绘制时使用当前相机逐帧投影。
- 飞行接近时就显示半透明囊弹轮廓和感叹号；屏外／背后目标显示屏边箭头。中央准星和底部快捷栏留出安全距离。
- 落地后显示剩余引信圆弧和加速脉动；进入真实伤害范围且无遮挡时显示红橙危险色。墙和楼板遮挡时变为低强调灰色，与伤害共用 `ExposureTo` 查询。
- 按紧迫性选择同一方向的代表目标；最多 8 个方向分组，多枚时显示数量。绘制前立即剔除已爆裂目标，不等下一次低频刷新。
- 菜单抽屉打开但世界仍运行时继续显示危险提示；提示不改变菜单或鼠标输入所有权。

投影计算为项目独立实现。功能参考：[Skiftsu UE5-Offscreen-Indicator](https://github.com/Skiftsu/UE5-Offscreen-Indicator)、[EasyIndicators](https://github.com/dootiedoot/UnityAsset-EasyIndicators)。本次没有安装插件或移入第三方代码。

## 爆裂表现

- 落地撞击声 → 0.65 秒收紧的蓄压声 → 爆裂主体、压力波与镜头冲击，均跟随 ContactAt / BurstAt 的服务端时钟。
- 复用共享 `UFPSImpactFXSubsystem` 的贴地波、尘雾、组织雾和液滴池。新增 4 个池化折射波槽，保持共享活跃粒子总量上限 192；声音单独预分配 6 个短声道。
- 近场最多 5 团尘、4 团组织薄雾、18 个液滴，远处减量；3,500 cm 以外不生成这些细节。压力波与地面波都按真实 140 cm 半径展开。
- 保留原囊弹网格做膜屑，增加到 16 片；沿接触面向外爆开，重力下落，0.45～0.9 秒收尾。落到接触平面背面时隐藏。
- 共享尘雾和声音由世界池拥有，投射物销毁不会提前切断尾音和池化细节。
- 450 cm 内无遮挡时按距离衰减施加 0.22 秒短促相机脉冲，无全屏闪白。爆炸不改变移动或瞄准输入。
- 服务器继续只结算一次伤害；本地表现通过一次性标志启动，迟到的旧爆炸状态不重播声音和压力波。

## 声音响度

四份 48 kHz 单声道音源实际导入 `/Game/Monsters/BellowSacLobber/V04/Audio`：

| 资产 | 时长 | 用途 |
| --- | --- | --- |
| S_BellowFlight | 1.0 秒循环 | 接近时的空间化气流／囊体声 |
| S_BellowContact | 0.2 秒 | 落地短撞击 |
| S_BellowFuse | 0.65 秒 | 收紧的气流和膜体蓄压 |
| S_BellowRupture | 1.1 秒 | 低频压力、破裂瞬态、气流与组织弹响 |

2026-10-12 V06 更新：按用户要求停用 S_BellowFuse 的运行时播放。落地立即停止飞行循环，至爆炸前不再播放蓄压声；表中引信音及下方引信倍率仅作为 V04 制作历史保留。其余三段声音和总增益继续沿用。

- 爆裂音以现有 `SourceAssets/FireballImpactRealistic20260914/Pressure.wav` 为底，加入项目制作的压力和膜裂声层；处理包络与饱和后源峰值为 -2.5 dBFS。
- SoundWave 的 volume=1、pitch=1。默认总增益 `fps.Bellow.AudioGain 1.25`，约 +1.94 dB；爆裂音源前 250 ms 的 RMS 约 -11.03 dBFS（制作数据，不代表游戏实测响度）。
- 爆裂／接触在 250 cm 内维持近场音量，之后线性衰减 2,150 cm；墙体遮挡降至 0.55 并低通。飞行／引信近场 180 cm、外侧衰减 1,200 cm。
- 独立倍率：爆裂 1.0、接触 0.78、引信 0.86、飞行 0.45，均乘总增益。仅控制囊弹家族，不修改其他武器或怪物音量。
- 调整入口为现有控制台变量 `fps.Bellow.AudioGain`；默认 1.25。未新增开发面板或快捷键。

## 制作源与资源

- `Tools/BellowSacLobber/author_presentation_audio_v04.py`：音频可重建源。
- `Tools/BellowSacLobber/import_presentation_v04.py`：导入四份声音并派生压力波材质。
- `SourceAssets/BellowSacLobberMeshy20261012/PresentationV04/`：WAV、制作参数、实际保存回执。
- `M_BellowPressureWave` 派生自已有 Mutant3 波材质，复用已导入 Easy Impact Frames 的噪声法线；保留原母版和许可来源。现有血雾／血滴／尘土材质继续复用。
- 新资源位于原有 BellowSacLobber 打包目录，C++ 默认引用直接接入原 F6 怪物，不替换 V03 动作集。

## 交付状态

四份声音和压力波材质已通过后台 commandlet 编译并保存；`ue_assets_saved.json` 为实际回执。原生构建记录在 `Saved/BellowSacLobber20261012/build-presentation-v04-*.log`。

最终 `FPSGAMEEditor` 和 `FPSGAME` Win64 Development 构建均返回 `Succeeded`，分别见 `build-presentation-v04-editor-final.log` 与 `build-presentation-v04-game.log`。首次 Editor 构建中的 Pawn 对象指针推导错误已在本次新增代码中修复，HUD 投影局部变量也已显式初始化；没有修改其他模块的历史警告。本轮未启动图形编辑器，原 F6 怪物将在下次正常启动后使用新的原生实现。

未启动游戏、试听、截图、渲染预览或自动测试；实际观感、听感与运行性能由用户体验。
