# SUPER90 弹药模型与轮盘图标修复

## 模型制作与接入

此前弹药交付包含数据、玩法和 PNG 图标，没有新增三维模型。本次参考项目现有 5.56／7.62 开口纸盒模型，制作三种弹药盒和三种独立弹壳：鹿弹红壳、箭型弹橄榄色壳、独头弹蓝壳。每盒展示两排共十发，仅为包装外观，不改变游戏弹药数量或制作配方。

模型使用厘米单位，包含纸板实体厚度、内衬、翻盖、文字、塑料壳纹路、封口和金属底座。纸板、塑料与金属分别使用材质槽；纸板颗粒由 Blender 原生节点烘焙。三种弹药盒接入 `AColdSteelPickup::BuildConsumable`，按稳定弹药 ID 选择资产，兼容原有保存的掉落记录。`items.json` 的 `world_mesh` 与打包目录同步补齐。

- UE 目录：`/Game/Items/Ammo12Gauge20261012`。
- 源文件：`SourceAssets/Ammo12Gauge20261012/Models/ShotgunAmmoModels.blend`。
- FBX／槽位／面数清单：同目录 `manifest.json`。
- 导入脚本：`SourceAssets/Ammo12Gauge20261012/import_models.py`。
- 保存回执：`SourceAssets/Ammo12Gauge20261012/model_import_receipt.json`。

独立弹壳作为可复用道具资产交付；本次不替换 SUPER90 已认可的原生换弹网格和动画，也不把整发弹壳用作飞行弹丸。弹药仍按已有数值弹药袋机制存储。

## 轮盘排查与修复

范围限定 SUPER90 三种弹药。三张实际 PNG 均存在，UE 原生图像加载器均成功解码为 1254×1254，排除了缺文件和 PNG 损坏。

后台实际绘制复现了三张图全空白，尽管三个纹理对象均已加载。直接原因是图片与不透明凹槽底板共用同一绘制层，Slate 合批后底板遮住图像。将底板、图标、文字、指针分别放到 +4、+5、+6、+7 层后，相同诊断条件下三张图片全部可见。对照图为 `Saved/ShotgunAmmoModels20261012/wheel-reopen.png`（修复层级前）与 `wheel-layers.png`（修复层级后）。

同时修复两层失败缓存：`AmmoIconBrushes` 保存空画刷，`FramedIcons` 再缓存该空结果；旧代码再次打开轮盘不会重试，文件就绪后仍可能没有图标。修改为每次打开轮盘清理裁切画刷，在打开阶段对失败的共享图标重试一次。成功加载的纹理继续复用，绘制期间不循环读盘。三选项轮盘的名称和数量调整到图片下方，下方两张图片向上留出文字空间。

后台诊断入口 `ShotgunAmmoIconDiagnosis` 直接使用实际 `OpenForWeapon`、`AmmoIcon`、`FramedIcon` 和 `NativePaint`。它创建独立内存中的 SUPER90 条目，不初始化玩家档案、不加载或写入存档。`-ReopenAfterMissingIcon` 在内存目录临时模拟首次图片缺失，再恢复路径并重新打开，用于排查上述持续空白问题。

最终六个模型已通过后台导入保存，日志 `SourceAssets/WeaponSurface20260930/logs/import_models.20261012-220113-531.log` 包含 `AMMO_MODELS_SAVED 6`，进程退出码为 0。后台静态网格制作显式加载 `StaticMeshEditor` 模块，支持编辑器子系统尚未自动实例化的 commandlet 环境。日志另有营火 CDO 缺少资源的工程既有错误，与本次弹药资产保存无关，没有修改该营火资产。

正式 Editor 构建和诊断结果见生产回执。后台图标复现不等于完整 PIE、换弹交互或三维模型视觉验收；实际游戏效果由用户测试。其他口径没有扩展检查。

最终构建成功（`Saved/BuildEditor/shotgun-models-wheel-final.stdout.log`，10.59 秒）。`wheel-final.log` 记录模拟首次缺图 `initial_missing=1` 后，重新打开轮盘的三个图标画刷及纹理均有效，进程退出码为 0。已直接查看 `wheel-final.png`：三种图标可见，名称和数量位于图片下方且不重叠。本次没有启动 PIE，没有加载或写入玩家档案。
