# 疾雷 V14 游戏接入

2026-10-31，按用户“接入游戏”完成。范围为疾雷锤座 V14，不包含尚未另行授权接入的贯雷 V12 候选。

已保存 `/Game/Weapons/ThunderGodHammer20261028/JiLeiInlaidLightningV14` 中的网格、5 款独立材质和 9 张 4K PBR 贴图；原厂圆徽和接口复用当前 `M_ThunderGodHammerSurface`。新版疾雷灰白金属框图标已覆盖实际加载的 PNG 和 Texture2D，旧图及目录保存在本文件夹 `Backups`。

`Content/ColdSteelData/thunder-god-hammer-modules.json` 的 `slots.head_mount.ji_lei_seat` 已指向新网格。`thunder-god-hammer-gunsmith.json` 仅更新对应外观和介绍文字，传说品质、攻击速度 +20%、落雷、感电、蓄力、范围及伤害参数没有改动。沿用原安装位置和 `thunder_god_hammer_modular_v1` 接口。

437,372 个源三角形作为 Nanite 源网格，显式切线与完整回退几何保留。完整回退仍有几何成本，没有性能测试或帧率改善声明。新表面材质使用单面不透明 Substrate；ORM/Normal 为线性，BaseColor 为 sRGB，法线翻转绿通道，纹理保持流送。已有 `/Game/Weapons/ThunderGodHammer20261028` cook 目录和图标 UFS 目录覆盖本次资产，无需新增打包规则。

入口：`prepare_materials.py` 读取已认可 Blender 源，保留原 FBX；`install.ps1` 使用已有编辑器桥或后台 commandlet；`import_assets.py` 创建并保存资产；`publish.py` 只合并疾雷视觉字段，并保留并行改动。首次导入的发光引脚命名错误已修正，随后从已保存材料继续接入。

交付记录：`runtime_manifest.json`、`import_receipt.json`、`publication_receipt.json`。最终 commandlet 完成并保存 16 个资产，目录发布完成。本次没有 C++ 改动，不需要原生构建；未运行游戏、未作实机视觉或性能测试。

图标由内置 imagegen 使用实际 V14 模型图和已认可金属框母图制作，源图为 `ji_lei_seat_framed.png`，完整提示词见 `icon_prompt.txt`。没有用图标生成结果替换三维几何。

游戏目录有进程内缓存，下一次启动游戏加载新版本；本次不自动启动或重启编辑器。
