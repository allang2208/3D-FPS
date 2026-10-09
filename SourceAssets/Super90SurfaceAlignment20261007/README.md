# Super90 枪体贴图与刻字坐标调整

用户反馈：改造预览的机匣仍有错位图块，原厂字样落到了后握把。

## 原因与制作改动

原始 FBX 的 UV 使用源 PNG 的左上图像坐标。机匣左侧 UV 岛 U=.3591–.4174、V=.2255–.5544，右侧 U=.7315–.7894、V=.6712–.9980，与源图两块刻字面板吻合。旧制作流程误用另一份 GLB 的旋转元数据，在 Blender 中写成 `(1-u,1-v)`，额外镜像 U。当前改为 `(u,1-v)`，并迁移旧版本网格，重新按源金属图分配 WS1 金属、聚合物、金色小件及橡胶区域。

枪体源法线 PNG 为 DirectX，和 GLB 转换图在绿通道反转后才一致。UE 关闭该枪体贴图的 `flip_green_channel`，Blender 编辑源独立将其转换为 OpenGL。其余法线图、公共母材质、枪体几何、骨架、权重、手臂、动作及配件功能保留。

制作入口仍为 `../Super90WS1Surface20261007/author_surface.py`，主制作入口复用同一 `mapping.py`，不会再次加错水平翻转。保存入口是本目录 `apply_alignment.py`，使用现有编辑器桥批次；成功后执行 `../Super90WS1Surface20261007/publish_source.py` 同步正式可编辑源与 FBX。

旧文件保留在 `Before/`。`author_inputs.json` 记录修复所需的原始输入，`current_inputs.json` 记录现用材质；实际保存结果以 `import_receipt.json` 为准。未运行游戏、截图、渲染或自动测试，视觉结果交由用户确认。

## 已落盘

用户退出 PIE 后，通过现有 UE 桥执行 `apply_alignment.py` 成功，保存了 23 份网格、贴图、材质及相关安装座资产；回执为 `import_receipt.json`，桥输出为 `apply_alignment_after_pie_response.json`。随后执行 `publish_source.py`，将修正后的 Blender 文件和 FBX 同步到 Super90 正式制作源。未启动游戏或进行测试，无需 C++ 编译。
