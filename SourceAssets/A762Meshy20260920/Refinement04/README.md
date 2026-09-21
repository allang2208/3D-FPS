# A762 后托衔接重建 04

依据用户后托近照，修正两根规则托杆与残留生成尾板之间的接头、碎边及外缘。旧尾板来源保留在新可编辑源的隐藏集合 `A762_BEFORE_STOCK_JOINT_04`。

## 本轮制作

- 读取现有双杆的实际中心、半径和尾板端部轮廓，保留枪托长度、上下杆位置及两杆之间的镂空。
- 两根托杆分别制作连续的渐扩肩部；其末端接入闭合的支撑骨架和弯曲背板。替换尾板侧原先残缺的生成接口，不在断口外侧简单叠一个套圈。
- 重建原有上宽下窄的尾板轮廓和下部三角支撑，加入侧面固定件，并处理接头与支撑面的过渡。
- 橡胶托垫采用完整曲面，防滑横纹直接形成在有底面的表面上。金属背板、窄接缝和橡胶分开赋材质；新增形体使用自己的 UV 与几何法线，避免旧图集边缘被拉到连接处。
- 新零件的材质槽均保留 `FactoryStock` 身份；导入时采用当前 FBX 的材质分区并显式绑定材质路径，避免新几何继承旧分区编号。

机匣侧接口、其他枪体几何、前后瞄具、弹匣、骨架、11 段原动作和 AKM 音效沿用现状；没有修改 C++。

## 文件与运行入口

- `A762_StockJoint_Editable.blend`：完整可编辑源与旧版几何。
- `Exports/SK_A762_Manny.fbx`：本轮重新导出的枪体。
- `Exports/SM_A762_FrontSight.fbx`、`Exports/SM_A762_RearSight.fbx`：未改动的前后瞄具，随完整源保留，本轮不导入。
- `rebuild_stock.py`：后托作者入口；复用相邻 `Refinement02/rebuild.py` 的基础几何函数。
- `import_stock.py`：通过项目互斥桥备份、导入、绑定材质和保存。
- `authoring.json`、`import.json`、`DELIVERY.json`：制作参数、实际保存回执和交付状态。

运行网格继续使用 `/Game/Weapons/A762/Integrated20260920/SK_A762_Manny`。本轮材质与替换前备份分别在 `/Game/Weapons/A762/Refinement04/Materials` 和 `/Game/Weapons/A762/Refinement04/Before`。

未启动游戏、运行测试、截图或验收渲染，最终外观由用户测试。

项目桥已完成原运行网格备份、新材质保存及枪体重导入，完成回执为 `ue_import_01.txt` 中的 `A762_STOCKJOINT04_IMPORTED_AND_SAVED`。
