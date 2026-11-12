# 观峰镜半片未放大及拉弓移动分界修复

用户实机反馈：镜内约一半未缩放，拉弓时放大部分继续挤占未放大部分。此前 V12 构建、模型保存和 42% 镜口构图目标不构成画面合格，本次以该反馈继续修复。

## 原因与改动

共用镜片材质的覆盖量使用 `step(dot(Position-Center,Forward),Depth)` 选择后部镜片。其中材质的 `Position` 包含 UE 第一人称投影变换，CPU 写入的 `LensCenter`、`LensForward` 和 `RearDepth` 则仍是未变换的世界空间数据。第一人称视模 FOV 把镜片放大后，二者不在同一空间；拉弓改变镜体姿态，会改变错误裁切面的相交区域，留下透明、未放大的部分。

UE 5.8 `BasePassVertexShader.usf` 在 WPO 后调用 `ApplyMaterialFirstPersonTransform`；`MaterialTemplate.ush` 的默认世界坐标读取变换后的像素位置。该代码路径与用户反馈吻合，未运行实机复现或截图测量。

观峰 V11/V12 的玻璃槽只有一块闭合镜片，作者坐标 X 范围约 `-0.4975..-0.3025 cm`，无须使用多片镜组的前后截面筛选。对 `ReticleStyle == Peakwatch (7)`，覆盖量只随既有 ADS `LensBlend` 变化，由原镜片的实际几何边界限定显示区域；完整 ADS 时全片使用捕获画面，拉弓／松弦不会再驱动内部裁切线。其它镜型沿用原覆盖分支。

没有增加捕获、屏幕叠层或额外网格。继续使用已有一份 ADS 捕获、3–6 倍倍率、角度分划和拉弓反馈；这次不再改镜口目标大小或弓的姿态。

## 制作源与交付边界

- `SourceAssets/SharedPhysicalOptics20261030/lens_coverage.hlsl`：实际覆盖表达式。
- 同目录 `install.py`：新建材质时沿用本修复，避免重制时退回旧分支。
- `SourceAssets/PeakwatchCoverage20261110/publish_coverage.py`：只修改现有覆盖节点及其镜型输入，保留其余材质图和各枪分划；保存前备份原材质。
- 目标资产：`/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens`。

2026-11-10 已在后台完成材质编译和保存，commandlet 退出码为 0。记录见作者目录的 `asset-receipt.json`、`commandlet-result.json` 和 `assets-20261110-102019.log`；本次材质编译记录为 4093 像素指令、519 顶点指令、7 个采样器。这些是编译产物信息，不是运行性能或画面验收数据。

上述材质修复阶段没有 C++ 修改，无须重编原生 DLL。当时未运行游戏、PIE、截图或验收。

## 用户追加授权后的画面检查（2026-11-10）

用户随后明确要求自行检查拉满、松弦、切倍率、镜内完整放大和镜外视野。本节记录该授权后的实际运行，不把此前的编译保存当作检查通过。

使用 `DayNight_Lighting` 正式地图，1600×900，后台 `UnrealEditor-Cmd -game -RenderOffscreen`，正式高地长弓、V12 观峰模型与已保存镜片材质。隔离 `ColdSteelProfile` 和 `UserDir`，角色及弓动作照常 Tick，经实际 PlayerController 鼠标输入触发 ADS、拉弓和射箭；只固定测试角色移动，未手工指定弓动画进度。

本轮增加按命令行启用的 `Weapons/Bow/PeakwatchCoverageAudit.inl`，由既有 `ScopeScreenshotAudit.cpp` 包含；没有改动正式成像算法。最终构建日志：`Saved/BuildEditor/build-20261110-115710.log`。记录生成测试 DLL 的 SHA-256、进程 PID、启动参数及独立档案，见各采集目录 `launch.json`。

两次进程均正常退出（退出码 0）：

- `SourceAssets/PeakwatchCoverage20261110/Review/production-20261110-115243`：24 帧，包含 3 倍和 6 倍拉满、连续松弦阶段、倍率往返及退出 ADS。首轮中间档因检查脚本使用整倍步进，实际到达 5 倍，虽然历史文件名含 `4p5`；以该轮 `capture.json` 的实际倍率为准。
- `SourceAssets/PeakwatchCoverage20261110/Review/halfstep-release-20261110-115813`：修正检查脚本为半倍步进后采集 28 帧，实际到达 3、4.5、6 倍；补充 3／6 倍松弦中的覆盖遮罩。无缺失图片，状态记录包含 Drawing、Holding、Release、Recover 和 Ready。

检查结果：

| 项目 | 本次观察与测量 |
| --- | --- |
| 镜内完整覆盖 | 3／6 倍拉满和松弦共 4 个纯色遮罩样本均覆盖整块镜片，没有旧的半片透明区域。镜片内部缩入 4% 避开抗锯齿边缘，再排除准星与拉弓 HUD 区域后，剩余测量像素覆盖率均为 100%。未排除 HUD 时为 97.45%–99.55%。 |
| 分界移动 | 正常场景的拉弓、松弦起始／中段／回收画面未见内部放大／未放大分界。镜框随正常回收姿态略有转动，放大画面边缘跟随实体镜片。 |
| 倍率与镜外视野 | 3→4.5→6→3 的 26 个完整 ADS 样本，主相机水平 FOV 始终为 99.8159°，视模 FOV 为 14.9146°，LensBlend=1；镜内场景细节随倍率改变，镜外几何未随倍率缩放。 |
| 镜口大小 | 拉满 3／6 倍的投影直径均约 376.65×377.99 px，即短边高度约 42%。两者投影中心差异小于 0.01 px；截图绿色实际边界约 377–378 px。该精度是记录值，不代表画面抗锯齿具有亚像素验收精度。 |
| 镜框外溢出 | 四个覆盖样本在投影镜片外扩 4% 的边界之外均检出 0 个探针色像素；结合正常截图未发现放大画面挤占镜外视野。外扩用于排除边缘抗锯齿／泛光，不把它当作新的可见镜口。 |
| 退出恢复 | 最后样本 `first_person_enabled=false`、视模 FOV 恢复 90°，截图显示镜片恢复普通透明玻璃。 |

纯色遮罩仅临时替换当前进程的捕获纹理，用来检查实际材质覆盖，未保存到正式材质。紧随探针恢复的少数帧可带有绿色 TAA 残影，因此正常场景结论同时依据首轮无探针干扰的动作帧；该调试残影不作为生产效果。

本次范围为上述地图、分辨率和离散动作／过渡样本，未代替连续操作手感、其他宽高比或所有场景验收。首轮和补充轮均保留原始 PNG、`capture.json`、`image-analysis.json`、`runtime.log`、`process-result.json`。检查程序和像素测量入口为作者目录的 `capture.ps1`、`analyze_capture.py`。
