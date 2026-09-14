# 胖子僵尸死亡脓液

当前阶段：开发、材质制作及 UE 接入。未启动游戏或制作验收截图，实际外观与玩法由用户测试。

最新时序见 [完整死亡动画与即时脓液](fat-zombie-death-timing-and-pus-20260914.md)：生命归零立即生成脓液，原死亡动画完整播放约 2.5667 秒后才转布娃娃。

最新扩散见 [脓液逐渐扩散](fat-zombie-pus-spread-20260914.md)：生命归零后先出现小片液体，默认 1.6 秒逐渐铺开，外围液滴错开出现，伤害区域随可见范围扩展。

最新回收设置（用户于 2026-09-14 指定）：护士僵尸、胖子僵尸、手脑怪、毒蛆的尸体默认均在死亡后 15 秒回收；胖子脓液持续 20 秒后开始 1 秒淡出，独立于尸体回收。此次仅修改数值，未进行游戏测试。

最新材质见 [脓液可见性修正](fat-zombie-pus-visibility-20260914.md)：主体改为写入场景深度的 Masked 湿润 PBR，移除透明水膜的 DepthFade，保留水体纹理、边缘覆盖和结束消退；由用户测试实际观感。

## 原项目依据

只读参考 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`：

- `data/enemy-config.json` 的 `fatZombie.attackSkills.corrosionAura`：`damage=8`、`intervalMs=500`、`corpseDuration=6000`、`deathAnimMs=1500`、`corpseWidth=200`、`corpseHeight=50`、`corpseOffsetY=0`。
- `src/entities/enemy-types/fat-zombie.js`：死亡动画结束后才开始尸体腐蚀区域；按不同阵营筛选，调用 `takeDamage(8, source, 'magic', false)`；尸体阶段不跟随活体攻击速度。
- `src/physics/skill-shapes.js` 的 `GroundEllipse`：只作用地面单位，检查同一地表高度层及实体脚下范围。
- 旧项目显示的是融化动作最后一帧加腐蚀区，并没有可直接移入 UE 的真实液体。此次写实脓液外观和随机轮廓属于 UE 新制作。

## 接入时序与数值

- 既有胖子 600 生命、25 攻击及已确认的四个动作保留。仅新增死亡后的残留物，不加入源项目的活体腐蚀光环或远程伤害减半。
- 死亡只生成一次脓液，位置锁定死亡时脚下；按用户最新要求在生命归零时立即生成，不等待死亡动画。
- 脓液独立 Actor，生成时开始计时并可见；第 0.5 秒首跳，之后每 0.5 秒一次，逻辑第 20 秒末跳，共 40 个伤害节拍。
- 每跳 8 点魔法原始伤害，走现有 `ApplyDamage`、魔法防御、玩家闪避和生命 HUD。对玩家按现有规则扣除魔防，最低 1 点；不挂毒蛆中毒层数，不因尸体消失停止已生成的残留。
- 同一潭的主体和多个液滴，每个目标每跳只结算一次；不同胖子的脓液可各自造成伤害。
- 20 秒伤害阶段结束后，1 秒内变暗、变粗糙并淡出，随后回收。离开接触范围或跳起后不继续叠加离地持续伤害。

## 阵营、地面与生命周期

- 有有效 GenericTeamId 的目标使用现有团队敌对关系。否则，玩家／Friendly／Player 标签视为玩家阵营，Enemy 或怪物战斗组件视为怪物阵营；无阵营的中立物件不作为伤害目标。
- 怪物阵营的胖子脓液伤害玩家及玩家友军，不伤害同阵营怪物。Friendly 胖子的残留则反向伤害敌人。
- 判定使用实际生成的地面三角形、脚下高度和接触半径；透明外缘不算有效腐蚀区。角色必须落地，不隔层伤害、不以角色躯干进入球形粗筛作为最终命中。
- 液体沿地形采样，拒绝陡面、阶梯立面、大落差及越墙投射；无合适地面或缺材质时不生成隐形伤害区。
- 液体不阻挡玩家、武器或导航。定时器随 Actor 销毁清理；F6 清除开发怪物时，同时清除该面板生成怪物的脓液并取消未触发的死亡生成。

## 随机外形

- 三维主体基础半径 145 × 90 cm，面积按 UE 胖子体型设计；旧 200 × 50 是二维投影尺寸，没有把屏幕像素直接当厘米。
- 每次死亡随机种子、平面方向、长短轴约 ±10%、3/5/9 阶连续轮廓变化；主体之外散落 7–12 个约 3–11 cm 半径的细滴，随机距离与拉长比例。
- 同一次生成的种子保持不变，画面不会每帧重新随机。可在 `FatZombie|Pus` 设置非零 `ShapeSeed` 固定形状，也可修改伤害、间隔、持续时间、范围及液滴数。
- 地面网格同时作为视觉与伤害区域的数据源；地形裁掉的部分不保留隐藏伤害。表面最大厚度约 1.45 cm，外缘约 3.5 mm。

## 材质与资源来源

读取结果见 `Saved/FatZombiePus/material_sources.json`。

- `JVAD3D_SimpleWaterPuddles/Materials/M_JVAD3D_SimpleWaterPuddles` 可改 Color、Roughness、Spec、opacity，但它是固定 Alpha 的静态贴花。
- `WorldGeneration/TemperateHills/Rivers/M_TemperateRiverWater` 为现有半透明水面，有 FlowSpeed、Specular、WaterTint；其法线和泡沫适合复用。
- `RuralAustralia/Water/M_Water_01` 有浑水颜色与纹理，读取后选用现有 `T_Water_01_M` 的色块变化。

独立衍生资产：

- `/Game/Monsters/FatZombieMeshy/Pus/M_FatZombie_Pus`
- `/Game/Monsters/FatZombieMeshy/Pus/MI_FatZombie_Pus`

材质由现有河流水体母材质复制后，按相同基础图重建成液膜：复用 `/Game/WaterMaterials/Textures/T_River_Waves01_Normals`、`T_River_Waves02_Normals`、`T_Ocean_Foam`，以及 RuralAustralia 的浑水遮罩。流速从 0.14 降到 0.007，弱化水波，改成黄绿／深橄榄色浑浊层、少量浅色浮沫、低粗糙度湿亮表面及薄边透明过渡；没有绿色自发光或大浪。

现有水体资产及世界河流不被改色。素材均来自用户工程中已有资源，无新增下载或再分发授权判断；新增的材质图、代码和重建脚本为本次工程制作。

重建脚本：`Tools/FatZombie/inspect_pus_material_sources.py`、`Tools/FatZombie/build_pus_material.py`。使用原有 FatZombieAuthoring 素材宿主进行必要材质制作，依赖纹理按原包路径复制；最终只回写本次两个脓液材质资产。

## 构建记录

- 原有 FatZombieAuthoring 宿主的材质制作完成，退出码 0：`Saved/Logs/FatZombie-pus-material-build.log`，记录 `Saved/FatZombiePus/material_authoring.json`；两个材质包已并入主工程。
- Editor 构建成功，退出码 0：`Saved/Logs/FatZombie-pus-Editor-build.log`。采用模块后缀 61457，加载新代码需要重新打开编辑器。
- Game 构建过程中遇到同期 715 配件改动：首次缺少 `AttachmentPath` 接口，随后该接口已由现有改动补齐；重试发现 `DanWesson715AttachmentVisual.cpp` 局部变量 `Mesh` 遮蔽 `ACharacter::Mesh`，本次仅将这三个局部引用更名为 `OpticMesh` 以解除编译阻塞，保留配件行为。失败记录分别为 `Saved/Logs/FatZombie-pus-Game-build.log` 和 `Saved/Logs/FatZombie-pus-Game-build-retry.log`。
- Game 最终构建成功，退出码 0：`Saved/Logs/FatZombie-pus-Game-build-final.log`；已生成 `Binaries/Win64/FPSGAME.exe`。
- 不将编译／材质保存等同于写实外观或游戏实测通过。本轮未启动游戏、截图或执行运行测试，交由用户测试。
