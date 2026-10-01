# 暴风雪：近手乌云跟随、翻卷与红色范围预览

2026-10-01，用户确认乌云重新出现，随后要求减轻积蓄完成后移动时的拖影、改善僵硬感，并将长按范围预览改成火球／冰锥路径的红色。本轮仅制作近手积蓄乌云和范围预览；施法、付款、30 秒保持、范围成长、区域落冰与雨雪继续沿现有实现。

近手乌云原为世界空间粒子，位置由模拟持续重写，渲染器不输出运动矢量。改为局部空间，围绕现有 `CloudOrigin()` 模拟偏移；组件仍在原技能 Tick 中跟随默认施法位置，不增加世界位置平滑或遗留粒子。原 `User.CurrentPosition = CloudOrigin - CloudHeight/2` 的几何关系改写为局部 `-SurfaceNormal*CloudHeight/2`，不改变法杖／空手位置入口。使用 UE 5.8 的 `InterpolatedSpawnMode=NoInterpolation`，近手渲染器配置为 Precise，专用材质开启 Responsive AA。后续棋盘格修复关闭了材质透明速度输出：原材质 DepthFade 读取场景深度，与速度输出的深度写入在 SM6 下冲突；不可重新同时开启。

仍为三层 12／10／7 个核心，共 29 个粒子、一个 Niagara。各层种子错开，云团以不同速率旋转、翻卷、上下起伏、呼吸及轻微密度变化；下层反向运动，纹理扰动速度略增。新增 `M_BlizzardGatherCloud`、`MI_BlizzardGatherCloud` 两个专用副本，继续依赖已安装 Normandy 云纹理，保留已有软边遮罩。世界区域乌云、寒雾、雨雪和冰锥不采用近手抗拖影参数。

范围预览只修改 `M_BlizzardAimPreview` 的 Tint 默认值，保留原椭圆几何、细圈、分段、淡出和地面投影。作者直接读取 `FPSMagicPreview::LineColor()`，当前线性 RGBA 为 `(0.95, 0.12, 0.08, 1)`，与火球、冰锥路径共用颜色来源。

可重建源为 `Tools/Skills/build_blizzard_charged_v3.py`；本轮定向保存入口为 `Tools/Skills/refine_blizzard_gather_20261001.py`，只处理近手系统、两个近手材质副本和预览材质。执行及保存记录在 `Saved/BlizzardGatherNatural20261001`。资产落盘状态以 `asset-authoring.json` 和实际命令退出结果为准，不能将脚本已写好当作已保存。

本轮已通过无界面 commandlet 完成上述四个资产的编译与保存，进程退出码为 0，保存回执 `asset-authoring.json` 已生成；编译日志为 `asset-commandlet-01.log`。原积蓄／正式乌云按 `User.StormDuration` 控制系统时长的修正继续保留。

本轮没有改动 C++，不需要原生重建。没有启动游戏、PIE、截图、渲染或运行验收；观感及运动时的拖影改善由用户测试确认。

用户后续报告凝聚云团棋盘格，日志明确给出 SM6 编译失败及 Default Material 回退。定向修复作者与这两份材质已通过现有编辑器桥保存；详细原因与本次电矛可读性调整见 `Docs/Skills/magic-readability-and-blizzard-material-fix-20261001.md`。原局部运动和29粒子系统未重建，未追加运行测试。
