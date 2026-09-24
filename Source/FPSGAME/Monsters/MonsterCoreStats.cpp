#include "MonsterCoreStats.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotMonster.h"
#include "WolfMonster.h"
#include "InfectedDogMonster.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "FatZombie.h"
#include "Mutant3.h"
#include "WitchMonster.h"
#include "NurseZombie.h"

namespace MonsterCoreStats
{
double RankExperienceMultiplier(EMonsterRank R)
{ switch(R){case EMonsterRank::Elite:return 2.;case EMonsterRank::Lord:return 4.;case EMonsterRank::Boss:return 20.;default:return 1.;} }
double RankGoldMultiplier(EMonsterRank R)
{ switch(R){case EMonsterRank::Elite:return 2.;case EMonsterRank::Lord:case EMonsterRank::Boss:return 3.;default:return 1.;} }
double RankCombatBonus(EMonsterRank R)
{ switch(R){case EMonsterRank::Minor:return 1.;case EMonsterRank::Elite:return 3.;case EMonsterRank::Lord:return 5.;case EMonsterRank::Boss:return 7.;default:return 0.;} }
double HealthMultiplier()
{
    // 2026-09-23 用户拍板：全部怪物生命值翻倍。调参只改这一个数（对应原版
    // monsterGrowth 的全局成长层语义；六维/防具/奖励不受影响）。
    return 2.;
}

// 六维与 rank/level 逐字对照原 data/enemy-config.json（手脑12lord/胖子4/突变体3为9elite/
// 巫婆8lord/毒蛆4elite）；狼、护士为 UE 新增身份：参照 blackWolf/zombie 量级，用现行
// 表面值反解（狼 def12=⌊1.5×5+0.3×16⌋、mdef8=⌊1.2×6+0.3×3⌋、critres5=⌊5⌋、bite22=
// round(0.5×16+0.5×28)；护士防具全 0、atk15=round(0.5×3+0.5×27)），接入前后行为逐位不变。
bool Get(const AActor* Target,FMonsterCoreStats& Out)
{
    if(!Target)return false;
    CoreCombatFormula::Attributes A;int32 Level=1;EMonsterRank Rank=EMonsterRank::Normal;bool bKnown=false;
    if(const auto* H=Cast<AHandBrainMonster>(Target)){A={50,25,30,40,20,10};Level=H->Level>0?H->Level:12;Rank=H->Rank;bKnown=true;}
    else if(const auto* M=Cast<APoisonMaggotMonster>(Target)){A={7,13,24,22,24,13};Level=M->Level>0?M->Level:4;Rank=M->Rank;bKnown=true;}
    else if(const auto* D=Cast<AInfectedDogMonster>(Target)){A=D->BaseAttributes();Level=D->Level;Rank=D->Rank;bKnown=true;}
    else if(const auto* W=Cast<AWolfMonster>(Target)){A={16,28,3,5,6,8};Level=W->Level>0?W->Level:5;Rank=W->Rank;bKnown=true;}
    else if(const auto* F=Cast<AFatZombie>(Target)){A={18,6,3,20,3,5};Level=F->Level>0?F->Level:4;Rank=F->Rank;bKnown=true;}
    else if(const auto* U=Cast<AMutant3>(Target)){A={50,30,5,40,10,6};Level=U->Level>0?U->Level:9;Rank=U->Rank;bKnown=true;}
    else if(const auto* C=Cast<AWitchMonster>(Target)){A={20,15,30,33,25,13};Level=C->Level>0?C->Level:8;Rank=C->Rank;bKnown=true;}
    else if(const auto* N=Cast<ANurseZombie>(Target)){A={3,27,3,0,0,3};Level=N->Level>0?N->Level:3;Rank=N->Rank;bKnown=true;}
    else if(Target->ActorHasTag(TEXT("FatZombie"))){A={18,6,3,20,3,5};Level=4;Rank=EMonsterRank::Normal;bKnown=true;}
    else if(Target->ActorHasTag(TEXT("Mutant3"))){A={50,30,5,40,10,6};Level=9;Rank=EMonsterRank::Elite;bKnown=true;}
    else if(Target->ActorHasTag(TEXT("Witch"))){A={20,15,30,33,25,13};Level=8;Rank=EMonsterRank::Lord;bKnown=true;}
    if(!bKnown)return false;
    const double Infection=UProgressiveInfectionComponent::AttributeMultiplier(Target);
    A.Str*=Infection; A.Dex*=Infection; A.Int*=Infection;
    A.Con*=Infection; A.Wis*=Infection; A.Luck*=Infection;
    Out={A,Level,Rank};
    return true;
}

int32 CombatLevel(const FMonsterCoreStats& S,double MaxHp,double SpeedPx)
{
    // 原版 deriveEnemyCombatLevel（enemy-base-stats.js）：六维为主体，HP 与移速提供
    // 封顶的非线性补充（HP≤+8、移速≤+4），rank 加成后四舍五入，下限 1。
    double Raw=1.+S.A.Str*.08+S.A.Dex*.08+S.A.Con*.10+S.A.Int*.08+S.A.Wis*.08+S.A.Luck*.04;
    Raw+=FMath::Clamp(std::sqrt(FMath::Max(0.,MaxHp)/100.)*1.5,0.,8.);
    Raw+=FMath::Clamp((FMath::Max(0.,SpeedPx)-80.)/40.,0.,4.);
    return FMath::Max(1,(int32)CoreCombatFormula::Round(Raw+RankCombatBonus(S.Rank)));
}

double LevelDifferenceMultiplier(const AActor* Victim,int32 PlayerLevel)
{
    FMonsterCoreStats S;if(!Get(Victim,S))return 1.;
    // 原版 exp-system.js getExpLevelMultiplier：压级 diff>5 每级 -15%（rank 下限
    // normal.01/elite.03/lord.05/boss.10）；越级 diff<-5 每级 +10%，封顶 1.5。
    // UE 无地牢 grade 锚点，有效等级=配置等级（等价 F 档 anchor 3 + (L-3)）。
    const int32 Diff=PlayerLevel-S.Level;
    if(Diff>5)
    {
        double Floor=.01;
        if(S.Rank==EMonsterRank::Elite)Floor=.03;else if(S.Rank==EMonsterRank::Lord)Floor=.05;else if(S.Rank==EMonsterRank::Boss)Floor=.1;
        return FMath::Max(Floor,1.-.15*(Diff-5));
    }
    if(Diff<-5)return FMath::Min(1.5,1.+.1*(-Diff-5));
    return 1.;
}

int64 ScaleKillExperience(const AActor* Victim,int32 PlayerLevel,int64 BaseReward)
{
    FMonsterCoreStats S;if(!Get(Victim,S))return BaseReward;
    return FMath::Max<int64>(1,FMath::FloorToInt64((double)BaseReward*LevelDifferenceMultiplier(Victim,PlayerLevel)));
}

int64 RollKillGold(const AActor* Victim,double GoldTribute)
{
    FMonsterCoreStats S;if(!Get(Victim,S))return 0;
    // 原版 damageable-entity.js rollEnemyGoldReward：(base 0 + L×4 + rand[1,10]) 先乘
    // 全局 .5 取整，再乘 rank 金币倍率（elite2/lord3，其余 1）与祭品系数取整。
    // UE 暂无地牢金币系数与怪物金币祭品键，两项按 1 保留在公式形状里。
    const double Raw=S.Level*4.+FMath::RandRange(1,10);
    const int64 BaseAmount=FMath::FloorToInt64(Raw*.5);
    return FMath::Max<int64>(0,FMath::FloorToInt64((double)BaseAmount*RankGoldMultiplier(S.Rank)*GoldTribute));
}
}
