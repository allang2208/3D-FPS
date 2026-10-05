# 螺柱 M-14：V10 毒液材质

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。接续 V09 的液团、拉丝与命中液膜，调整用户提出的液体写实感。

## 外观制作

- **厚薄与透色**：主体采用 Substrate Thin Translucent 彩色透射。根据原球体截面、尾部收细与观察方向估算 0.025–约 23 cm 的光程，再以 Beer–Lambert 吸收计算透光；厚处呈暗橄榄色，细丝和边缘透出较浅黄绿色。吸收系数为 `(0.073, 0.057, 0.157) /cm`，可用 `AbsorptionStrength` 调节。
- **浑浊内芯**：原不透明内芯改为有光照的半透明斑块。覆盖随密度、视角与厚度变化，上限约 0.315，轮廓渐隐；用于表现悬浮杂质，减少硬球内芯感。
- **湿润高光**：外层粗糙度约 0.064–0.135，Specular 0.26 对应约 0.0208 的正常入射反射率。低强度法线起伏保留连贯高光，浑浊层使用更宽、更弱的反射。
- **折射**：主体用 Pixel Normal Offset，参数 `RefractionOffset=0.08`，按厚度收敛；液膜最大增量 0.025。参数为屏幕偏移强度，不是物理折射率。
- **细节流动**：将周期正弦密度改为两层连续三维值噪声，沿液丝方向缓慢平移。稀疏气泡由每格稳定种子确定位置和大小，避免统一频率闪动；无自发光。
- **命中液膜**：延续 0.4 秒寿命与原不规则扩散轮廓，透射随膜厚从约 1 mm 向薄膜变化；边界覆盖归零，折射、法线与反射随覆盖衰减。

这是基于现有网格的光程近似和材质动画，没有新增体积液体求解器。液滴、残留贴花仍使用现有共享表现；本轮只修改 M14 的主体、内芯、瞬时液膜。

## 接入与恢复

三份现有专用材质原位升级，保留运行时路径以复用蓝图和对象池引用：

- `/Game/Monsters/SpiralPillarM14/VenomV09/M_M14_VenomBody`
- `/Game/Monsters/SpiralPillarM14/VenomV09/M_M14_VenomCore`
- `/Game/Monsters/SpiralPillarM14/VenomV09/M_M14_VenomFilm`

制作入口：[author_venom_material_v10.py](../../Tools/SpiralPillarM14/author_venom_material_v10.py)。已有编辑器的正常接入入口：[save_venom_material_v10.py](../../Tools/SpiralPillarM14/save_venom_material_v10.py)，仅在保存需要时结束当前 PIE。

HLSL 位于 `SourceAssets/SpiralPillarM14Meshy20261004/ProductionV10/Shaders`；保持 V09 的 `M14LiquidShape`、CPD 0 随机种子及 CPD 1 飞行时间。升级前的三份材质保存在同目录的 `BackupV09`。历史 V09 生成器仍是旧版恢复源，重建当前材质须接着执行 V10 制作入口。

没有新增纹理、粒子或原生 Tick；外层彩色透射、内芯透明绘制及局部折射会改变渲染成本，本次没有性能采样。伤害、判定、射程和攻击动作沿用原实现。

## 制作状态

三份实际运行引用的材质已完成必要编译并保存，沿用 V09 资产路径。本轮没有原生代码变更，不需要 Editor/Game 原生重编译。

通过已有编辑器会话保存，结束了妨碍保存的 PIE，没有打开、重启编辑器或主动启动游戏。未运行游戏测试、截图或验收渲染，观感与性能由用户体验确认。

[资产保存回执](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV10/Records/assets.json)。
