# SVCH 指定模型替换

用户指定 Sketchfab `b3bb922bdf1a481a96b9e2940b2d26fc` 替换旧枪体，并选择继续使用机械瞄准。源包内部为 MWIII KV Inhibitor；下载元数据、作者、许可标注和完整原始文件保存在 `SourceAssets/SVCHReplacement20261018/`。

## 已制作和保存

- 新枪体取自选定模型的机匣、握把、标准枪管、标准弹匣、枪托及配套弹药。未将备用枪管、备用弹匣和瞄准镜叠装到枪上。
- 枪体及新增机械准星共 57,827 三角面。保留源 UV、颜色贴图和法线细节；粗糙度与金属度为本地材质参数。
- 机械准星含真实镂空照门、准星柱、圆角护耳和转轴。准星位置由新模型几何给出，转换使用实际导入网格的 `WPN_root` 参考变换。
- 为保持认可手型，握把和护木的下部厚度局部收窄，并渐变到原接口。整条手臂仅在锁骨层做位置/方向适配；手腕、手指及其他手臂局部关节姿态不重新设计。
- 弹匣绑定 `WPN_SOCKET_Magazine`，拉栓绑定 `WPN_bolt`，扳机绑定 `WPN_Trigger`。共用动画、机械时钟、R11 换弹回位逻辑保持原实现。
- 原生 V9 裸手引用保持原路径；新枪体的内嵌备用手臂隐藏槽按实际导入槽号注册，并转入原有 18 个修正形态。

运行资产：

- `/Game/Weapons/SVCH/Replacement20261018/SK_SVCH_Replacement`
- `/Game/Weapons/SVCH/Replacement20261018/DA_SVCH_ReplacementGrip`
- 材质与贴图位于同目录下 `Materials`、`Textures`。

接入修改涉及 `SVCHWeaponAssets.h`、预加载表、`modular_outfits.json`、抛壳标定及通用光学/枪口配件的 SVCH 安装点分支。装备光学瞄具时隐藏新机械准星。原厂枪口保留，通用枪口件安装在实际枪口端面。

## 回退与证据

旧模型 `/Game/Weapons/SVCH/Refined20261018/R8Surface/SK_SVCH_R8Surface` 和旧接触配置 `/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip` 未覆盖。旧背包图标备份在本次源目录的 `Before/`。

导入落盘状态见 `install_receipt.json`，标定见 `calibration.json`，图标落盘见 `icon_receipt.json`，构建见 `build-editor.log`。Blender FBX 仍产生多网格 bind-pose 警告；此类警告也存在于旧 R8 导入。本次不把导入完成作为运行变形验收。

本轮仅进行制作、导出、导入保存、必要构建及生产图标生成。未主动打开交互编辑器、启动游戏、执行换弹/ADS/命中回归或生成验收截图。新模型的实际握持、检视、普通与空仓换弹、拉栓及各配件组合交由用户实机确认；历史 R11 通过记录不代表新模型已经验收。
