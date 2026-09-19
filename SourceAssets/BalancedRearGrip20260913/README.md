# 均衡后握把

按用户参考图与通用模型工作流制作。对象为实心黑色聚合物后握把，保留短上翘尾部、宽侧浅凹面、前缘横向防滑纹和封闭底部。

## 设计属性

`balanced_reargrip` / 均衡后握把 / reargrip。

- 后坐力控制 +10%：已接入 `recoil_mult=0.9`。
- 枪械稳定性 +10%：依据当前枪匠 Shake 字段，已接入 `shake_mult=0.9`。
- 制作记录见 `design.json`。用户已选定 A（91703），现已完成三枪资产与枪匠接入，尚未游戏测试。

## 输入及制作入口

- 原图 `reference.png`；三视图 `three_views.png` 由内置 image_gen 生成，完整提示词 `reference_prompt.txt`。背面依据同一造型推断。
- ComfyUI 将 1774×887 参考分为 x=0/650/1124、宽=650/474/650 的三张视图，分别去背景；宽侧→front/back，窄侧→left。
- TRELLIS.2-4B 多视角、1024_cascade、SS64、16/32/24 步、4K、50 万面母版导出目标。两份候选种子 91703 / 91727。
- `generate.py` 提交/下载，`wait_download.py` 等待本批回执，`save_editable.py` 保存 Blender 源文件且不启动渲染。
- 各 seed 目录保留工作流、回执、执行历史、raw GLB、带纹理 GLB及可编辑源。实际生成状态以该目录 history 为准。

未进行游戏测试或验收渲染；未替换已选中的幻影后握把。原始参考的第三方权利不因生成而改变。

## 生成交付

91703、91727 两份执行历史均返回 success，raw 与带纹理 GLB 已下载，Blender 可编辑源已保存。用户认可 A（91703）。A 已接入 M4、AKM、QBZ-191 的后握把选项并应用上述数值；B 保留为未选候选。逐枪材质与导入记录见 ../RearGripFinish20260913/README.md，游戏效果由用户测试。
