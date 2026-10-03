# 虎首正侧面造型 V5

本目录为 2026-10-03 对照原始正侧视图制作的独立修订。V4 源文件、PBR、参考和导出继续保存在上级，不覆盖旧网格。

## 制作内容

- 在正面扩大虎口，外展虎目、吻部与颊部；嘴壁、唇缘、牙齿和眼石随同一个连续坐标场变化，保留 UV。
- 移除全底壳的八棱锥式收尖。后底壳圆收抬起，下颌与虎须前移，保留局部尖收。
- 冠顶从原来的低扁分层改成较高的连续穹顶，重排细边和红石带。
- 沿用实际柄尾切口、单一云环和 V4 接座，装配 pivot、单位、挂点、普通/长握柄位移合同保持原值。
- 沿用六组 PBR 和原来的三档 LOD 制作路线；本轮不是减面或性能优化，不从面数推断帧率。

精确参考是 `../Reference/TigerPommel_Reference.png`。面部浮雕及侧后卷云仍沿用已有高度源，其线条与原图并非逐根相同。后脑不可见处延续现有设计；底图多出的连接环不采用。

## 制作入口

1. Blender 后台运行 `author_pommel.py`：输出可编辑 `TangDao_TigerPommel_Editable.blend`、`Export` 下 FBX/GLB、`pommel_manifest.json`。
2. Blender 后台运行 `render_menu_icon.py`：输出真实模型灰阶透明图，仅用来制作游戏图标，不是验收渲染。口腔保留深灰层次，避免灰阶助手把内腔提亮成白片。
3. 内置 imagegen 将当前真实模型图放入项目既有金属框；输入与提示词写入 `Icons/framed_icon_prompt.json`。
4. `import_background.ps1`：无编辑器时使用后台 commandlet；已有编辑器则使用现有互斥桥。导入独立 V5 网格和对应图标，复用六组既有材质。
5. 资产保存成功后，导入脚本更新现有 `tiger_mountain` 的模型路径与外观说明，保留 stats/effects、其他选项和长握柄偏移，并写 `../active_revision.json`。上级 `catalog_extension.py` 据此读取新清单，主目录重建继续使用 V5。

模型资产：`/Game/Weapons/TangDao20261002/TigerPommel20261002/SilhouetteV5/Meshes/SM_TangDao_Pommel_tiger_mountain_SilhouetteV5`。

材质资产仍在上级原有 `Materials`，没有新建重复贴图或改变旋风材质映射。新网格通过既有材质身份继续使用这些映射。PNG/Texture2D 使用原图标键，修改前副本和目录记录保存在本目录 `Before`。

## 交付边界

制作回执为 `import_receipt.json`，交付状态为 `delivery.json`。没有启动交互 UE、游戏、PIE、自动测试或验收渲染；正侧面最终相似度与游戏表现由用户测试。不使用旧轮次的图或回执宣称 V5 已验收。

原参考、纹饰源、PBR、Blend、FBX/GLB、PNG 与 UE 二进制保留本机；来源许可沿用原记录，未认定可公开再分发。
