# G18 大弹鼓左手换弹

- 制作参考：手臂技能 `pose-contact.md` 的弹鼓托底和闭合抓握；源方法为 AKM `PalmGripV3`。
- 输入：当前 G18 单持原生 V7 裸手源、G18 大弹鼓 V2 源、步枪鼓壳配准矩阵和掌握参数。
- 输出：`G18_Drum50_Reload_Editable.blend`、普通/空仓两条 FBX、UE 作者动画及一份含两条动作的共享 Profile。
- `author_reload.py` 只改左臂与手指，按目标骨架重新计算掌面语义和累计指段角，不直接照搬供体局部欧拉角；保留右手、枪体、弹匣机械轨迹及动作长度。
- 源时钟托握区间为 0.64–1.135 秒；1.135 秒后先松指，1.215 秒后沿鼓壳外侧退手。普通在 1.48 秒归回原轨迹，空仓在 1.40 秒前交回套筒操作。实际时间随同一换弹倍率缩放。
- 卡片数值位于上一级 `catalog_extension.py`；动作本身不再额外拉长，避免重复乘以 1.5。
- `manifest.json` 定义原基础动作与作者动作配对。`import_reload.py` 完成实际导入保存，并调用共用差量制作器；运行时由 `SVDGripProfiles.cpp` 的 G18 专属分支加载和选择。
- 两条作者动画与 `DA_G18_Drum50` 已实际导入保存，制作器报告 ready=True、retained=0、pending=0。保存回执为 `import_receipt.json`、`install_receipt.json`，桥输出为 `import-mcp-2.txt`。源码常规后台构建成功，见 `compile_receipt.json`。
- 共用制作脚本清空旧层时使用已有的 `SetSharedClipsFromJson` 制作接口，替代对只读 `Clips` 字段的直接写入；无需改变运行时字段权限。
- 未运行游戏、预览渲染或动作验收，由用户测试实际抓握、换弹接触及衔接效果。
