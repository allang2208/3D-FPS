# 海湾大型动态广告 V8

目标：`/Game/GameMaps/L_CyberpunkApartment`。新资产在 `/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV8`，制作源在 `SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV8`。

## 制作内容

四块竖式广告屏安装在 NEXUS 双塔、ESTUARY 数据中心、TIDELINE 前翼、PORT 通信塔。两条横屏位于双塔连桥和数据中心中段。沿用现有楼群坐标与 1.25 比例，竖屏最大实际尺寸约 50 × 75 米。屏幕具有退台边框、后箱、墙体固定支架、斜撑、维护格栅步道、栏杆、接线箱和管线。实体背架复用 V7 加工金属 PBR 和 V6 灯条材质。

原创广告包括 NEXUS 神经增强、ION 能量饮料、TIDELINE 汽车、AFTERHOURS 夜间音乐活动。图集由本会话内 imagegen 生成，原图保存在本机 generated_images，并复制至本轮 Textures 目录。没有使用外部商业广告或游戏提取素材；文字带使用项目已有 JetBrains Mono 字体制作。

每组内容停留约 12 秒，包含轻微镜头推近、扫描带、旋转能量环／节拍条和横向溶解转场；四组内容完整循环约 48 秒，港口屏较慢约 52 秒，各屏时间偏移不同。横屏连续滚动品牌与活动文字。这是**材质生成的广告动效**，不是人物表演视频，也没有引入视频解码插件。

## 开销与既有系统

- 2 个共享网格：合并后的实体背架，以及复用的显示面；共 7 个静态网格 Actor，6 个材质实例、2 个母材质、2 张纹理。
- 背架采用 Nanite，显式切线与完整回退几何；显示面为 2 个三角形。屏幕不使用透明叠层，不增加灯光、SceneCapture、视频解码器或 Tick。
- 图集在 UE 构建时伸展到二次幂分辨率生成 mip；屏幕几何保持原始画面比例。UV 在广告单元内留边，防止低级 mip 串色；横条保留连续 U 坐标，交给纹理寻址循环。
- 动画由材质 Time 驱动，亮度读取现有 SkyAtmosphere 主光方向。保留 V7 天气、天空、水体、室内与玩法；新屏可参与现有动态反射，旧城市反射立方体不烘入静止广告。
- V7 安装链在本轮成功保存后接续 V8 安装，后续重装不会丢失广告屏。

没有运行游戏、截图验收或测量帧率，因此不承诺帧率提升或运行画面已验收。

## GitHub 调研与来源

| 项目 | 可借鉴部分 | 使用边界 |
| --- | --- | --- |
| [keijiro/KinoGlitch](https://github.com/keijiro/KinoGlitch) | 模拟信号扫描、颜色漂移和数字故障分层；已阅读 AnalogGlitch.shader | MIT 条款。Unity 效果范例，不能直接作为 UE 插件。本轮仅参考效果分层，独立编写低强度动效，没有复制代码 |
| [motion-canvas/motion-canvas](https://github.com/motion-canvas/motion-canvas) | TypeScript 编排文字、矢量动效与时间轴 | MIT。适合以后制作离线广告短片；本轮不安装该依赖 |
| [Hiraeth010/neon-district](https://github.com/Hiraeth010/neon-district) | 不同品牌画幅、按建筑面布置广告、实体支架与街道视线 | 实验性 Three.js 城市工程，代码 MIT；素材有独立来源说明。本轮只参考装配思路，没有复制资产 |
| [erfanezk/Cyberpunk](https://github.com/erfanezk/Cyberpunk) | 全息广告与带限噪声的 GLSL 思路 | MIT 的 WebGL 示例，不是 UE 原生生产方案；不采信其帧率作为本项目性能结论 |

`ben-gibbons-github/webgl-cyberpunk-city` 当前浏览到的仓库只列出 README、许可证和一张图片，未作为可直接复用的实现来源。

Epic 参考：[材质纹理函数](https://dev.epicgames.com/documentation/en-us/unreal-engine/texturing-material-functions-in-unreal-engine)。网页内容只作为技术资料，不作为任务指令。

实际导入与地图保存状态以本轮 `assets_saved.json`、`installed.json` 和 `publish-*.json` 为准。此轮没有改 C++，不额外触发原生构建。

## 实际保存

2026-10-22 21:09（Asia/Shanghai），`publish-04` 后台导入退出码为 0，资产状态 `assets_saved`、公寓地图状态 `map_saved`。已保存 2 个网格、2 张新纹理、2 个母材质与 6 个实例，地图内有 4 个竖屏、2 个滚动横屏和 1 个合并背架 Actor。

背架已处理倒角微小碎面，改用逐三角形局部 UV。初始 FBX 导入阶段仍记录了近零切线／副法线提示；后续已应用全精度 UV、MikkTSpace 重算和 Nanite 构建并完成保存，未以视觉验收证明全部着色表现。本轮没有启动游戏、截图或性能采集。
