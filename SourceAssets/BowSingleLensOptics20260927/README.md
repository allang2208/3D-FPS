# 弓单镜片二倍／四倍瞄具

已按用户认可的开放薄框设计制作并接入。两款均为一片闭合微凸玻璃、薄钢框、暗黄铜窄压圈、钢制弧臂、当前 V19 贴合木座与嵌槽绑线。

| 选项 | 固定倍率 | 开镜耗时 | 分划 |
| --- | --- | --- | --- |
| 清野二倍镜 `bow_clearfield_2x` | 2× | +10% | 细十字与小中心点 |
| 远望四倍镜 `bow_farwatch_4x` | 4× | +25% | 细十字、中心点、下方两道无距离标注刻线 |

`ads_mult` 沿现有合同同时影响入镜／退镜时长。伤害、子弹速度、拉满、搭箭、散布与耐力不额外改变。光学倍率以原装弓满 ADS 为 1×，半角正切计算 FOV；沿原动作权重过渡，灵敏度跟随相机视野。

后续用户修订：两款参照枪械 `prism_scope_2x` 的实体瞄具表现，保留弓、手臂、实体镜框、镜片分划、周围视野与 HUD。相机分别提供 2×／4× 放大；取消弓的全屏圆形遮罩和高倍镜隐藏请求。现有模型及实体玻璃直接复用，无需重导。

分划清晰度修订：原 0.07 mm 深色几何线由镜片 UV 抗锯齿分划替代，使用低亮度绿芯、窄暗边、约 3.6 渲染像素中心点及最小 1.15 渲染像素线宽，长刻线向镜框逐渐减光；4× 保留下方两条参考线。三个实际运行材质已保存，源码与回执见 `ReticleReadability/`。原刻线几何在网格中保留但材质隐藏，当前运行分划以该目录作者代码为准。未测试。

## 来源与制作

- `Concepts/accepted-single-lens-design.png`：本对话已认可的概念参考；倍率画面仅为示意。
- `author_assets.py`：原创镜框、支臂、单片玻璃、实体分划；复用当前 `BowWoodBracket20260927/author_sight.py` 的弓体表面投影、木座与绑线构造。只运行旧脚本的底座构造前缀，不改写其资产。
- 木纹 UV／贴图沿用保留的 `WoodLongbow20260925` 来源；UE 复用 `WoodBracketV19` 的木材、蜡麻材质。金属细纹 ORM 与法线为本次程序化原创。
- 四款当前弓体共用未变形安装区域，源依据 `BowBodyVariants20260926/author_bodies.py` 的受保护中心区域与 `BowFlex20260927/author_bodies.py` 根骨权重。底座覆盖 Z=13.65–18.75 cm，保持在该范围内。
- 原始尺寸用 UE cm，导出前反转 Y；前方 +X，上方 +Z。光学中心 `(-3.5,-10.1,16.5) cm`；目距 60 cm。外径 4.5／4.8 cm，轴向框厚 0.34 cm。
- `Bow_SingleLensOptics.blend`、`Export/*.fbx`：游戏模型可编辑源与导出。玻璃、分划、木座、金属独立材质槽，同一个静态网格接入瞄具槽。
- `Bow_SingleLensOpticIcons.blend`、`Icons/*.png`：实际模型导出的 1024×1024 透明灰阶图标，保留玻璃透射、木纹和金属粗糙度。水平正交视角由侧面向后转 35°，无二维镜像。只在独立图标材质副本去色。

## 已落盘

- UE 根目录：`/Game/Weapons/DarkBow20260925/SingleLensOptics20260927`。
- 11 个新增已保存资产：2 网格、5 材质、2 金属贴图、2 图标 Texture2D；`import-receipt.json` 记录实际保存与来源散列。
- `install_config.py` 已更新 `bow-gunsmith.json` 的 sight 槽、原装／拆除的 1× 状态、正式 PNG 及 `DefaultGame.ini` Cook 路径；安装前副本在 `Saved/BowSingleLensOptics20260927/Before`。没有替玩家修改已装备选项。
- 应用、撤销、选择存档继续使用原有 `gunsmith_parts`、`ResolveBowVisual` 路径；无新存档格式。实体玻璃可用于装备和三维改造预览。
- 原生新增字段放在 BowWeaponComponent 尾部；装备刷新缓存倍率，镜内绘制不解析 JSON、不同步加载资产、不增加 SceneCapture。
- 复用同轮成功构建 `Saved/BuildEditor/build-20260927-204103.log`。该构建编译本次五个相关实现单元并链接 `UnrealEditor-FPSGAME.dll`，未再排队重复构建。
- 资产后台导入：`install.20260927-204308-024.log`，commandlet exit 0。初轮透明材质赋值已改用 `set_editor_property`，保存失败的初轮没有发布目录。
- 后续实体瞄具 ADS 修订：`M4GunsmithVisual.cpp::GetScopePresentationAlpha()` 对弓返回 0，原有实体视模／HUD 恢复流程解除高倍隐藏，`AimVerticalFOV` 保持 2×／4×。2026-09-27 21:28:59 已通过现有桥 Live Coding 编译并应用到正在运行的编辑器，见 `OpenSight/compile-result.json`；本次未更新基础 Editor DLL，常规构建待编辑器关闭后完成。

发布整理时将已取消的 `BowScopeDrawing.h` 全屏分划及调用分支移出当前源码；该整理尚未重新构建。未启动游戏、未测试或进行实机视觉验收；由用户测试。已有概念图不代表实机倍率或接触验收。
