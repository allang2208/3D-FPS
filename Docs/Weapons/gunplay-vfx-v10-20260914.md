# Gunplay V10：扩大扩散、停火余烟与火光柔边

按用户反馈，扩大连续白烟的扩散范围，在停火后留下少量从枪管口冒出的细烟，并细化枪口火光从亮芯到透明外缘的衔接。

## 烟雾

- 出生尺寸沿用 V9，随年龄逐渐扩散，成熟阶段宽高默认达到 V9 的 1.6 倍；`UFPSWeaponFXComponent::SmokeSpreadScale` 提供 1.0–2.5 的调整范围。单层寿命调整为 2.1–2.5 秒，略增上升与侧向漂移。
- 每发延长同一个连续组件的供烟时间。供烟结束前 0.18 秒，平滑转向停火余烟；余烟阶段持续约 1.1–2.3 秒，时长和烟量随最后一发的枪管热量变化。
- 余烟初始发射率约每秒 12–20 层并逐渐降至零，尺寸为主烟的约 46%，透明度为主烟的 62%，前冲速度降低到约 3 cm/s，随后缓慢上飘。单发也有余烟，连续开火会增加持续时间。
- 供烟原点使用当前真实枪口／枪口附件出口，已有烟保持世界空间。出生尺寸、速度和颜色由新粒子采样，转入余烟不会让已有主烟突然缩小。再次开火继续供烟，不重置整片烟雾。
- 保留已修复 Niagara Sprite 标记的 `M_MuzzleSmokeSheetV9`，不新增外部贴图。连续密度场和低透明度烟层叠加路线不变。

## 火光

新材质从 V8 柔边版本派生，将低透明度边缘的提亮改为更宽的平滑过渡，依据屏幕像素导数平滑透明度响应；灰阶外缘保留薄弱光晕，透明区域不额外发光。

亮芯至外缘按连续权重过渡到较暗的暖色，核心发光小幅增加；发光仍沿用预乘透明度的材质输出，因此结束时光和轮廓同步淡出。深度交界的淡出距离由 3.5 cm 调到 6 cm，启用序列帧插值，并细调生命周期的透明度曲线。

保留现有朝向、随机焰瓣、生命周期长度、步枪火光尺寸以及手枪 0.45 倍尺寸设置。曳光、抛壳位置、转轮手枪射击不抛壳及 LPVO 1–6x 隐藏弹壳规则不作修改。

## 作者源与接入

- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`：扩散调节、主烟到余烟过渡、组件生命周期和 V10 引用。
- `SourceAssets/GunplayVFX20260914/FlashFeatherV10.hlsl`：项目原创火光边缘算法。
- `Tools/AssetPipeline/build_gunplay_presentation_v10.py`：材质、实例与 Niagara 资产生成入口，依赖本地合法 V8/V9 资产。
- `/Game/Weapons/GunplayFX/NS_FPS_MuzzleFlashV10`、`NS_FPS_MuzzleSmokeStreamV10`、`M_MuzzleFlashFeatherV10`、`MI_MuzzleFlashCoreV10`、`MI_MuzzleFlashLobesV10`。

这些改动仅涉及本地枪械表现组件，不改变弹药、伤害、动画事件或网络状态。新增版本保留旧资产作为制作输入；第三方派生二进制沿用原资源的分发限制。

按用户规则不启动游戏、不做自测或视觉验收，最终观感由用户测试。

## 制作与构建记录

- 五项 V10 资产已编译／保存，`Saved/Logs/GunplayV10-Assets-20260914-c.log` 记录全部 `GUNPLAY_V10_SAVED` 和 `GUNPLAY_V10_ASSETS_CREATED`。使用 D3D12 资产编译命令，不加载游戏地图或渲染预览。
- Commandlet Python 制作完成，整体退出码 1；日志另有工程既存的 GameFeatureData 配置错误，以及启动阶段原生 CDO 查找尚未生成的 V10 烟系统的记录。该烟系统随后由脚本创建并保存，普通 Editor 构建在资产完成之后执行。
- 普通 Editor 模块构建完成：`Saved/BuildEditor/build-20260914-091008.log`，`Result: Succeeded`。没有运行游戏测试。
