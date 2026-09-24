# 天空亮斑、第二个太阳与反射方向

用于主场景出现疑似第二太阳、反向光晕或强反射。先定位实际场景和运行材质，避免套用丘陵的独立天空实现。以下是排查路线，不自动触发启动 UE、修改效果或 A/B 测试。

## 运行覆盖优先于资产默认值

- 分开查看实际 DirectionalLight、天空材质的太阳盘／HDR 高亮、SkyLight 指定立方图，以及相机后处理。一个亮斑不等于多了一盏灯。
- 查实际天空组件的 material → MID → parent → master 链。FPSGAME 的 `StormCloudComponent` 会把 PWL 天空材质替换为 `/Game/Weather/NaturalV2` 动态实例；只读关卡中原始 PWL 材质可能漏掉真正运行链。
- 后处理以实际相机、启用的 override 和 blend weight 为准。主场景 PWL Profile 曾有 LensFlareIntensity≈3.65，但第一人称相机由 `FPSComfortLighting::Apply` 覆盖为 0，权重为 1。不能再以 profile 的 3.65 判定当前光晕来自镜头耀斑。
- 场景中存在普通 SkyLight 和 CubemapSkyLight 不等于两个都在工作；结合可见性、启用状态和 SourceType 判断。

## 三条方向需要分别查清

1. 权威太阳方向：实际 DirectionalLight 的旋转与天空使用的 light index。
2. 视觉天空：立方图是否自带太阳／亮斑，材质是否用 `Time × SkySpeed` 或其他旋转；不要只看静态 SkyRotation。
3. 反射和环境光：SkyLight 是否指定同一 cube、SourceCubemapAngle 是否与视觉天空一致，还是实时捕获。

2026-09-24 主场景记录：一盏太阳；运行天空使用 NaturalV2 HDR 材质与 `T_HDR_Sunshine_02`；MPC 的 Sky Rotation=0、Sky Speed≈0.0005，视觉立方图随时间旋转；指定立方图的 SkyLight 角度为 0。源码结构存在方向脱节的可能，但没有通过用户授权的比较实验确认截图亮斑根因；不要把这些值写成通用修复参数，也不要声称已修复“双太阳”。

确需调整时，在用户授权范围内统一选定权威方向与需要保留的高亮表现，再同步视觉天空和反射。不要自动关闭整套环境光、Bloom、Lumen 或光追。HDR 压缩只改变编码，不会凭空新增灯或太阳节点。

工程排查记录：`Docs/Weather/main-hub-highlight-diagnosis-20260924.md`。HDR 格式与驻留预算见性能技能的 `references/hdr-texture-residency.md`。
