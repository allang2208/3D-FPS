# 必要恢复输入（本机保留）

- `NightWarden_CompleteBody_PreHandRepair.blend`：从 V10 提取完整原始皮肤与原生骨架，去掉旧服装和动作，145849 顶点、46 骨；供 V14 左手权重修复重建。原对象名保留为 `NW10_CompleteOriginalBody_Source`。
- `RampageBiped/Motion/native_walk.json` 和 `Source/rampage_biped_source.json`：V18 的原生重定向与供体输入；由 read_biped_source_v17.py、retarget_rampage_stride_v17.py 维护。
- `RampageBiped/Motion/rampage_keys.json` 和 `Records/motion_manifest.json`：已否定 V17 的诊断对照，禁止当作当前成品重新安装。

这些文件不随 Git 公开，包含用户模型和 Epic 动作派生数据。源/目标散列保存在本机 Closeout20261017/recovery-copies.json；旧目录归档后，活动脚本不从 trash 读取。
