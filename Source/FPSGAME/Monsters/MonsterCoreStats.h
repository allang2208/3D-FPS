#pragma once
#include "CoreMinimal.h"
#include "../Combat/CoreCombatFormula.h"
#include "MonsterCoreStats.generated.h"
class AActor;

// 品阶（原 data/enemy-config.json rank 口径）。
UENUM(BlueprintType)
enum class EMonsterRank : uint8 { Normal, Minor, Elite, Lord, Boss };

// 韧性类别（2026-09-29 用户拍板"按类别×阶级定韧性基准"）：决定阈值基线、
// 三抗性与脱战恢复；阶级只缩放阈值与破韧时长。类别按怪物韧性身份归类，
// 不严格等于继承家族（小手按轻装杂鱼处理）。
enum class EMonsterToughnessClass : uint8
{
    Light,      // 轻装：护士/毒液僵尸/小手——脆，频繁破韧
    Heavy,      // 重装：胖子/突变体-3——高阈值，钝抗明显
    Caster,     // 施法：巫婆/毒蛆——中阈值，冲击抗性
    Canine,     // 犬科：野狼/僵尸犬/感染犬——低阈值，破韧频繁
    Colossal    // 巨物：大手/手脑——最高阈值，破韧后控制短
};

// 怪物档案核心：防御常量 + 配置等级 + 品阶。2026-09-28 用户拍板剔除怪物端六维
// （六维是静态中间量：怪不升级不穿装，公式输出终生不变，且攻击/生命本就走字面量覆盖）。
// Def/Mdef/CritRes 为原六维公式的**逐位烤入值**（def=⌊1.5体+.3力⌋、mdef=⌊1.2精+.3智⌋、
// critRes=⌊体⌋），并已并入运行时字段覆盖（手脑 mdef65/大手 mdef30/小手 mdef55/巫婆 mdef55）；
// AttrWeight 为战斗等级的属性权重和（.08力+.08敏+.10体+.08智+.08精+.04运）。
// 怪物暴击率（2+运）无任何消费方，未保留。渐进感染减益在 Get() 内对数值整体乘系数。
struct FMonsterCoreStats
{
    int32 Def = 0;
    int32 Mdef = 0;
    int32 CritRes = 0;
    double AttrWeight = 0.;
    int32 Level = 1;
    EMonsterRank Rank = EMonsterRank::Normal;
    EMonsterToughnessClass ToughnessClass = EMonsterToughnessClass::Light;
};

namespace MonsterCoreStats
{
    // 按类/标签识别（FatZombie、Mutant3、Witch 为标签+子类双重口径，保持旧 BP 兼容）。
    FPSGAME_API bool Get(const AActor* Target, FMonsterCoreStats& Out);

    // 原版 deriveEnemyCombatLevel（src/config/enemy-base-stats.js）：六维为主体，
    // HP 与移速提供封顶的非线性补充；图鉴/威胁显示用，配置等级仍驱动奖励。
    FPSGAME_API int32 CombatLevel(const FMonsterCoreStats& S, double MaxHp, double SpeedPx);

    // 原版压级/越级经验倍率（exp-system.js getExpLevelMultiplier）：UE 无地牢锚点，
    // 有效等级=配置等级（等价 F 档 anchor 3 + (L-3)）。未注册目标恒为 1。
    FPSGAME_API double LevelDifferenceMultiplier(const AActor* Victim, int32 PlayerLevel);

    // max(1, floor(Base×倍率))；未注册返回原值。
    FPSGAME_API int64 ScaleKillExperience(const AActor* Victim, int32 PlayerLevel, int64 BaseReward);

    // 原版 goldDrop：((L×4 + rand[1,10])×0.5)×rankMul{elite2,lord3}×祭品系数，两次 floor。
    FPSGAME_API int64 RollKillGold(const AActor* Victim, double GoldTribute = 1.);

    // 品阶倍率（原版 expValue.rankMul / goldDrop.rankMultipliers / combatLevel.rankBonus）。
    FPSGAME_API double RankExperienceMultiplier(EMonsterRank Rank);
    FPSGAME_API double RankGoldMultiplier(EMonsterRank Rank);
    FPSGAME_API double RankCombatBonus(EMonsterRank Rank);

    // 全局生命成长层（原 monsterGrowth 的同一层语义）：各怪 BeginPlay 把 MaxHealth
    // 乘上此系数后再初始化。2026-09-23 用户拍板全员翻倍=2.0；BP 实例覆盖值同样生效。
    FPSGAME_API double HealthMultiplier();

    // 韧性基准（2026-09-29）：按类别基线 × 阶级缩放，写入目标的 UMonsterCombatComponent
    // （阈值/破韧时长/三抗性/脱战恢复五项）。由组件 BeginPlay 统一调用，晚于地牢导演
    // 写入实例 Rank，因此阶级缩放对地牢精英/领主实例同样生效。未注册目标不改（保留组件默认）。
    FPSGAME_API void ApplyToughnessProfile(AActor* Monster);
    FPSGAME_API float ToughnessRankThresholdScale(EMonsterRank Rank);
    FPSGAME_API float ToughnessRankBreakScale(EMonsterRank Rank);
}
