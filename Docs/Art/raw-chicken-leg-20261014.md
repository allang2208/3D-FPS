# 生鸡腿材质派生（2026-10-14）

本轮按用户授权，将本机已有的 Quixel **Roasted Chicken Leg** 制作为独立生鸡腿外观资产。五个 UE 资产已通过现有编辑器的互斥桥导入并保存；没有修改原烤鸡腿，没有添加菜谱、食物属性、商店、掉落或原料获取规则。

## 来源与制作范围

- 本机源：`D:/FPS3D/VaultCache/FabLibrary/Roasted_Chicken_Leg-acc6ad95/fbx/high/roasted_chicken_leg_wd5f_extracted`。
- [Fab 原商品](https://www.fab.com/listings/acc6ad95-9e16-4398-b13b-057e59c04488)，发布者 Quixel Megascans，资源 ID `wd5ffbnaa`。
- 保留原网格轮廓、UV 和比例，没有减面或局部重塑。Blender 实际读取为 2505 顶点、5006 三角形；UE 导入后因渲染顶点拆分为 2857 顶点，不代表增加了原模型几何细节。
- UE 尺寸约 **25.13 × 13.86 × 5.72 cm**，保存一个 26-DOP 凸碰撞体。
- 新建 2048² 程序化底色、粗糙度与微表面法线。使用淡粉肉色、乳白脂肪色，粗糙度范围 0.34–0.52，微表面高度 0.16 mm；不复用原熟肉的颜色、焦痕、法线或粗糙度贴图。
- UE 材质为不透明 PBR，Metallic=0、Specular=0.32；底色 sRGB，粗糙度非 sRGB，OpenGL 法线导入时翻转绿色通道。纹理允许流送。
- 当前保持原烤鸡腿几何，是否仍有熟肉轮廓感、颜色是否符合期望，留给用户视觉确认。本轮没有预览渲染、截图或游戏验收。

## 资产与回执

UE 目录：`/Game/Items/Consumables/ChickenLeg20261014/Raw`。

- `SM_RawChickenLeg`
- `M_RawChickenLeg`
- `T_RawChickenLeg_BaseColor`
- `T_RawChickenLeg_Roughness`
- `T_RawChickenLeg_NormalGL`

制作源位于 `SourceAssets/RawChickenLeg20261014/`：可编辑 `RawChickenLeg_Editable.blend`、FBX、三张 PNG、`prepare_raw_chicken.py` 与 `import_raw_chicken.py`。生产烘焙仅用于制作贴图，没有执行模型预览渲染。

`ue-import.json` 记录五个保存成功的资产、实际尺寸和碰撞；`import-bridge-04.txt` 为成功桥回执。早期 01/02 次调用未写出资产，03 次被本机 Python 启动器的沙箱限制挡住；04 次在同一互斥桥中完成导入。没有另开编辑器，也没有覆盖已存在的同名资产。最终文件散列及源文件保留结果见 `delivery.json`。

## 许可范围与 NoAI 处置

官方 [Fab Standard License 摘要](https://www.fab.com/eula)允许为项目修改资产并作为项目组成部分分发，禁止将资产作为独立商品再次出售或分发。[Epic Content License Agreement](https://www.unrealengine.com/eula/content)同样允许私下修改，源文件分享限于为项目工作的获准协作者。由此可支持本轮项目内的本地材质派生；没有查到该商品另行禁止材质修改的条款。

本地元数据和商品页明确标注 **NoAI**。发现标记前曾生成一份 AI 底色候选；发现后已停止使用，并将候选及含候选的备份移至 `trash/campfire-raw-chicken-ai-candidate-20261014/`，记录散列。该候选从未导入 UE；当前交付仅使用独立 Blender 程序化材质，不再调用图像生成。

本地元数据没有取得时的确切许可套餐或条款快照，公开商品页也未提供该账户的取得记录。因此本轮不能宣称公开发行许可已审清。若实际按旧 Megascans 的 Unreal Engine 套餐取得，则限 UE 使用；教育套餐限教育非商业用途；免费评估套餐仅限内部评估。应以取得当时的授权记录为准。上述限制不应被笼统替换成“只有 NoAI”。原始源包及可提取派生资产不作为独立资源公开分发；本轮没有提交、推送、下载新包或接受新许可。

## 后续接入边界

这次完成的是可供 UE 使用的生鸡腿外观资产。`Content/ColdSteelData/campfire-recipes.json` 仍为 0 条菜谱；生鸡腿尚未注册为库存物品，没有图标或来源，不应称为已可在游戏中获取或烹饪。首批菜品、食材来源和对应数值继续由用户决定。

用户可在内容浏览器打开上述网格，确认尺寸、轮廓、材质和碰撞；在决定物品与菜谱后，再接入库存和烧烤流程。本轮未替用户执行这些测试。
