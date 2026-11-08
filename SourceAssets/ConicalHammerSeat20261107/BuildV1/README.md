# 锥形锤座 BuildV1

2026-11-09 整理：被否定的带框图、带框 Blender 场景和旧回执已带散列归档。author_icon.py 现在只生成仍被 IconV2 使用的实际灰模参考；import_assets.py 只导入认可的 IconV2 图，不再覆盖成 V1。以下旧带框说明仅为历史。

> 图标更新：用户于 2026-11-07 否定本版 Blender 自制框图。当前图标为 `../IconV2/head_mount_conical_seat.png`，使用认可母版与实际模型双参考经 imagegen 重新生成；不要重新部署本目录旧图标。模型与 PBR 资产仍为本版。

> 后续接入：用户已认可 IconV2 并授权通用改造、旧前顶动作、范围击退和被动数值接入。当前运行接入记录见 `../IntegrationV1/README.md`；本页下方“玩法状态”保留本版制作当时的历史边界。

2026-11-07。按用户要求制作实体模型、法线贴图及沿用现有标准的改造图标。

## 制作产物

- 锻钢战锤和符文战锤各一套原生接口模型，保留各自锤头侧接口、下方锤颈接口与零点，不对原厂模块统一缩放后硬套。
- 实体八切面尖锥、阶梯承力肩、车削套环、倒角面板、真实凹刻双折线、沉入式紧固件和开槽钉头。锻打、拉丝与细小磨损烘焙进材质贴图。
- 每套独立 4096 × 4096 BaseColor、ORM、切线空间 Normal，共六张 PBR 贴图。作者法线为 OpenGL；UE 导入设置翻转绿色通道。ORM 为 R 遮蔽、G 粗糙度、B 金属度。
- 单套模型一个材质槽。细节几何约 4.4 万／4.9 万三角形；当前提供细节版，未进行性能验收。Nanite 关闭。
- 唯一共享改造图标 `head_mount_conical_seat.png`，1024 × 1024 RGBA。实际模型灰阶渲染，厚倒角金属方框、四角铆钉、银色内圈、深灰不透明底板和少量框外透明边，无文字。保留图标作者场景和未加框的模型源图。

## 方向与接口

尖锥沿作者坐标 +Z 伸出，对应旧版锤头前顶动作的接触端，不沿中央锤座侧板的 Y 法线。FBX 使用 -Y forward / +Z up，组件位置维持 0,0,0。

Steel：左右接口 X=-0.04/+0.04 m，下接 Z=0.865 m；尖锥长 10.42 cm。

Runebound：左右接口 X=-0.0354452141/+0.0345547859 m，下接 Z=0.842 m；尖锥按该原生锤座宽度制作，长 9.1175 cm。

## 文件

- `ConicalSeat_Steel_Construction.blend`、`ConicalSeat_Runebound_Construction.blend`：未合并的结构制作阶段，保留实际接口参照。
- `ConicalHammerSeats_Editable.blend`：两套完成 UV、烘焙与合并的最终模型。
- `Export/`：两套 FBX、嵌入材质纹理的 GLB。
- `Textures/`：六张 4K PBR 贴图。
- `Icons/head_mount_conical_seat.png`：共享母图；`ConicalSeat_IconSource.blend`：实际模型与金属框的图标作者场景。
- `production_receipt.json`、`icon_receipt.json`、`import_receipt.json`：制作和 UE 保存回执。
- `author_model.py`、`native_interfaces.py`、`solid_surface_tools.py`：模型与烘焙作者脚本。`finish_export.py` 将 glTF 导出步骤清理后的网格重新输出 FBX，避免先导出的 FBX 与最终保存模型不一致。
- `import_assets.py`、`import_background.ps1`：同一资产批次互斥下的后台导入与保存；不启动编辑器界面、不运行游戏。

UE 资产已通过后台 commandlet 导入并保存到 `/Game/Weapons/CommonHammerSeats20261107/ConicalSeatV1`，共 11 个资产（两模型、两材质、六贴图、一图标纹理），完成回执见 `import_receipt.json`。

共享 PNG 已同步到 `Content/ColdSteelData/AttachmentIcons20260913/head_mount_conical_seat.png`，对应当前近战改造面板的共享图标命名与查找路径；发布记录见 `icon_publication.json`。未为不同宿主重复创建专属图标。

## 玩法状态

本轮制作资产，不发布到运行中的改造选项表，不修改现有双手锤快速近战动作。

后续接入要求已保留：选装此锤座时复用 `QuickCombatLeftWristV7/A_Warhammer_QuickCombat` 的旧前顶动作，前方范围快速近战与击退；将当前武器伤害代入现有快速近战公式，物理伤害 +5%、快速近战伤害 +20%。范围和击退参数尚未确定，不能将这些玩法描述为本轮已生效。

未追加游戏测试、动作验收、装配预览或性能测试，由用户测试。图标渲染属于用户要求的资产制作。
