#include "../Weapons/MagicCrystalMana.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Dungeon/DungeonLayout.h"
#include "../Weapons/JingangRuneComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelIncineratorStorage.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "ColdSteelContainerSearchSubsystem.h"
#include "GameFramework/PlayerController.h"
#include "ColdSteelProfileRecovery.h"
#include "../Items/FoodSpoilage.h"
#include "../Items/CampfireFoodCatalog.h"
#include "ColdSteelCurrency.h"
#include "ColdSteelItemRarity.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/RuneOrbBladesComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "EngineUtils.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FrostSwordRunes.h"
#include "Misc/SecureHash.h"

using namespace ColdSteelInventory;
#include "../Skills/ColdSteelSpellRewards.h"

int64 UColdSteelStatusModel::MaxExperience()const{return(20ll+Level*20ll+int64(Level)*Level*12)*8;}
bool UColdSteelStatusModel::GainExperience(int64 Amount)
{
    if(Amount<=0||Amount>1000000000000ll)return false;SyncRuntime();auto P=Snapshot();const int64 Granted=FMath::FloorToInt64(Amount*TributeEffect(TEXT("expPercent")));P.Experience+=Granted;
    ColdSteelSpellRewards::ApplyExperienceLevels(P);
    const int64 Gained=GainedCharacterExperience(P);
    const FGuid LeveledHorse=CreditPresentMountExperience(P,Gained);
    const bool bCommitted=CommitState(P);
    if(bCommitted)
    {
        ApplyCommittedMountLevel(LeveledHorse);
        QueueExperienceNotice(Gained);
    }
    return bCommitted;
}
bool UColdSteelStatusModel::AwardKill(AActor* Victim,int64 Reward)
{
    ApplyKillStaminaRecovery(Victim);
    if(!Victim||RewardedVictims.Contains(Victim)||Reward<=0||Reward>1000000000)return false;
    if(ActiveFireballRewards && ActiveFireballRewards->Victim==Victim){ActiveFireballRewards->Kills.FindOrAdd(Victim)=Reward;return true;}
    SyncRuntime();auto P=Snapshot();if(!DungeonLayout::RecordKill(P.DungeonRun,Victim))return false;P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);
    // 2026-09-23 迁移原 exp-system.js/goldDrop：经验按玩家与怪物配置等级的压级/越级倍率
    // ×阶级经验乘区（elite2/lord4/boss20，2026-09-29 起接入结算，未注册目标恒 1），
    // 灵魂与最终击杀经验等额，复用等级、阶级与经验祭品加成后的同一整数奖励。
    const int64 Granted=FMath::FloorToInt64(MonsterCoreStats::ScaleKillExperience(Victim,Level,Reward)*TributeEffect(TEXT("expPercent")));
    // 诊断（2026-09-29"杀怪零经验"排查）：逐杀打印基础/到账/等级差/当前进度，
    // 下次实测若仍见零经验，本行可直接定位是压级、满级钳制还是提交被拒。
    UE_LOG(LogTemp,Display,TEXT("EXP_KILL victim=%s base=%lld granted=%lld playerLv=%d tribute=%.2f exp=%lld/need=%lld"),*Victim->GetName(),Reward,Granted,Level,TributeEffect(TEXT("expPercent")),P.Experience,MaxExperience());
    P.Experience+=Granted;
    if(Granted>0 && !CreditCombatSouls(P,Granted))return false;
    if(ActiveTrainingHit && ActiveTrainingHit->Victim==Victim && ActiveTrainingHit->bEligible)
    {
        ActiveTrainingHit->bKillAttempted=true;
        if(!ActiveTrainingHit->SkillId.IsNone())
        {
            const auto& Skill=MasteryDefinition(ActiveTrainingHit->SkillId);
            const int32 MasteryXP=Skill.KillExperience+Skill.HitExperience+ActiveTrainingHit->ExtraExperience+(ActiveTrainingHit->bCritical?Skill.CriticalExperience:0);
            ColdSteelSkills::AddExperience(P,Skill,MasteryXP);
            if(ColdSteelSkills::IsTwoHandedSubMastery(ActiveTrainingHit->SkillId))
                ColdSteelSkills::AddExperience(P,MasteryDefinition(TEXT("twoHandedMastery")),MasteryXP);
        }
        if(ActiveTrainingHit->bCritical)ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,CriticalStrikeSkill.CriticalHitExperience+CriticalStrikeSkill.CriticalKillExperience);
        if(ActiveTrainingHit->bMelee)ColdSteelSkills::AddExperience(P,DexterousHandsSkill,DexterousHandsSkill.MeleeKillExperience+DexterousHandsSkill.MeleeHitExperience);
        if(ActiveTrainingHit->bPerfectBowHit)ColdSteelSkills::AddExperience(P,DexterousHandsSkill,DexterousHandsSkill.PerfectBowHitExperience+DexterousHandsSkill.PerfectBowKillExperience);
        if(ActiveTrainingHit->bHeartPiercingArrow)
        {
            const auto& Piercing=MasteryDefinition(TEXT("heartPiercingArrow"));
            ColdSteelSkills::AddExperience(P,Piercing,Piercing.HitExperience+Piercing.KillExperience);
        }
    }
    ColdSteelSpellRewards::ApplyExperienceLevels(P);
    // 击杀奖励先落在实时档案里，写盘交给定时自动存档；升级仍走即时带校验事务。
    if(!StageTraining(MoveTemp(P)))return false;RewardedVictims.Add(Victim);
    // 白玉/人参献祭：击杀后 1 秒内回复 maxHp×(killHpHealPercent-1) 与 maxMp×(killMpHealPercent-1)。
    if(const double HpRatio=TributeEffect(TEXT("killHpHealPercent"))-1;HpRatio>0)
        if(auto* H=CurrentPawn.Get()?CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr)if(!H->IsDead())
        {KillProcHp+=H->MaxHealth*HpRatio;KillProcTime=1;if(auto* S=UCombatStatusFormula::GetOrAdd(CurrentPawn.Get()))S->ShowProcTile(TEXT("marbleHeal"),1);}
    if(const double MpRatio=TributeEffect(TEXT("killMpHealPercent"))-1;MpRatio>0)
        if(CurrentPawn.IsValid()){KillProcMp+=Derived(TEXT("maxMp"))*MpRatio;KillProcTime=1;if(auto* S=UCombatStatusFormula::GetOrAdd(CurrentPawn.Get()))S->ShowProcTile(TEXT("ginsengHeal"),1);}
    return true;
}
