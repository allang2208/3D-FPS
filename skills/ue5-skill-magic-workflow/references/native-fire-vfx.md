# 现有火焰资产的 Niagara 适配

适用于换用本机 Cascade / Niagara 火焰素材。案例是 2026-09-22 焰甲与陨星 RealisticV5；当前作者为 `Tools/Skills/build_fire_magic_realistic.py`。这是制作经验，保存和编译完成不表示用户已认可画面。

## 保留源材质的输入语义

- 先读取原系统实际使用的材质、SubUV 行列、帧推进、寿命、Dynamic Parameter 和颜色范围，再建立项目副本。不要只看贴图名称后统一套用 8×8 / RGB-on-black。
- UE Python 中 `ParticleSystem.emitters` 可能受保护。本次使用 `ObjectExporterT3D` 导出本地文本，读取 LOD0 的模块和 Distribution 曲线，无需为了读取参数启用 Cascade 转换插件。实例脚本在 `SourceAssets/FireMagicRealistic20260922/read_sources.py` 与 `summarize_sources.py`；完整 T3D 和材质图导出留本机。
- Realistic `M_Fire_B` 为 8×4，`M_Fire_C` 与 Trench `M_Fire_SubUV` 为 6×6；火焰 Dynamic X 是随机遮罩偏移，Y 是透明度指数。Realistic `M_Explosion_B` 为 12×12，X 则是 Glow，不能复用火焰参数解释。保持完整材质图中的颜色/打包通道解码、粒子色与 DepthFade。
- 帧序列按单粒子寿命推进，错开发射时间产生变化；不要随机跳帧替代动画。原系统可能使用极高 HDR 值，必须与项目曝光补偿共同调整，避免补偿后变成一片白。

## 黑焰和主体消失

- 本次 SplineV4 黑焰来自最终发光缺少 `EyeAdaptationInverse`：RGB 被曝光压暗，而 AlphaComposite 仍遮挡背景。局部材质补偿时保留原透明度/软边，不改全场景曝光；Niagara sprite usage 也需启用。
- 火苗和实体主体分别制作。火球保留可辨识球核，陨星保留写实岩体；增加烟、尾焰或爆燃不等于可以删除主体。
- 编辑器处于 PIE 时，资产 API 可能拒绝操作并返回 false/None，看起来像源资产不存在。先根据日志确认状态；必要的制作需结束 PIE 后再进行，不能据此覆盖或重建源资产。

## 归档不能切断重建链

当前 RealisticV5 从 SplineV4 复制系统容器后清掉旧发射器，再加入新层；它也调用 `build_fire_magic_spline` 的曝光和扰动函数。SplineV4 又依赖 PolishV2 / 初版。它们不再是现用视觉，但仍是有效作者输入，保留这些脚本与模板。

仅把无调用的废案、旧备份和研究快照移入 `trash`，按项目规则记录原路径、替代物及哈希。资产包授权不等于再分发许可；公开仓库发布作者脚本、参数说明和恢复顺序，不发布 Fab 二进制或完整第三方材质/系统导出。
