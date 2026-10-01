# HK416 普通与扩容弹匣：同步 M4 空仓拍击

用户要求普通弹匣和扩容弹匣同步采用上一轮的完整 M4 拍击。两种弹匣均走 HK416 `reload_empty` 分支，因此更新同一组五个动画及对应运行握把层；不改非空仓换弹，也不重导已完成的弹鼓和机瞄分区。

## 动作

- 基础源保留当前插匣、压实和机械轨道，左臂拍击直接复用 `M4SlapImpact20260910/M4_Hand_MAT_Editable.blend` 的 `M4_MAT_reload_empty`。
- 保留普通／扩容的第 130 帧拍击、第 162 帧结束，总源时长 2.7 秒。与弹鼓的第 116 帧拍击、第 148 帧结束分开，不改变换弹数值或音效调度。
- 第 102–122 帧逐步接入完整 M4 左锁骨、上臂、前臂、腕、手指及 twist 关系；沿用前一轮对 HK416 挂机按钮的整臂接触平移，不单独重算肘或转腕。
- 前握把回握窗口从原来的 88–111 帧移至 142–162 帧，保留完整拍击及回弹。覆盖 base / vertical / canted / prism / angled 五套。

## 实际接入

正式动画路径：`/Game/Weapons/HK416/Reworked20260930/Animations/<family>/A_HK416_<family>_reload_empty`。

游戏优先读取 `/Game/Weapons/AnimationProfiles20261001/ue_hk416/DA_<family>` 的动作修正层，导入后同步重烘四款前握把的 `reload_empty` 项，保留同一资料里的弹鼓及其他动作。没有原厂／扩容专用条目的 drum profile 不新增无用条目。

制作源、FBX、备份、导入脚本与保存回执位于 `SourceAssets/HK416StandardEmptyReload20261001/`。`HK416CommonAttachments20260930/author_animations.py` 新增互斥的 `--only-standard-empty` 参数；完整制作同时包含普通与弹鼓空仓动作。`import_grip_profiles.py` 共享实现两种空仓层的刷新，旧弹鼓入口保留兼容。

本轮没有 C++ 修改，不需要重新编译。导入使用既有编辑器桥或后台 commandlet；若正在 PIE 或目标包存在未保存编辑，先保留现场。资产是否已写入以 `import_receipt.json` 为准。未运行游戏测试，观感由用户测试。

## 本轮落盘记录

用户退出 PIE 后，通过现有编辑器完成五套动画和四款运行握把资料保存，保存回执已逐项记录。2026-10-01 15:01:31，编辑器在末尾发生 PythonScriptPlugin / python311 访问冲突，桥连接中断；最后一项 DA_angled 已于 15:01:29 保存。源动画目录表和最终回执随后在外部 Python 中补完，没有重新启动编辑器，也没有重新导入已保存资产。

共享握把导入函数不再跨 `BakeClip` 保存 `Clips` 数组元素的 Python 反射视图：先读取旧时长为普通浮点值并释放视图，再重建数组，避免失效视图访问。崩溃原因尚未确认，未重跑验证该问题。
