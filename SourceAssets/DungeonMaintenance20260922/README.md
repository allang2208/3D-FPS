# 地牢废案归档与手工维修配电区

用户于 2026-09-22 否决地牢 5080 生成物品整批候选。活动清单不再生成或安装这些模型，所有原始产物与被污染的整场景源原版保留在 `../../trash/dungeon-5080-rejected-20260922`。

完整范围、UE 保存结果和恢复边界见 [实施与废案记录](../../Docs/Gameplay/dungeon-5080-retirement-20260922.md)。`Config/retirement.json` 是废案范围；`Config/cabinet.json` 是手工维修柜的尺寸与摆放配置。历史归档脚本是本次迁移记录，不作为普通重建入口重复运行。

后续修改柜体运行 Blender 作者脚本 `Scripts/author_cabinet.py`，再经项目桥运行 `Scripts/install.py`。完整工作间源通过 `DungeonWorkbenchKit20260921/Scripts/assemble_room_source.py` 重建。默认不启动游戏、测试或预览。
