# M24 水平碳纤维后托接缝修订

本轮针对 `M24HorizontalStock20261106/VisualReview/Current/` 用户要求截图后发现的接颈扇形折痕、细缝和原厂前段异常大三角面进行制作。

## 修改内容

- 后托继续使用用户指定的 `Meshy_AI_Carbon_Stock_1105135808_texture.glb`；保持水平、上一版刚体位置、比例、主体 UV 与原始面角法线。
- 接颈不再按极角重排截面点。沿实际边缘遍历、以顶侧中点对齐、按周长对应轮廓，通过不同点数的环带逐段缝合到原边界，并焊接两端。
- 过渡曲面的端部切向来自两侧源表面法线，缓和接头处的斜率变化。新增面生成独立有效 UV，原碳纤维底色和 NormalDX 材质绑定沿用。
- 原厂旧转接件把非平面的宿主边界映射到同一后端截面，造成折叠。现从原枪源找回被替换的 309 个三角面，保留其前部真实宿主边界，仅在 Y=100 mm 后方截断，再连续接到 Y=50 mm 的现有尾座。
- 原厂新过渡沿用原厂机匣金属，先进版本沿用先进机匣金属。

## 文件与接入

- `M24_HorizontalJointClean.blend`：可编辑源。
- `author_joint.py`、`joint_geometry.py`、`native_front.py`：可重放的制作流程。
- `Exports/SM_M24_CarbonSpine_Native.fbx`、`Exports/SM_M24_CarbonSpine_Advanced.fbx`：两种导出。
- `Inputs/`：本轮读取的当前机匣与碳纤维后托。
- `Before/`：本轮发布前两项正式资产的备份。
- `stock_construction.json`：实际构造记录。
- `publish.py`、`run.ps1`：通过现有互斥桥，在当前编辑器或后台 commandlet 中导入、写回原稳定引用并保存。遇到 PIE、目标包未保存或磁盘哈希变化会保留现场。
- `saved.json`：资产保存回执；以 `complete: true` 表示本轮两项正式资产完成保存。

覆盖范围仅为 `/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native` 与 `SM_M24_CarbonSpine_Advanced`。保留现有三档 LOD 和材质引用，未改动独立瞄具导轨、枪机、握把、动画或玩法。

本轮未追加游戏测试或验收截图；前一轮截图仅作为缺陷依据，不代表本轮视觉验收通过。

## 保存结果与限制

2026-11-06 13:44，两项正式资产由后台 commandlet 保存完成，`saved.json` 为 `complete: true`。Native 三档三角数为 199938 / 99968 / 39987，Advanced 为 209091 / 104545 / 41818。

初次 FBX 导入日志出现退化切线、近零切线/副法线提示，Advanced 还出现近零法线提示。发布流程随后执行现有 `bake_stock_tangent_basis`，从构建后的角点基底重新写回三档 LOD 并保存；该步骤返回成功。本轮没有独立读回或渲染验收，不能据此宣称所有着色问题已经通过视觉确认。完整导入记录为 `publish.py-20261106-134232.log`。
