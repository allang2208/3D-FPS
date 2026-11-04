# 钩月原厂同源材质

用户要求“参考原厂的材质处理，统一处理刃口和主体的材质”。本次采用原厂 `M_TacticalHatchet` 对应的实际 PBR，替换 R4 的程序灰钢表面；保留现有网格、UV、安装接口、动作和数值。

- 从原装斧头钢面三角形对应的图集区域分别提取深灰石洗主体和浅银磨刃，不直接套用包含握柄等区域的整张图集。
- BaseColor、粗糙度、金属度和切线法线取自同一原厂样片，以源三角形的 UV 梯度确定物理纹理尺度，只处理样片的平铺边界。
- 保留 R4 原有的刃口分区，磨刃纹理沿月牙调整方向。法线经当前模型的作者切线基换算，UE 保持 OpenGL 法线翻绿一次。
- 源文件仍为上级 `SwiftCrescent_Editable.blend` 与 FBX，游戏仍引用原来的 R4 网格和材质。只重导入 3 张 PBR 纹理和 1 张共享灰阶改造图标，不重建 UE 网格或材质表达式图。

`author_finish.py` 为当前 Blender 制作入口：读取本目录保留的 R4 模型源、运行同源表面转移并保存作者文件。随后运行上级 `render_icon.py`、本目录 `import_assets.py`、`register.py`。后台导入使用 `run_import.ps1`；编辑器运行时使用已有互斥桥。

`texture_recipe.json` 记录真实样片位置、物理尺度与参数，`source_receipt.json`、`import_receipt.json`、`delivery.json` 分别记录制作、保存和发布结果。`Before/` 保留本次修改前的源与正式资源。未运行游戏测试或追加验收渲染。
