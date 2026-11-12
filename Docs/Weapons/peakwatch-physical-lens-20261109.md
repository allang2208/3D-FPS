# 观峰变倍镜：原镜片内成像与图标重制

2026-11-09，用户要求观峰镜采用近期枪械高倍镜方案，并重制不合格图标。范围为高地长弓 `bow_woodsteel` 的 `sight / highland_peakwatch_3_6x`。

## 本版行为

- 共用 `PhysicalScopeScene` 的单个本地捕获，在现有 `M_Peakwatch_Glass` 材质槽显示放大画面；镜外保持正常弓 ADS 视野。
- 保留实际镜体、镜架、变倍环、弓与手臂；不再用屏幕圆框接替实体镜，也不在完整 ADS 时隐藏整套视模。
- 3–6 倍、每格 0.5 倍、平滑倍率及变倍环联动保持。鼠标灵敏度以普通 ADS 投影配合镜内倍率计算一次，避免旧主相机变倍再次叠乘。
- 独立视模构图沿用最低倍率，不随滚轮改变镜体大小；退出、菜单、换装、第三人称、死亡及视角目标改变时恢复临时投影与材质。
- 分划改在镜内显示：峰脊针尖对应相机瞄准方向，保留稀疏角度刻线及拉弓、满弓、节拍、穿心、放箭反馈。角度刻线不是箭种弹道距离标尺。正常战斗 HUD 继续显示。
- 固定倍数弓镜与箭矢结算、武器属性、动作时钟、存档及远端装备逻辑沿用既有路径。

## 几何与性能合同

沿当前实装 `Scope3to6V11/SM_Highland_Peakwatch3to6`，镜片局部中心 `(-0.4,-10.223,24.3328)` cm，半径 `1.115 × 1.75` cm；与作者源的镜片坐标一致，并通过实际网格组件变换到世界空间。镜体按原安装姿态保留。

复用一个异步准备的镜片材质和一份有界捕获，默认 1024，限制 512–1536；非 ADS 不捕获。分划按角度映射，细刻线和数字根据像素间距取舍。没有新增逐帧文件读取或同步资源加载。

## 图标来源与接入

新版以正式模型的 `peakwatch_actual_part.png` 和认可边框 `muzzle_brake_framed_v2.png` 为输入，经 imagegen 重制。保留一个完整镜体和安装架，改善旧图主体过小、偏暗的问题；采用灰阶、厚倒角金属方框、四角铆钉、银色内环、深灰底板及窄透明外缘。

正式读取键为 `Content/ColdSteelData/AttachmentIcons20260913/FramedBows/bow_woodsteel_sight_highland_peakwatch_3_6x.png`；同步对应 Texture2D，使用 UI 纹理组、Editor Icon 压缩、sRGB、Never Stream。源图经 1024 尺寸转换及规范要求的中性灰阶处理，保留 alpha。

作者目录：`SourceAssets/PeakwatchPhysicalOptics20261109`。保留生成母图、转换脚本、来源记录、修改前源码和旧资产副本、精确发布脚本及执行回执。共用材质源的重建入口也加入新分划参数，避免重导丢失。

## 交付状态

源码、生成图及正式 PNG / Texture2D 已完成。Editor 正式 DLL 构建成功：`Saved/BuildEditor/build-20261109-225738.log`。材质与图标保存回执：`SourceAssets/PeakwatchPhysicalOptics20261109/asset-receipt.json`。完整镜片图完成着色器编译并再次保存，见同目录 `material-build.json`、`finish_material.py-result.json`（退出码 0）及 `assets-20261109-230113.log`。

本轮未启动游戏、PIE、额外截图或自动验收，由用户检查实际镜内视野、准星与手感。

本文件取代观峰镜 V4/V5 的当前运行方案描述；旧文档保留为历史记录，不代表本版效果。
