# 弓镜分划拖影修订

用户反馈：两款弓镜的十字和中心点有明显拖影、残影。当前分划位于透明镜片材质中；旧作者脚本没有为该材质显式启用深度／速度输出。角色相机的常规运动模糊强度已是 0，本次从透明分划的运动重投影与历史帧保留处理入手。此为依据源码的定位，未采集游戏画面来确认唯一原因。

- `Output Depth and Velocity = True`，使用实体镜片的完整运动向量，`Velocity From Depth Only = False`。
- `Opacity Mask Clip Value = 0.333`。镜片透明区域的不透明度最高 0.235，低于阈值；仅分划及其暗边覆盖区域写入镜片深度／速度，避免整片玻璃覆盖后方场景的运动信息。
- 保持 `After DOF` 并启用深度测试，让十字保持随真实镜片移动、正确遮挡。
- 新增 `Temporal Responsiveness` 输出，输入为分划覆盖度乘 0.75。引擎将大于 0.5 的值编码为拒绝历史帧，低覆盖度边缘使用较温和的响应；透明空白处为 0。沿用项目已经启用的 `r.Velocity.TemporalResponsiveness.Supported=1`，本次不修改全局配置。
- 不启用会作用于整片玻璃的 `Responsive AA` 开关；该开关主要面向 TAA，不能替代 TSR 的局部响应输出。
- 中心点 3.6 像素、增益 2.4、绿色、细十字、解析抗锯齿、玻璃透光和两种倍率保持原设置。

`apply_temporal.py` 仅对两份现有玻璃材质添加局部响应节点与相关属性；保存前资产与旧作者脚本已归档到 `trash/weapon-bow-inspect-publication-20260927/` 下本目录对应的 `Before/`、`BeforeSource/`。可复用作者脚本 `../materials.py` 同步此处理，后续重新制作镜片会沿用。

两份材质已通过后台 Python commandlet 保存，记录见 `apply-receipt.json`，执行日志为上级源目录 `install.20260927-221058-279.log`。保存前两份材质的 `Output Depth and Velocity` 均为 False，保存后均为 True。未启动交互编辑器、游戏、截图或测试；减轻拖影的实际效果由用户确认。

参考：[Epic：透明材质的运动信息与遮罩阈值](https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-in-unreal-engine#outputtingtranslucencyvelocitiesinmaterials)、[Epic：Temporal Responsiveness](https://dev.epicgames.com/documentation/unreal-engine/thin-geometry-detection-with-temporal-super-resolution)、[Epic：Responsive AA 与 TSR](https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-frequently-asked-questions-for-unreal-engine)。本机节点档位依据 UE 5.8 `MaterialExpressionTemporalResponsivenessOutput.h` 与 `VelocityShader.usf`。
