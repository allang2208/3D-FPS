# 修女鞋靴 R8 制作与接入

本轮面向近距离观察的修女 NPC 鞋靴，交付可编辑模型、细节高模、分区 PBR、原生绑定及远景 LOD。默认不运行游戏、截图或性能测试，最终表现由用户体验确认。

## 制作内容

- 从当前运行引用的 `RefinementR4/Meshes/SK_Nun_Boots` 捕获真实网格、原生骨架、权重、UV 和材质槽，保留黑色袜层与裙摆覆盖合同。
- 沿前掌弯折区加入三道浅压褶，最大位移约 0.077 cm；外层、内衬、线体共用连续变形，保持鞋底接地面与原生权重。
- 皮革、加固裁片、橡胶底、叠层沿条、蜡线、铁扣和内衬分别处理。鞋面维持深棕皮革身份，降低大块斑驳，增加细颗粒和受弯区域的材质变化。
- 新烘焙使用项目已有 xjghdgl 皮革扫描源。颜色不用于推导高度；法线来自 Bump/Displacement 的物理厘米表面场。可编辑高模用相同高度场位移，明确排除在游戏导出之外。
- 本体坐标的局部遮罩驱动鞋头抛光、后跟摩擦、弯折与下沿薄尘，跟随蒙皮而不产生世界空间滑动。铁扣和蜡线保留独立反射及微纹。
- 鞋面颜色/法线 4096，ORM 2048；沿条 2048；橡胶 1024。ORM 为 R 遮蔽、G 粗糙度、B 金属度。OpenGL 法线导入 UE 翻转绿色一次，保留 mip 和流送。
- 游戏 LOD0 220748 三角形，未增加密度；LOD 策略 100% / 45% / 18%，屏幕阈值 1 / 0.18 / 0.075。高模细分与位移仅用于制作。

## 路径与流程

制作源：`SourceAssets/ChapelNun20261115/BootFinishR8/`，包含 Inputs、Authored、Textures、`NunBoots_R8.blend` 和分阶段保存回执。

1. `capture_boot_finish_r8.py` 冻结活动资产。
2. Blender 后台执行 `author_boot_finish_r8.py`；普通 Python 执行 `bake_boot_finish_r8.py`。
3. Blender 后台执行 `finish_boot_author_r8.py`，打包材质图和物理高度场。
4. 退出 PIE 后，通过现有批次互斥分别执行 `save_boot_finish_r8_materials.py`、`save_boot_finish_r8_geometry.py`。

新材质和纹理位于 `/Game/Characters/ChapelNun20261115/BootFinishR8`。游戏继续使用原 `SK_Nun_Boots` 路径，避免额外运行时组件或加载逻辑；只修改修女资产，不改共用玩家靴。`save_final_boots.py` 在 R8 保存完成后自动沿用该制作源。

`saved_assets.json.completed` 为实际资产保存完成标志。模型和贴图已经制作不代表已导入；若 PIE 占用，则保持此前游戏资产，等待退出试玩后保存。本轮未新增 C++，无需全工程重编译。没有运行或截图验收。
