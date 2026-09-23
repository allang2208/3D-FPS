#pragma once
#include "CoreMinimal.h"
#include "../Combat/CoreCombatFormula.h"
#include "MonsterCoreStats.generated.h"
class AActor;

// 品阶（原 data/enemy-config.json rank 口径）。
UENUM(BlueprintType)
enum class EMonsterRank : uint8 { Normal, Minor, Elite, Lord, Boss };

// 怪物六维核心：六维 + 配置等级 + 品阶。六维来自原项目
// E:/无尽轮回/长期备份/2026-7-13-1/game-dev data/enemy-config.json；
// 狼、护士为 UE 新增身份，六维按其现行表面值（物防/魔防/抗暴）反解，
// 保证接入前后伤害与暴击行为逐位不变。表面字段（MaxHealth/AttackDamage/
// BiteDamage/狼防具等）保持原版 maxHp/atk/matk/mdef 直接配置的覆盖语义。
struct FMonsterCoreStats
{
    CoreCombatFormula::Attributes A;
    int32 Level = 1;
    EMonsterRank Rank = EMonsterRank::Normal;
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
}
