#include "MonsterCoreStats.h"
#include "HandBrainMonster.h"
#include "FleshHandMonster.h"
#include "PoisonMaggotMonster.h"
#include "WolfMonster.h"
#include "InfectedDogMonster.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "FatZombie.h"
#include "Mutant3.h"
#include "WitchMonster.h"
#include "NurseZombie.h"
#include "SpitterZombie.h"
#include "MonsterCombatComponent.h"
#include "Components/ActorComponent.h"

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
    // 2026-09-28 用户要求移除翻倍，恢复 1.0（2026-09-23 曾拍板翻倍）。
    // 调参只改这一个数（对应原版 monsterGrowth 的全局成长层语义；六维/防具/奖励不受影响）。
    return 1.;
}

// 防御常量表（2026-09-28 用户拍板剔除怪物端六维）：Def/Mdef/CritRes 为原六维公式
// （def=⌊1.5体+.3力⌋/mdef=⌊1.2精+.3智⌋/critRes=⌊体⌋）的逐位烤入值，并已并入此前的
// 运行时字段覆盖：大手 mdef30、小手 mdef55、手脑 mdef65、巫婆 mdef55（狼系字段 12/8/5
// 与公式一致）。AttrWeight=战斗等级属性权重和（.08力+.08敏+.10体+.08智+.08精+.04运）。
// 行尾注释为烤入时的原六维 {力,敏,智,体,精,运}，仅供追溯，运行时不再参与任何计算。
// 感染减益改为对四值整体乘系数：与狼系字段语义一致，floor 位置差异 <1 点（原为缩放
// 六维后再 floor）。
bool Get(const AActor* Target,FMonsterCoreStats& Out)
{
    if(!Target)return false;
    FMonsterCoreStats S;bool bKnown=false;
    auto Fill=[&](int32 Def,int32 Mdef,int32 CritRes,double Weight,int32 Level,EMonsterRank Rank,EMonsterToughnessClass TClass)
    {S.Def=Def;S.Mdef=Mdef;S.CritRes=CritRes;S.AttrWeight=Weight;S.Level=Level;S.Rank=Rank;S.ToughnessClass=TClass;bKnown=true;};
    if(const auto* Hand=Cast<AFleshHandMonster>(Target))
    {
        if(Hand->bMinion)Fill(21,55,10,6.6,Hand->Level,Hand->Rank,EMonsterToughnessClass::Light);   // 小手 {20,30,5,10,10,10}
        else Fill(84,30,45,13.3,Hand->Level,Hand->Rank,EMonsterToughnessClass::Colossal);           // 大手 {55,25,10,45,15,10}
    }
    else if(const auto* H=Cast<AHandBrainMonster>(Target)){Fill(75,65,40,14.4,H->Level>0?H->Level:12,H->Rank,EMonsterToughnessClass::Colossal);} // {50,25,30,40,20,10}
    else if(const auto* Mg=Cast<APoisonMaggotMonster>(Target)){Fill(35,36,22,8.16,Mg->Level>0?Mg->Level:4,Mg->Rank,EMonsterToughnessClass::Caster);} // {7,13,24,22,24,13}
    else if(const auto* D=Cast<AInfectedDogMonster>(Target)){Fill(34,13,18,7.64,D->Level,D->Rank,EMonsterToughnessClass::Canine);} // {24,32,4,18,10,6}
    else if(const auto* W=Cast<AWolfMonster>(Target)){Fill(12,8,5,5.06,W->Level>0?W->Level:5,W->Rank,EMonsterToughnessClass::Canine);} // {16,28,3,5,6,8}
    else if(const auto* F=Cast<AFatZombie>(Target)){Fill(35,4,20,4.6,F->Level>0?F->Level:4,F->Rank,EMonsterToughnessClass::Heavy);} // {18,6,3,20,3,5}
    else if(const auto* U=Cast<AMutant3>(Target)){Fill(75,13,40,11.84,U->Level>0?U->Level:9,U->Rank,EMonsterToughnessClass::Heavy);} // {50,30,5,40,10,6}
    else if(const auto* C=Cast<AWitchMonster>(Target)){Fill(55,55,33,11.02,C->Level>0?C->Level:8,C->Rank,EMonsterToughnessClass::Caster);} // {20,15,30,33,25,13} mdef 字段覆盖 55
    else if(const auto* Sp=Cast<ASpitterZombie>(Target)){Fill(36,10,20,8.28,Sp->Level,Sp->Rank,EMonsterToughnessClass::Light);} // {22,38,10,20,6,5}
    else if(const auto* N=Cast<ANurseZombie>(Target)){Fill(0,0,0,2.76,N->Level>0?N->Level:3,N->Rank,EMonsterToughnessClass::Light);} // {3,27,3,0,0,3}
    else if(Target->ActorHasTag(TEXT("FatZombie")))Fill(35,4,20,4.6,4,EMonsterRank::Normal,EMonsterToughnessClass::Heavy);
    else if(Target->ActorHasTag(TEXT("Mutant3")))Fill(75,13,40,11.84,9,EMonsterRank::Elite,EMonsterToughnessClass::Heavy);
    else if(Target->ActorHasTag(TEXT("Witch")))Fill(55,55,33,11.02,8,EMonsterRank::Lord,EMonsterToughnessClass::Caster);
    if(!bKnown)return false;
    const double Infection=UProgressiveInfectionComponent::AttributeMultiplier(Target);
    S.Def=(int32)(S.Def*Infection);S.Mdef=(int32)(S.Mdef*Infection);
    S.CritRes=(int32)(S.CritRes*Infection);S.AttrWeight*=Infection;
    Out=S;
    return true;
}

int32 CombatLevel(const FMonsterCoreStats& S,double MaxHp,double SpeedPx)
{
    // 原版 deriveEnemyCombatLevel（enemy-base-stats.js）：属性权重和为主体（已常量化进
    // AttrWeight），HP 与移速提供封顶的非线性补充（HP≤+8、移速≤+4），rank 加成后
    // 四舍五入，下限 1。
    double Raw=1.+S.AttrWeight;
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
    // 2026-09-29 修复：阶级经验乘区（elite×2/lord×4/boss×20）此前只在图鉴显示、
    // 未进结算——AwardKill 与火球延迟击杀两条路径都经由本函数，在此一处乘上即成对生效。
    // 未注册目标恒为 1，行为不变。
    return FMath::Max<int64>(1,FMath::FloorToInt64((double)BaseReward*LevelDifferenceMultiplier(Victim,PlayerLevel)*RankExperienceMultiplier(S.Rank)));
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

// ── 韧性基准（2026-09-29 用户拍板：按类别×阶级）──────────────────────────
// 类别基线（normal 档）：阈值 / 破韧秒 / 锐·钝·冲三抗 / 脱战恢复秒。
// 数值承接 2026-09-20 各怪手调值的类别化归并（护士=轻装 60、胖子=重装 110、
// 巫婆=施法 80、狼=犬科 50（45/55 取整）、大手·手脑=巨物 150 原值保留）。
struct FToughnessBaseline
{
    float Threshold; float BreakSeconds;
    float Blade, Blunt, Impact; float RecoverySeconds;
};
static const FToughnessBaseline& ToughnessBaselineOf(EMonsterToughnessClass Class)
{
    static const TMap<EMonsterToughnessClass,FToughnessBaseline> Table =
    {
        {EMonsterToughnessClass::Light,    {60.f, 1.2f, .15f, 0.f,  .10f, 2.f}},
        {EMonsterToughnessClass::Heavy,    {110.f,1.4f, 0.f,  .20f, .25f, 2.5f}},
        {EMonsterToughnessClass::Caster,   {80.f, 1.2f, .10f, 0.f,  .25f, 2.f}},
        {EMonsterToughnessClass::Canine,   {50.f, 1.1f, 0.f,  .10f, .05f, 1.5f}},
        {EMonsterToughnessClass::Colossal, {150.f,0.9f, .10f, .05f, .20f, 2.f}},
    };
    const FToughnessBaseline* Found = Table.Find(Class);
    if(!Found) Found = Table.Find(EMonsterToughnessClass::Light);
    return *Found;
}
float ToughnessRankThresholdScale(EMonsterRank Rank)
{
    // 阶级只缩放"破韧难度"与"破韧收益窗口"；杂鱼更脆、领主近乎不可打断。
    switch(Rank)
    {
    case EMonsterRank::Minor: return .7f;
    case EMonsterRank::Elite: return 1.3f;
    case EMonsterRank::Lord:  return 1.6f;
    case EMonsterRank::Boss:  return 2.f;
    default: return 1.f;
    }
}
float ToughnessRankBreakScale(EMonsterRank Rank)
{
    switch(Rank)
    {
    case EMonsterRank::Minor: return .85f;
    case EMonsterRank::Elite: return 1.15f;
    case EMonsterRank::Lord:  return 1.3f;
    case EMonsterRank::Boss:  return 1.5f;
    default: return 1.f;
    }
}
void ApplyToughnessProfile(AActor* Monster)
{
    FMonsterCoreStats S;
    if(!Monster || !Get(Monster,S)) return;
    auto* Combat = Monster->FindComponentByClass<UMonsterCombatComponent>();
    if(!Combat) return;
    const FToughnessBaseline& Base = ToughnessBaselineOf(S.ToughnessClass);
    Combat->ToughnessThreshold = Base.Threshold * ToughnessRankThresholdScale(S.Rank);
    Combat->ToughnessBreakSeconds = Base.BreakSeconds * ToughnessRankBreakScale(S.Rank);
    Combat->BladeResistance = Base.Blade;
    Combat->BluntResistance = Base.Blunt;
    Combat->ImpactResistance = Base.Impact;
    Combat->ToughnessRecoverySeconds = Base.RecoverySeconds;
}
}
