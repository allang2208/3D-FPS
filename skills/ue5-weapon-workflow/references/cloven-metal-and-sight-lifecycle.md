# 裂角护手金属与独立瞄具生命周期

## 护手沿用剑身金属

用户指定剑身金属时，从当前实际母材质和同源 PBR 贴图取样，不另外猜底色、粗糙度或法线强度。整剑图集直接绑定护手的新连续 UV 会采到符文、皮革和宝石；先从真实剑身钢面三角形提取样片，按物理纹理尺度转移四路贴图，周期衔接边界，保留翼面纹饰边和根部过渡。法线需要转到新 UV 的切线基。

复制当前剑身材质图作为独立 UV 适配副本，只替换四路纹理；沿原护手槽绑定，保留宝石、暗槽与嵌纹。当前配方为 `SourceAssets/HighlandClaymoreMeshy20260922/ClovenSurface20261002/BladeMetal20261002`，仍读取上一轮连续 UV 的 Blend 和 `surface_transfer.npz`，它们是制作依赖。上一层默认安装器恢复旧表面；当前金属必须通过 `install_background.ps1 -Script <install_blade_metal.py 的绝对路径>` 接入。

## 悬浮机瞄先查组件归属

截图和最近使用的枪只能帮助定位，不能证明残留组件属于那把枪。用户保留现场且授权读取时，记录 mesh、owner、parent、socket、visibility 和 hidden-in-game，区分装备视模、拾取物和制作 Actor。本例读到的其实是隐藏 M4 上独立的前后机瞄，M16 原装机瞄位于自身骨骼网格内。

独立附件在 RegisterComponent 前按宿主状态初始化可见性；更新时所有现有附件先跟随主视模，再判断是否凑齐一对或更新折叠角。枪匠 setter 也必须尊重主视模可见和 hidden-in-game，不能稍后只按枪型／装备标志重显。递归隐藏一次不能覆盖迟创建组件和后续 setter。

本例保留现有网格、挂点、折叠和材质，只修可见性来源。详见 `SourceAssets/SightResidualDiagnosis20261002/README.md`；现场读取、源码修复、正式 DLL 落盘与修复后用户测试是不同状态。
