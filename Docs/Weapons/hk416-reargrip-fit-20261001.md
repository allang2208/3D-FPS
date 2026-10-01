# HK416 通用后握把衔接修复

用户要求重新检查并修复后握把衔接。本次仅处理 HK416 的幻影、稳固防滑、均衡三款通用后握把。原装 416 后握与机匣相接正常，未修改；其他枪型、属性及手部动作未改。

## 原因与修复

旧作者入口保留了 M4 的顶部翘尾与连接座，将 Z > 8 mm 的点压缩到约 24.93 mm，并增加独立的 22 × 22 × 4 mm 方垫块。高度接近不代表安装轮廓相同：幻影和均衡顶部有明显空隙，防滑握把有外露台阶。局部灰模对照保存在本次 SourceAssets 目录的 `before_*.png`。

从 HK416 原装 `Hand_grip_low` 提取 Z ≥ 10 mm 的安装面，逐点保留机匣端轮廓、UV 和自定义法线。移除三个旧 M4 顶部及垫块，以各自真实握把截面重做连续接颈。握持区保持原位置、尺寸和 UV，不对全握把拉伸或整体减面。

过渡下端分别为幻影 Z = 0 mm、防滑 Z = -12 mm、均衡 Z = -3 mm；新接颈的闭合底面埋入保留主体 0.6 mm。源握把有重叠壳和碎边，因此按实际表面截线取外轮廓，未把全部边界硬串成一圈。下端使用两端截面的方向，上端沿原装表面切线过渡，避免从重叠壳提取不稳定斜率形成褶皱。新接颈封闭不表示既有握持主体的全部历史拓扑都已重建。

沿用 `HK416_InterfaceSteel` 对应的 HK416 接收机匹配材质及三款已有主体材质，保留现有干燥/雨湿绑定。未新增白模材质。

## 接入与复现

- 作者入口：`SourceAssets/HK416RearGripFit20261001/author_models.py`；`Inputs` 保留本轮修复前的三个可编辑源，`Meshes` 为最终 FBX/Blend。
- 共用算法：`SourceAssets/HK416CommonAttachments20260930/reargrip_interfaces.py`。
- 原通用配件 `author_models.py` 已改用新算法；`models.json` 的三个 FBX 来源已更新，其他条目保留。
- 三个既有游戏资源 `/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_{phantom_reargrip,stable_antislip_reargrip,balanced_reargrip}` 已重导并保存。导入继承即时读取的材质绑定，路径和配件 ID 不变。
- 导入通过当时已运行编辑器的批次互斥桥完成，没有启动或重启 UE。见 `import_bridge.json`、`import_receipt.json`。

## 用户要求范围内的检查

`inspect_result.py` 检查了三款新接头拓扑及正反两侧局部装配。每个新接头开放边和非流形边均为 0；原装接触面顶点最大偏差约 3.42e-8 m，来自坐标变换浮点误差。局部效果为 `after_*_side.png`、`after_*_opposite.png`，属于离线灰模装配检查，不是游戏截图。

未启动游戏，未进行实机、动作或一般回归测试；实机外观由用户确认。
