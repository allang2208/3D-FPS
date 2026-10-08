# 缚群衣物重新制作 V19

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户否定当前衣物，要求删除后重建，并直接复用技能中巫婆布料经验。V18 不再作为合格服装模板。本轮为制作、必要构建及资产接入，不自动启动游戏、渲染或测试。

## 复用依据

- `skills/ue5-monster-workflow/references/robed-humanoid-recovery.md`：显示衣物、模拟代理、人体碰撞分开；保留身体与动作基础；衣物不得重复加厚。
- `Tools/WitchRebuilt/author_drape04.py`：连续披挂衣片使用同一承重支撑，不能像裤腿一样分别绑定多条肢体。
- `Tools/WitchRebuilt/author_surface06.py`、`author_seams07.py`：连续规则代理、单层表面、短袖管与毫米级翻边。保留 UV 接缝而不制造真实几何断缝。
- `UWitchRebuiltClothingAsset`：直接复用既有位置、法线、切线稳定绑定及每次重建入口，不新增布料求解器或逐帧修形系统。
- 巫婆 Drape06 的 4 次目标迭代 / 6 次上限 / 1 子步配置。该角色历史性能数据不算缚群 V19 的实测。

## 全新衣物

从已保存 V18 母版保留 `BC_Flesh`、完整骨架、原身体蒙皮、UV 和 M 铭牌。新场景中删除两片旧披衣、两件旧袖口、四个旧代理和旧背带，再创建新裁片。

1. 连续偏肩披衣从左肩延伸到后背，前侧和右侧触手肩部敞开。侧边在腿根以上收短，后摆从后腿之间下垂，不通过删掉零散三角面挖洞。
2. 披衣共用 body / body_rear 支撑，肩带范围固定，再向下渐放松，最大活动范围 12 cm。衣摆不混入脚或攻击触手权重。
3. 两件短袖口位于各自下肢中段，按实际同侧肢体表面转移蒙皮，限定各自 upper/lower 链。避开膝肘与掌脚关节，只有末端允许最多 1.8 cm 的布料运动。
4. 背带重做为固定肩部缝合带，M 铭牌共用这一支撑。旧的悬跨开口背带被移除。
5. 显示面由同一模拟表面细分，免费边缘做薄翻折；没有对整片布做 Solidify，没有重复内外壳。保留原绿色织物、左右袖口、皮带、金属的 UE 材质资产引用与 G 磨损 / B 污渍通道。

作者代理共 1,853 点：披衣 1,125，两件袖口各 364；显示衣物共 10,907 顶点，另有固定背带和铭牌。点数为制作输出，不代表游戏性能测量。

## 接入方式

- 制作：`Tools/BoundCongregate/author_garment_rebuild_v19.py`。
- 源及导出：`SourceAssets/BoundCongregateMeshy20261006/GarmentRebuildV19/`。
- 导入：`import_garment_rebuild_v19.py` 复用现有 `import_garment_drape_v18.py` 的参数化入口。旧 V18 默认调用保持兼容，不复制另一套导入器。
- 原生构建：`BoundCongregateAuthoring.cpp` 仅增加 V19 配置分支，现有巫婆稳定捕获、有限碰撞胶囊、距离暂停和非 CCD 路线继续使用。衣内碰撞按该衣片附近的身体样本生成，不带入远处同骨肉块。
- 新拓扑使用现有 `MonsterSoftCorpse/author_cages.py` 重新生成完整软体死亡嵌入，最后更换正式蓝图的 VisualMesh；不沿用旧衣物的顶点绑定。
- 正式目标：`/Game/Monsters/BoundCongregate/GarmentRebuildV19/SK_BoundCongregate_GarmentRebuildV19`。
- 原蓝图的移动 120、加速度 300、制动 480、转向 50 度/秒、触手 CD 20 秒及三种攻击保持当前设置。仅切换 VisualMesh。

## 状态

新模型、FBX 和 Editor 原生构建已完成。制作期间用户打开的编辑器可用，通过现有互斥桥执行 prepare / finish 两个短批次，三件新布料、独立骨架、匹配死亡网格与数据及正式蓝图 VisualMesh 已全部保存。`delivery.json` 记录 `saved: true`。

连续死亡制作复用现有算法，输出 680 个节点、2,226 个四面体；外部制作在两个编辑器批次之间进行。Editor 与 Game 的 Development 构建均已成功，构建产物已落盘。

证据位于本版目录的 `authoring.json`、`delivery.json`、`import-editor-prepare-01.log`、`import-editor-finish-01.log`、`soft-corpse-author.log` 和构建日志。旧衣物不再由正式蓝图显示；V18 母版作为未修改的身体/骨架输入保留，不继续修补或叠加到新衣物上。

未自行打开或关闭 UE，未启动 PIE、截图、渲染、布料探针或其他测试。制作与保存完成不代表动态效果已获用户认可，最终外观由用户体验。
