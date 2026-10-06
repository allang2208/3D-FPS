# RSH-12 轻型快拔握把

RSH 专属 `grip_body / rsh12_quickdraw_grip`。与加重握把互斥，可组合三种已有 `reargrip` 防滑纹。

模型从已接受的原厂 `9_l` 握持外壳出发，保留上端接口、掌面和手指接触轮廓；新增石墨灰薄框、独立防滑掌面、沿背部曲面的浅装饰槽及内收圆角短尾。握把本体和防滑纹使用独立静态网格。没有调整已接受的手臂动作和握点。

## 产物

- `RSH12_QuickDrawGrip_Editable.blend`：分件作者源、装配参考与打包材质。
- `Exports/SM_RSH12_QuickDrawGrip.fbx`：原生组件参考空间本体。
- `Exports/SM_RSH12_QuickDrawGrip_Surface.fbx`：独立防滑表面，物理尺度 UV。
- `Exports/SM_RSH12_QuickDrawGrip.glb`：独立完整模型。
- `Textures`：2K BaseColor、ORM、OpenGL/DirectX 法线。
- `Integration20261005/QuickDrawGrip_Framed.png`：实际模型图制作的正式灰阶金属框图标。

## 数值与接入

- `equip_speed_bonus: 1.0`：拔出速度提高 100%，动画及装备阻塞时间为原来的 1/2。
- `ads_percent: -0.20`：开镜耗时降低 20%，按现有 ADS 加法规则叠加。
- `recoil_mult: 1.05`：后坐力增加 5%，按现有后坐力乘法规则叠加。
- 单持读取已装备枪匠数值；双持每只手在装备开始时读取自己的数值。只有无支撑前握把的增益受现有双持限制，后握把效果保留。
- 复用本体替换、原厂 section 显隐、枪匠预览、落地武器和装备实例存档路径。
- UE 路径：`/Game/Weapons/RSH12/QuickDrawGrip20261005`。
- 正式图标键：`ue_rsh12_grip_body_rsh12_quickdraw_grip`，部署至 `FramedFirearms` 及旧根目录，并保存 UI Texture2D。

## 制作来源与执行状态

上端握持形面来自 Medji 的 Rsh-12（CC BY 4.0）；署名见 `Docs/ThirdParty/RSH12-Medji-CCBY4.md`。新外饰和 PBR 由 Blender 作者脚本制作，正式图标由内置 imagegen 依据实际网格图和统一框母版制作；提示词保留在 `Integration20261005/icon_prompt.txt`。

导入、目录发布、基础 DLL 构建分别由对应 receipt 记录。只完成制作和必要构建，不启动游戏、不执行测试或验收；游戏表现交由用户测试。
