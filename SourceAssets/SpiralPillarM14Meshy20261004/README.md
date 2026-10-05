# 螺柱 M-14：本机模型与公开配方

原始输入为用户提供的 `Meshy_AI_Veiled_Maw_M_14_1004025810_texture.glb`。原文件 66,840,344 字节，SHA-256 `69f13330a914d0c432d93ef1109e846727f80be98ad95029a5088e001826d663`。Meshy 生成套餐与资产公开再分发许可未确立；原模型、PBR、Blend/FBX、骨架绑定、二进制权重、UE 包、日志及回执留本机。

Git 发布 `Tools/SpiralPillarM14` 的原创制作配方，以及本目录 V09/V10 的六份原创 HLSL。版本目录是逐步制作的依赖链，不能仅按版本较旧删除。活体为 V15，连续软体死亡为 V19，绿色毒液为 V16，旋风范围为 V20。嘴部弱点接入统一伤害判定。

先按 [发布与恢复记录](../../Docs/Monsters/SpiralPillarM14Publication20261005.md) 恢复合法输入，再运行对应制作/保存步骤。不要遍历执行全部脚本；中间安装脚本可能恢复旧攻击或旧死亡设置。V17/V18 尸体安装脚本已归档，V18 材质由 `restore_corpse_materials_v18.py` 单独恢复，最终使用 `import_death_and_range_v20.py`。

已保存资产与此前构建回执保存在本机 `source_manifest.json` 及各版 `Records`。本轮仓库整理没有运行游戏、构建或视觉验收，新拆出的材质恢复入口也未执行。
