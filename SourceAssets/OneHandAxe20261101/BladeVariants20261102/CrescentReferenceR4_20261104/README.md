> 2026-11-04 材质更新：已改用原厂深灰石洗钢主体和浅银磨刃的同源 PBR，并完成 3 张 PBR、共享改造图标的 UE 保存与发布。当前制作入口及配方见 [FactoryFinish20261104/README.md](FactoryFinish20261104/README.md)。几何和 UV 沿用本版。下文保留原建模记录。

# 钩月斧刃 R4：参考稿模型

2026-11-04：用户以“按照这个进行建模构造”批准 `../CrescentReferenceDraft02/` 的外形进入建模。本目录已完成模型、PBR、FBX、共享改造图标、UE 后台导入保存和游戏视觉登记；模型外观仍由用户评价，未运行游戏测试。

## 构造

- 依据参考图左侧斧头及已选稿构造宽月牙，保留上下双凹刃根、中央厚肩、短后钩与竖直接颈。
- 刃口采用真实楔形厚度，主体以连续厚度场从刃面过渡到中央肩部；深灰碳钢和银色磨刃分区烘焙。
- 原装安装端保持局部 Z=11.5 cm，保留至 Z=13 cm 的原装颈部。两端按实际边界重采样，以 12 段相连截面过渡到新斧头；不使用旧版细杆拼接轮廓。
- +X 为切刃方向，+Z 朝上，沿用原点、`blade_1` 槽和既有 0.01 挂载缩放。
- 成品约 18.36 × 1.70 × 19.88 cm，36,762 三角形，一份游戏材质，2K PBR。几何主要承担近景弧刃、渐变肩厚与原装接颈，继承本武器既有 Nanite 路线；无帧率实测。

## 交付文件

- `SwiftCrescent_Editable.blend`：可编辑模型，PBR 已打包；保留隐藏的原装参照部件。
- `Export/SM_TacticalHatchet_Head_SwiftCrescent_R4.fbx`：实际导入的游戏网格。
- `Textures/`：BaseColor、ORM、OpenGL 切线法线；UE 导入只翻转一次法线绿通道。
- `SwiftCrescent_Icon.blend`、`Icons/blade_1_axe_swift_crescent.png`：实际模型生成的共享金属框灰阶改造图标。图标灰阶处理不修改游戏材质。
- `import_receipt.json`：6 个已保存 UE 资产，分别为网格、材质、3 张 PBR 和共享图标 Texture2D。
- `registration_receipt.json`、`delivery.json`：实际落盘与登记状态。
- `Before/`：本次替换的图标、数据和父级入口备份。

运行时网格为 `/Game/Weapons/TacticalHatchet20261101/ModulesV1/SM_TacticalHatchet_Head_SwiftCrescent_R4`。`tactical-hatchet-modules.json` 中只更新 `axe_swift_crescent` 的视觉配方与刃口采样位置；共享改造表只更新外观说明，数值保持不变。其余两款通用斧刃未在本次重建，也不标记为已获认可。

## 制作入口

`author.py` → `render_icon.py` → `import_assets.py` → `register.py`。父级对应入口已指向本目录。材质烘焙及 FBX 导出沿用现有工具；R2 只提供材质作者函数，不使用其被否决的几何。

无编辑器时通过 `run_import.ps1` 在现有 UE 批次互斥下执行无界面 commandlet；有编辑器时沿用现有 MCP 桥，不启动竞争进程。本次未打开编辑器界面，未启动游戏或追加验收渲染。已加载的游戏实例需要重新进入后读取更新的部件目录。
