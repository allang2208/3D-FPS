# FireFlame 外焰接入（2026-09-14）

用户同意使用新导入的 Free Spline VFX 为当前慢速火球补充外焰。保留柔和亮核和翻滚主体，增加短、根部柔化的火舌。

## 当前接入

- 运行主体仍为 `/Game/Skills/Fireball/NS_FireballSlowBurnCore`，在该资产中追加 `FireballOuterFireFlame` 发射器。原有 `FireballCore` 与 `FireballSlowRoil` 发射器未改动。
- 火焰贴图来自 Dr.Game 的 [Free Spline VFX](https://www.fab.com/listings/2b923e61-b02d-4cc9-bd0b-b067c9e6056e)：`/Game/_SplineVFX/_GenericSource/Texture/T_Vfx_Stamp_FireFlame_88`，对应原 `NS_Spline_Fire / Fire_B` 的视觉素材。
- 新建 `M_FireballOuterFireFlame` 与 `MI_FireballOuterFireFlame`，不修改原资产包。专用材质按 RGB 火焰贴图处理，不沿用 Epic EOO 通道解释；使用帧间混合，柔化底部和两侧，以 6 cm 深度淡化处理场景交界，在所有透明度处理之后预乘发光，避免单独残留亮边。
- 没有复制原样条蓝图的地形吸附、贴花、烟雾、火星和附加灯光。新增层沿用现有核心模板的基本粒子生命周期。

## 初始参数

| 项目 | 当前值 |
| --- | --- |
| 粒子空间 | 局部空间，CPU |
| 生成频率 | 8 个/秒 |
| 寿命 | 0.9–1.4 秒 |
| 根部半径 | 8–10 cm，位于主体内部 |
| 火焰宽/高 | 10–13 / 13–16 cm，随后轻微缩小 |
| 根部支点 | UV `(0.5, 0.82)` |
| 循环播放 | 8×8，12–16 帧/秒，各粒子起始帧不同，启用帧混合 |
| 粒子透明度峰值 | 0.58，材质再乘 0.60，另受覆盖度及边缘淡化影响 |
| 发光倍率 | 1.7 |
| 根部渐隐 | 每帧局部 UV.y 从 0.62 到 0.98 |

位置、尺寸和相位交错，不按闭合圆环排列、不统一绕轴旋转。火焰根部融入现有主体，目标是让短火舌露出主体约 4–7 cm；最终可见长度和亮度尚未进行实机确认。

## 悬浮及发射

- 悬浮时火舌朝上并略向外倾，根部仅有小幅摆动和短距离上移。
- 使用现有 `User.Flight` 与 `User.FlightAge`，在发射后的前 60 ms 平滑过渡到局部 -X。已有 Actor +X 跟随真实速度，所以该方向对应弹道后方。
- 根部位置和 `Particles.SpriteAlignment` 同步转向后方，令序列贴图内部的向上燃烧也旋转为向后燃烧。固定 `SpriteUVScale=(1,1)`，避免继承模板的翻转方式；不使用随机火焰旋转覆盖飞行方向。
- 飞行位置保持在短距离后方范围内，不以长时间悬浮的粒子年龄乘飞行速度。现有世界空间拖尾、凝聚/脱手规则、左手动作、碰撞及伤害不变。
- 外焰属于已有 Core 组件，凝聚缩放、靠近相机的可见性和命中后的即时停止随原组件生效。没有新增 Actor、组件、网络接口或 C++ 改动，无需本次原生重编译。

## 作者源

- `Tools/Skills/build_fireball_outer_flame.py`：独立制作并保存外焰层；仅改自己的材质和当前火球中的新增发射器。
- `Tools/Skills/build_fireball_assets.py`：完整重建在慢速主体之后追加外焰调用。单独重建基础慢速主体后，需要再次执行外焰脚本。
- `SourceAssets/FireballOuterFlame20260914/authoring.json`：当前参数、素材路径及来源。
- `Saved/Fireball-Outer-Flame-Assets-20260914.log`：本次资产制作和必要 Niagara 编译日志。
- 两个专用材质及更新后的主体系统已保存，Niagara 编译 `valid=1`，制作脚本执行成功。命令行退出码 1 来自工程既有 `GameFeatureData` 资产管理器配置错误，本次未修改该无关设置。

## 棋盘格材质修复

用户实机反馈外焰呈马赛克。`Saved/Logs/FPSGAME.log` 在 2026-09-14 12:29:29（日志 UTC 04:29:29）明确记录：`MI_FireballOuterFireFlame ... missing usage flag NiagaraSprites! Default Material will be used in game.` 原因是新建材质没有持久保存 Niagara Sprite 用途标记。之前的 Niagara 粒子程序编译成功不代表这个材质用途已配置。

- `build_fireball_outer_flame.py` 增加 `enable_sprite_usage`，创建父材质时显式调用 UE 5.8 `SetBaseMaterialUsage`；材质实例同时设置 NiagaraSprites 用途覆盖。
- `fix_fireball_outer_material_usage.py` 为已安装的两个材质补上用途并保存，不重建粒子或改动贴图、颜色、尺寸和运动。
- 修复保存日志：`Saved/Fireball-Outer-Material-Usage-Fix-20260914.log`。Windows 材质着色器构建日志：`Saved/Fireball-Outer-Material-Shaders-20260914.log`。
- 修复脚本执行成功并保存父材质和实例。`CookShaders` 已完成该材质的 Windows `PCD3D_SM6`、`PCD3D_SM5` 构建，没有报告该材质编译错误；命令行退出码 1 仍来自既有 `GameFeatureData` 配置错误。未运行游戏或进行视觉验收。

继续遵守已取得素材包的许可和依赖要求，本次接入不代表取得原始素材单独再分发授权。

按用户规则，未运行游戏、自动测试、截图或渲染；实际效果交由用户测试。
