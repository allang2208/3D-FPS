# 火球迁移：资产筛选（2026-09-14）

本轮按用户要求先查看原技能、现有工程资产及资产库并提出匹配建议。未修改技能代码、原有特效或游戏引用，未下载新包，未启动 UE 预览或实机测试。

## 原项目表现依据

源项目：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。

- `data/skills.json:skills.fireball`：第一次释放凝聚，第二次释放发射；命中后范围爆炸。
- `src/entities/components/fireball-system.js`：悬浮单颗火球、飞行短拖尾；命中目标、墙面或到最大射程时爆炸一次。爆炸由橙红冲击波、亮色火焰粒子和灰烟组成。
- `src/phaser/scenes/GameScene.js:_ensureFireballEmitters`：当前 Phaser 表现采用白/黄/橙/红主火焰团，加外层橙红光晕；与飞行阶段共享发射器。
- 已查看 `assets/skills/fireball_spritesheet.png`：73 帧旧球体参考。它仍被配置引用，但不能用它取代对当前 Phaser 粒子表现的理解。
- 原配置的悬浮上限 30 秒、冷却 20 秒、消耗 50 MP；飞行速度、射程、爆炸半径仍为原 2D 单位，后续迁移时需转换，不直接认定为 UE 厘米。

## 查看范围

1. 当前工程 `D:/FPS3D/FPSGAME/Content` 的实际资产文件。
2. `C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/FabLibrary/listings_v1.db`，只读查询：29 条本地条目。
3. `D:/FPS3D/VaultCache/FabLibrary/listings_v1.db`，只读查询：32 条本地条目；两库按 listing UID 去重共 40 条。空标题条目通过另一库标题或 download_meta 目录识别。
4. 三套候选的 Fab 官方商品说明。上述候选均有本地 acquisition 记录、下载缓存记录及当前工程文件。
5. Fab 网页库打开/读取超时，未确认账号完整云端资产清单；本地结果不能代表所有未下载或未缓存的云端资产。

## 候选比较

| 候选 | 当前状态 | 对火球的适合程度 | 建议用途 |
| --- | --- | --- | --- |
| Epic Niagara Examples Pack | 本地库已有，当前工程 `Content/NiagaraExamples` 已有 | 首选；包含火球循环材质、火焰/烟、拖尾及爆炸组件 | 组合完整火球的主要素材来源 |
| Realistic Starter VFX Pack Vol 2 | 本地库已有，当前工程 `Content/Realistic_Starter_VFX_Pack_Vol2` 已有 | 次选；所读火焰/爆炸资产为 Cascade `ParticleSystem` | 烟火贴图、爆炸和热扰动的备用来源 |
| RPG - Crafting & Environment VFX | 本地库已有，当前工程 `Content/RPGEnvironmentVFX` 已有 | 辅助；主题偏炼金、锻造、法阵、传送和环境魔法 | 可选的施法光晕/法阵素材，不作为火球主体 |

官方说明：

- [Niagara Examples Pack](https://www.fab.com/listings/0e188eca-4e54-4fb2-a9ed-d8b8a565e600)：包含爆炸、拖尾、火焰、烟雾等系统。
- [Realistic Starter VFX Pack Vol 2](https://www.fab.com/listings/ac2818b3-7d35-4cf5-a1af-cbf8ff5c61c1)：包含 Explosion、Fire、Molotov、Flamethrower、Smoke 等类别。
- [RPG - Crafting & Environment VFX](https://www.fab.com/listings/a5077033-9401-4b9b-9b31-031d81140604)：主题为 RPG 制作与环境特效，并提供尺寸、粒子密度等参数。

## 推荐的具体组合

以下均为现存资产路径；用途和改造方式是本轮建议，尚未制作或接入。

| 火球阶段 | 来源 | 需要的改造 |
| --- | --- | --- |
| 凝聚/悬浮主体 | `/Game/NiagaraExamples/Materials/MI_FireBall_8x8`，关联 `T_FireBall_EOO_Loop` 和 `T_FireBall_Normals_Loop` | 创建独立火球发射器，形成紧凑滚动火核、外焰和光晕；凝聚后持续循环 |
| 外焰/余烬 | `/Game/NiagaraExamples/FX_Misc/NS_Fire` | 提取或改造火焰和余烬层，调整生成形状；原系统是环境火焰，不能直接挂上就视作球体 |
| 飞行焰尾 | `/Game/NiagaraExamples/FX_Weapons/Trails/NS_RocketTrail` | 保留沿运动轨迹生成的组织方式，减少导弹烟尾，改成橙红短焰尾；原 `MI_RocketTrail_8x8` 实际引用烟雾 flipbook，需要相应换材质/调色 |
| 命中/撞墙/到射程爆炸 | `/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small`，较大等级可参考 `NS_Explosion_Medium` | 保留爆焰、火星、短灰烟；按火球范围调整，减少默认碎石和过重烟幕；原系统还引用地面尘土、贴花、后处理和相机震动，需逐项选择 |
| 原技能冲击波 | 新建薄层橙红扩散环，参考原 `fireGroundShockwave` | 与爆炸同步，贴地/贴墙方向适配，不在空中爆炸时强贴地 |

`MI_FireBall_8x8` 是现成材质与循环纹理，不是可以直接施放的完整火球 Niagara System。本轮在包内文件引用搜索中未发现其他资产直接引用该材质；不能据其名称宣称火球已接入。

Realistic 备用路径：`Particles/Fire/P_Fire_Small`、`Particles/Fire/P_Fire_Big`、`Particles/Explosion/P_Explosion_Big_A`、`Particles/Explosion/P_Molotov`。其中已读取的 `P_Fire_Small` 和 `P_Explosion_Big_A` 包含 `ParticleSystem` 类型名，不能称作 Niagara 原生系统。

RPG 辅助路径：`VFX/Niagara/NS_MagicalGlowRays`、`NS_MagicalSeal`、`NS_ForgeSparks`、`NS_CauldronBlacksmith`。法阵不属于原火球的必需表现，默认迁移可先不加入。

## 本轮结论与边界

现有 Niagara Examples 足以作为制作火球的主要基础，目前没有必要为此另购整套特效。匹配依据为原技能配置/渲染代码、现存资产及包内类型/名称引用和官方说明；尚未在 UE 中播放比较画面，也未测性能。本轮仅交付素材选择，火球技能逻辑、三阶段专用 Niagara、第一人称显示、碰撞伤害及 UI/成长/存档仍待后续迁移。
