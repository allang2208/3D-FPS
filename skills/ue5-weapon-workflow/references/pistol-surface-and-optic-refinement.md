# 手枪表面、衔接件与镜内表现

适用于 FPSGAME 的手枪配件制作与已有瞄具精修；沿用用户的后台开发规则，制作、保存与构建记录不等于运行或视觉验收。

## 通用手枪防滑纹

- 复用选项和材质，按枪型另做贴合网格。`pistol_grip_surface_options` 经 `PistolGripSurface::MergeOptions` 只合并到显式配置 `pistol_grip_surface.mesh/bone` 的枪型；不要放入向所有枪广播的 `common_options`。左轮的替换握把单独走 `DanWesson715FittedParts`。
- 保留原握把，薄覆片贴合侧面及前缘，边缘渐薄，避开弹匣井、按钮和机械件；挂点使用目标骨架参考链。当前 M1911 使用 `reargrip` 槽，但显示名为“握把防滑纹”。
- 玩家手枪、副手、独立枪匠预览、掉落装配均传入实际物品的武器定义，不能从主手角色猜宿主。卸载时销毁覆片，防止父级显隐传播让旧覆片复活；预加载与湿润映射同步接入。
- 用户确定细点快握：`ads_percent=-0.10`、`stability_mult=0.95`、`recoil_mult=1.05`。稳定性统一使用 `stability_mult`，不要再另列镜头震动奖励。`effects` 使用 `{text, benefit}` 对象数组；容量与耗时不得脱离同一属性计算链。

## 衔接件和扩容件局部精修

- 接触轮廓从宿主实际曲面或截面提取。外轮廓要保留护罩的窄下挂、圆弧和肩部，包围盒圆角块或截面凸包会填平凹区，形成厚重直墙。内侧贴合、后端薄过渡、外侧顺轮廓共同处理。
- 715 靶射配重套 V1 被用户否定；V2 按原护罩径向轮廓重做并获用户“成功了”反馈。现行作者入口 `SourceAssets/DanWesson715MuzzleWeightFitV2_20260927/author.py`，旧 `MuzzleModels20260927` 仅制作紧凑补偿器。V2 仍依赖旧目录的 `source_frame.json` 和 GripBrake 的 host 快照／材质母版，归档时保留这些输入。
- 瞄具座只替换安装座材质分区，保留镜体、光心、插座、UV 与法线。两种镜体分别采样支撑宽度；不要通过移动整个镜体修饰接缝而破坏 ADS。
- 扩容弹匣先保留上部插接区、供弹口与抓握位置，再对外露续接段与底板做有限圆角。若续接是独立面片，局部焊接后再倒角，防止缝口法线裂开。当前 M1911 制作链是 ExtendedMagazine → AttachmentPolish，不能把初版母版当废案移走。
- M1911 瞄具链是既有母版 → AttachmentPolish → ReticleReadability。运行路径相同；恢复资产时按此顺序，最终分划以 Readability 为准。ADS 下缩小看不清分划时先改分划几何和屏幕可读尺寸，不放大整镜或改变光心。

## 高倍镜与镭射

- LPVO 选定倍率与显示倍率分开，镜内 FOV、灵敏度及倍率环读取同一平滑值，避免各自插值不同步。固定 PSO 与长出瞳 2× 手枪镜保留独立分划和口径。
- 屏幕遮罩、眼位阴影与周边折射使用同一 `GetScopePresentationAlpha`；手枪镜较小孔径不能套用步枪 85% 固定口径后处理。保留清晰中心，不增加第二次场景捕获。
- 镭射落点仍来自真实世界射线及遮挡，不能粘到屏幕分划。近眼光束随 ScopeAlpha 淡出；光点在 bloom 前减弱发光，按当前相机 FOV／深度限制屏幕直径。通过组件独立 Custom Primitive Data 传参，不改共享材质状态、不新增每帧射线或材质实例。
- 低粗糙度金属在枪匠面板发黑时，先区分共享预览灯光和材质问题。面板灯光处理见 UI 技能 [预览渲染](../../ue5-ui-umg-slate/references/preview-rendering.md)，不要用提亮底色掩盖缺少反射光源。

案例记录：`Docs/Weapons/pistol-grip-surface-20260927.md`、`m1911-attachment-polish-20260927.md`、`dw715-muzzle-models-20260927.md`、`scope-optics-refinement-20260927.md`。这些均是游戏美术与表现参数，不是实物加工方案。
