# 百目炉渣：黑烟可见性修复 V21

用户反馈扩大 50% 后看不到烟雾，靠近怪物仍触发目盲。本次只处理黑烟显示链路，保留当前三种攻击、伤害、竖劈眩晕、动作、蒙皮、死亡和布娃娃。

## 针对性排查

- 运行代码仍以每秒 8 粒设置发射率，Radius 从 260 乘以 1.5 得到 390 cm。身上三个出生位置与漂移参数的类型和写入方式一致。
- V20 作者脚本写入旧字段 `bInterpolatedSpawning=false`，UE 5.8 实际资产仍是 `InterpolatedSpawnMode=Interpolation`。V21 使用真实字段 `RunUpdateScript`，出生时运行更新但不插值世界出生参数；年龄参与开方前限制在 0–1。
- 模板发射器仍有 ±100 cm 固定边界。运行系统边界原本可以覆盖模板边界，因此不能把这一项单独认定为消失原因。V21 的 CPU 发射器使用动态边界，运行烟迹边界按照实际 Niagara 组件变换转换为局部空间。
- 原材质面向短暂爆燃余烟，使用整个逐渐衰减的 Mantaflow 图集，并随年龄增加密度侵蚀，与 8 秒浓烟保留不匹配。V21 复制成怪物专属材质，在保留阶段使用图集较浓的翻卷区段，取消材质提前侵蚀；粒子 Alpha 从 0.50 调整为 0.65，最后 1.5 秒仍由粒子包络平滑消散。保留软边、红通道密度和深度交界淡化。

未取得游戏内粒子或画面证据，不能把这些配置问题说成已经视觉确认的唯一根因。无界面诊断世界没有产出粒子缓存帧，该结果也不能作为游戏发射失败的证明。

## 保存与接入

当前作者入口：`SourceAssets/HundredEyedSlagMeshy20260930/SmokeVisibilityFixV21/author_visible_body_smoke.py`。密度源码：同目录 `PersistentBodySmoke.hlsl`。V20 制作源已归档，UE 资产仍留在本机；恢复位置见 Publication20261002/archive-manifest.json。

新的运行引用：

- `/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/NS_SlagBodySmoke`
- `/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/M_SlagPersistentBodySmoke`

`SlagBlackMist.cpp` 的构造与补加载引用均切换到 V21。世界空间出生位置、缓慢上浮、50% 线性扩大、8 秒保留、1.5 秒渐散、每秒 8 粒（约最多 76 粒），以及只在浓烟内目盲、离开即解除的规则保留。

后台资产落盘与常规 Editor 玩法模块构建分别记录在 `asset_installation.json`、`build_installation.json`；完成回执为 `installation_complete.json`。这些回执只代表制作、保存和构建，不代表游戏效果验收。未启动交互编辑器、游戏或 PIE，交由用户测试。
