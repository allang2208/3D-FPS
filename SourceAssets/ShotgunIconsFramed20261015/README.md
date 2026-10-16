# 散弹枪三款配件图标重制

用户否决此前收束器、鸟笼消焰器和散弹枪消音器的简化 Blender 金属框图标，要求按枪械工作流参考其他已实装改造件重新生成。

本轮读取 `ue5-weapon-workflow/references/attachment-icons.md`，对照正式的战术消音器图标与认可母版 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png`。旧图的框体、铆钉、底板及表面层次偏离该母版。

采用内置 imagegen，一项一图。第一输入为正式框体母版，第二输入为当前实际配件网格的独立渲染；固定单件、水平枪口朝左、上向不变、外缘透明、框内深色底板、中性银灰金属。保留收束器的分段缝、鸟笼的真实长槽和消音器的三条纵向侧筋。图像原始输出直接复制，没有额外图像处理。

| 配件 | 最终母图 |
| --- | --- |
| 收束器 | `Final/muzzle_shotgun_choke.png` |
| 鸟笼消焰器 | `Final/muzzle_shotgun_birdcage_flash_hider.png` |
| 散弹枪消音器 | `Final/muzzle_shotgun_suppressor.png` |

三张均为 1254 × 1254 RGBA PNG，与母版尺寸一致。图像已在生成结果中查看；不将制作结果称为用户已验收。

`generation_prompts.json` 保存完整逐图提示词及输入映射；`References` 保存实际模型单件图和可编辑参考场景；`references.json` 保存源模型与相机约定。

部署入口为 `deploy_icons.py`，实际 PNG 根目录为 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms`。同步原三款模型作者目录下的正式图，三个 `author_icon.py` 改为恢复本轮最终母图，避免重新生成已退役的简化框。旧图、旧作者脚本及被替换的纹理包按准确路径备份至 `trash/shotgun-icons-rejected-20261015`，见归档清单。旧图标 Blender 场景只保留为制作历史，不作为当前正式图源。

`import_icons.py` 同步六个 UE Texture2D：共享 FramedFirearms 三个包，以及三款 CommonShotgun/UI 副本；沿用 UI 组、Editor Icon 压缩、sRGB 与 Never Stream。实际保存结果见 `import_receipt.json`，PNG 部署及备份见 `deployment_receipt.json`。

本轮只更换二维图标，不修改模型、材质、挂点、属性、存档或 C++ 加载代码，不需要原生重编译。没有启动游戏或进行运行时测试。
