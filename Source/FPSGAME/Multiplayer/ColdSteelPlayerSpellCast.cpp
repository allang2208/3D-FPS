#include "ColdSteelPlayerState.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "ColdSteelMapMarkerSharing.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/HighlandBreakSweep.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../Weapons/StarMarrowComponent.h"
#include "ColdSteelPreparedHit.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ConicalHammerSeat.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Monsters/RootCrownHitComponent.h"
#include "../Monsters/HeQueMonster.h"
#include "../Monsters/HumanoidHitVolumeData.h"
#include "../Combat/RangedAttackQuery.h"
#include "ColdSteelNetWorldSubsystem.h"
#include "ColdSteelNetSessionSubsystem.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "ColdSteelProfileTransfer.h"
#include "Serialization/JsonSerializer.h"
#include "ColdSteelProfileMerge.h"
#include "UppercutStaminaReceipt.h"
#include "../Building/WoodworkingQuality.h"
#include "../Building/ForgingQuality.h"
#include "../Building/GunAssemblyQuality.h"
#include "../Items/FoodSpoilage.h"
#include "../UI/ColdSteelProfileRecovery.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/BoundCongregate.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/TubeShotgunAssets.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/SwordUppercutWeapon.h"
#include "../Skills/WhirlwindTypes.h"
#include "../Skills/MagicOcclusion.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireballProjectile.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceSpikeVolley.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/MeteorGround.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/IceSpikeTypes.h"
#include "../Skills/IceWallTypes.h"
#include "../Skills/BlizzardTypes.h"
#include "../Skills/HolyLightTypes.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/FireMagicTypes.h"
#include "../Skills/ElectricMagicTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelCurrency.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Weapons/AzureDragonReach.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "../Weapons/Kukri/OffhandKukriThrust.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/LMGStabilityGrip.h"
#include "../Weapons/JingangRuneComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Kukri/SwiftFalconHeavy.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Weapons/Staff/StaffQuickCombatMotion.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Spellbook/SpellbookFocusMana.h"
#include "../Weapons/MagicCrystalMana.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/SniperSuppressorAssets.h"
#include "../Weapons/WeaponShotNoise.h"
#include "../Weapons/WeaponDamageFalloff.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/NetConnection.h"
#include "Engine/HitResult.h"
#include "CollisionQueryParams.h"
#include "Engine/ActorInstanceHandle.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameState.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"


using ColdSteelProfileTransfer::SaveToBlob;
using ColdSteelProfileTransfer::BlobToSave;

void AColdSteelPlayerState::CancelPendingNetworkCast()
{
    if(!HasAuthority()||PendingCastSkill.IsNone())return;
    const FName Skill=PendingCastSkill;const float Paid=PendingCastPaidMana;
    PendingCastSkill=NAME_None;PendingCastPaidMana=0.f;PendingCastPawn.Reset();PendingIdentifiedCastId=0;
    if(PendingCastOrb.IsValid())PendingCastOrb->Destroy();
    PendingCastOrb.Reset();
    if(ShadowModel)ShadowModel->RefundUnreleasedCast(Paid,Skill);
    bServerDirty=true;
}

uint32 AColdSteelPlayerState::RequestCastSpell(FColdSteelNetCastRequest Request)
{
    Request.SourcePawn=GetPawn();Request.Sequence=++LocalCastSequence;
    if(!Request.Sequence)Request.Sequence=++LocalCastSequence;
    if((Request.SkillId==TEXT("dragonBreath")||Request.SkillId==TEXT("stormDomain")||Request.SkillId==TEXT("flameArmor")||Request.SkillId==TEXT("iceArmor")||Request.SkillId==TEXT("lightningHaste")||Request.SkillId==TEXT("meteor"))&&Request.Phase==0)Request.CastId=Request.Sequence;
    ServerCastSpell(Request);
    return Request.Sequence;
}

void AColdSteelPlayerState::ServerCastSpell_Implementation(const FColdSteelNetCastRequest& Request)
{
    if (GetLocalRole() != ROLE_Authority) return;
    if (GetWorld() && GetWorld()->GetNetMode() == NM_Standalone) return;
    if(!Request.Sequence||Request.Sequence<=ProcessedCastSequence)return;
    ProcessedCastSequence=Request.Sequence;bServerDirty=true;
    if(!Request.SourcePawn||Request.SourcePawn!=GetPawn()){ShadowMirrorTimer=3.f;return;}
    // Limit new reservations only. Reliable release/cancel transitions must always settle.
    const double Now = GetWorld()->GetTimeSeconds();
    if(Request.Phase==0)
    {
        if(HasAuthorityConsumableReservation(Request.SourcePawn)){ClientCastResult(Request.SkillId,Request.Phase,4,Request.SourcePawn,Request.Sequence,Request.CastId);return;}
        if(Now-LastCastRequestAt<.15){ClientCastResult(Request.SkillId,Request.Phase,4,Request.SourcePawn,Request.Sequence,Request.CastId);return;}
        LastCastRequestAt=Now;
    }
    ExecuteCastRequest(Request);
}

namespace
{
// 各技能在服务端落地的最小校验：影子档扣账入口 + 对应组件指针。Phase1 的具体执行在组件侧。
struct FNetCastSkill { FName Id; };
const FNetCastSkill NetCastSkills[] = {
    { TEXT("fireball") }, { TEXT("iceSpike") }, { TEXT("iceWall") }, { TEXT("blizzard") },
    { TEXT("holyLight") }, { TEXT("lightning") }, { TEXT("meteor") }, { TEXT("flameArmor") }, { TEXT("iceArmor") }, { TEXT("lightningHaste") }, { TEXT("dragonBreath") },
    { TEXT("stormDomain") }, { TEXT("thunderLance") }, { TEXT("starMarrowCharge") },
};
bool IsNetCastSkill(FName Id)
{
    for (const auto& S : NetCastSkills) if (S.Id == Id) return true;
    return false;
}
}

void AColdSteelPlayerState::ExecuteCastRequest(const FColdSteelNetCastRequest& Request)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    const auto Reject = [&](uint8 Code)
    {
        if(Request.Phase==1&&PendingCastSkill==Request.SkillId&&
            ((Request.SkillId!=TEXT("dragonBreath")&&Request.SkillId!=TEXT("stormDomain")&&Request.SkillId!=TEXT("flameArmor")&&Request.SkillId!=TEXT("iceArmor")&&Request.SkillId!=TEXT("lightningHaste")&&Request.SkillId!=TEXT("meteor"))||Request.CastId==PendingIdentifiedCastId))CancelPendingNetworkCast();
        ClientCastResult(Request.SkillId, Request.Phase, Code,Request.SourcePawn,Request.Sequence,Request.CastId);
    };
    const auto Accept = [&](bool bNotifyRelease=true) {
        if(bNotifyRelease&&Request.Phase==1&&ShadowModel)ShadowModel->NotifyMagicReleased();
        ClientCastResult(Request.SkillId, Request.Phase, 0,Request.SourcePawn,Request.Sequence,Request.CastId); };
    if (!ShadowModel) { Reject(1); return; }
    const bool Dragon=Request.SkillId==TEXT("dragonBreath");
    const bool Identified=Dragon||Request.SkillId==TEXT("stormDomain")||Request.SkillId==TEXT("flameArmor")||Request.SkillId==TEXT("iceArmor")||Request.SkillId==TEXT("lightningHaste")||Request.SkillId==TEXT("meteor");
    if (!IsNetCastSkill(Request.SkillId)||Request.Phase>(Dragon?4:3)) { Reject(2); return; }
    if(Request.SkillId==TEXT("starMarrowCharge"))
    {
        const auto* Weapon=ShadowModel->Equipped();
        if(Request.Phase!=0||Request.WeaponInstance.IsEmpty()||!Weapon||Request.WeaponInstance!=Weapon->InstanceId){Reject(2);return;}
    }
    if(Identified&&(!Request.CastId||(Request.Phase==0&&Request.CastId!=Request.Sequence))){Reject(2);return;}
    const double Now = GetWorld()->GetTimeSeconds();

    // Dragon release and stop share this PlayerState's reliable channel.
    // A repeated/late stop only settles the identified cast, never its successor.
    if(Dragon&&Request.Phase==4)
    {
        if(PendingCastSkill==Request.SkillId&&PendingIdentifiedCastId==Request.CastId)CancelPendingNetworkCast();
        if(Pawn)if(auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>())Fire->NetStopDragonBreath(Request.CastId);
        Accept();return;
    }

    // ── Phase 2/3 取消/弃置：通用收尾——销毁在途实体，按技能退蓝/清占用。 ──
    if (Request.Phase == 2 || Request.Phase == 3)
    {
        if (PendingCastSkill == Request.SkillId&&(!Identified||PendingIdentifiedCastId==Request.CastId))
        {
            if (PendingCastOrb.IsValid()) { PendingCastOrb->Destroy(); PendingCastOrb.Reset(); }
            if (Request.Phase == 2||Request.SkillId==TEXT("blizzard")) ShadowModel->RefundUnreleasedCast(PendingCastPaidMana, Request.SkillId);
            else
            {
                if (Request.SkillId == TEXT("fireball")) ShadowModel->FinishFireballCast();
                else if (Request.SkillId == TEXT("iceSpike")) ShadowModel->FinishIceSpikeCast(FIceSpikeRewards());
                // iceWall 无独立 Finish：弃置未释放的种子墙只占用手位，CommitIceWallRelease 之前不产生结算。
                else if (Request.SkillId == TEXT("blizzard")) ShadowModel->FinishBlizzardCast(FBlizzardRewards());
                else if (Request.SkillId == TEXT("holyLight")) ShadowModel->FinishHolyLightCast(FHolyLightRewards());
                else if (Request.SkillId == TEXT("lightning")) ShadowModel->FinishLightningCast(FLightningRewards());
                else if (FireMagic::IsSkill(Request.SkillId)) ShadowModel->FinishFireMagicCast(Request.SkillId, FFireMagicRewards());
                else if (ElectricMagic::IsSkill(Request.SkillId)) ShadowModel->FinishElectricMagicCast(Request.SkillId, FElectricMagicRewards());
            }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;PendingIdentifiedCastId=0;
        }
        Accept();
        return;
    }
    if(!Pawn){Reject(1);return;}
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead()){Reject(5);return;}
    if(Request.Phase==1&&PendingCastPawn.Get()!=Pawn){Reject(5);return;}
    if(Identified&&Request.Phase==1&&PendingIdentifiedCastId!=Request.CastId){Reject(3);return;}

    // Restraint blocks both prepare and release, while cancellation/refunds
    // above remain available. Firearm reports use their separate hit path.
    if(UBoundCongregateCaptureComponent::IsCaptured(Pawn)){Reject(8);return;}
    // Knocked down: same refusal as restraint, cancellation/refunds above stay available.
    if(UPlayerKnockdownComponent::IsKnockedDown(Pawn)){Reject(8);return;}

    if(Request.SkillId==TEXT("starMarrowCharge"))
    {
        auto* Core=Pawn->FindComponentByClass<UStarMarrowComponent>();
        if(!PendingCastSkill.IsNone()||!Core||!Core->ActivateCharge(ShadowModel)){Reject(6);return;}
        ClientStarMarrowSpend(Pawn,ShadowModel->Snapshot().StarMarrowManaSpent);
        ShadowMirrorTimer=3.f;Accept();return;
    }

    // ── Phase 1 释放：按技能分派到组件服务端入口（影子档案校验在里面）。 ──
    if (Request.Phase == 1)
    {
        if (Request.SkillId == TEXT("fireball"))
        {
            auto* Ball = Cast<AFPSFireballProjectile>(PendingCastOrb.Get());
            if (PendingCastSkill != TEXT("fireball") || !Ball || Now - PendingCastAt > 35.0) { Reject(3); return; }
            Ball->LaunchAt(Request.AimPoint);
            ShadowModel->FinishFireballCast();
            PendingCastOrb.Reset(); PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("iceSpike"))
        {
            auto* Volley = Cast<AFPSIceSpikeVolley>(PendingCastOrb.Get());
            if (PendingCastSkill != TEXT("iceSpike") || !Volley || Now - PendingCastAt > 35.0) { Reject(3); return; }
            Volley->LaunchAt(Request.AimPoint);
            PendingCastOrb.Reset(); PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("iceWall"))
        {
            if (PendingCastSkill != TEXT("iceWall")) { Reject(3); return; }
            auto* Wall = Pawn->FindComponentByClass<UFPSIceWallComponent>();
            if (!Wall || !Wall->NetCommitWall(Pawn, Request, ShadowModel, PendingIceWallStats)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("blizzard"))
        {
            if (PendingCastSkill != TEXT("blizzard")) { Reject(3); return; }
            auto* B = Pawn->FindComponentByClass<UFPSBlizzardComponent>();
            if (!B || !B->NetCommitZone(Pawn, Request, ShadowModel, PendingBlizzardStats)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if(Request.SkillId==TEXT("lightningHaste"))
        {
            auto* Ice=Pawn->FindComponentByClass<UFPSLightningHasteComponent>();
            if(PendingCastSkill!=Request.SkillId||!Ice||!Ice->NetRelease(Pawn,Request,ShadowModel,PendingLightningHasteStats)){Reject(7);return;}
            // CommitLightningHasteCast already dispatches the release notification.
            PendingCastSkill=NAME_None;PendingCastPaidMana=0;PendingIdentifiedCastId=0;Accept(false);return;
        }
        if(Request.SkillId==TEXT("iceArmor"))
        {
            auto* Ice=Pawn->FindComponentByClass<UFPSIceArmorComponent>();
            if(PendingCastSkill!=Request.SkillId||!Ice||!Ice->NetRelease(Pawn,Request,ShadowModel,PendingIceArmorStats)){Reject(7);return;}
            PendingCastSkill=NAME_None;PendingCastPaidMana=0;PendingIdentifiedCastId=0;Accept();return;
        }
        if (Request.SkillId == TEXT("holyLight"))
        {
            if (PendingCastSkill != TEXT("holyLight")) { Reject(3); return; }
            auto* H = Pawn->FindComponentByClass<UFPSHolyLightComponent>();
            if (!H || !H->NetRelease(Pawn, Request, ShadowModel, PendingHolyLightStats)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("lightning"))
        {
            if (PendingCastSkill != TEXT("lightning")) { Reject(3); return; }
            auto* L = Pawn->FindComponentByClass<UFPSLightningComponent>();
            if (!L || !L->NetRelease(Pawn, Request, ShadowModel, PendingLightningStats)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (FireMagic::IsSkill(Request.SkillId))
        {
            if (PendingCastSkill != Request.SkillId) { Reject(3); return; }
            auto* F = Pawn->FindComponentByClass<UFPSFireMagicComponent>();
            auto Release=Request;
            const bool Meteor=Request.SkillId==TEXT("meteor");
            if(Meteor){Release.AimPoint=PendingMeteorPoint;Release.AimNormal=PendingMeteorNormal;}
            if (!F || !F->NetRelease(Pawn, Release, ShadowModel, PendingFireMagicStats,Meteor)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;PendingIdentifiedCastId=0;
            Accept(); return;
        }
        if (ElectricMagic::IsSkill(Request.SkillId))
        {
            if (PendingCastSkill != Request.SkillId) { Reject(3); return; }
            auto* E = Pawn->FindComponentByClass<UFPSElectricMagicComponent>();
            if (!E || !E->NetRelease(Pawn, Request, ShadowModel, PendingElectricMagicStats)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;PendingIdentifiedCastId=0;
            Accept(); return;
        }
        Reject(2); return;
    }

    // ── Phase 0 凝聚：影子档校验法耗/冷却并扣账；带悬停体的技能同时生成权威实体。 ──
    if (PendingCastOrb.IsValid() || PendingCastSkill != NAME_None) { Reject(4); return; }
    if(const auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();Fire&&Fire->IsDragonBreathActive()){Reject(4);return;}
    if (auto* HP = Pawn->FindComponentByClass<UFPSCombatHealthComponent>(); HP && HP->IsDead()) { Reject(5); return; }
    // Skill tree (2026-11-15): the shadow profile must have learned the spell. Net id "lightning" is lightningStrike;
    // ids outside the tree (starMarrowCharge, ...) are always learned.
    if (!ShadowModel->IsSkillLearned(Request.SkillId == TEXT("lightning") ? FName(TEXT("lightningStrike")) : Request.SkillId)) { Reject(2); return; }

    if (Request.SkillId == TEXT("fireball"))
    {
        const FFireballCast Stats = ShadowModel->FireballStats();
        if (!ShadowModel->BeginFireballCast()) { Reject(6); return; }
        auto* Ability = Pawn->FindComponentByClass<UFPSFireballComponent>();
        auto* Ball = Ability ? Ability->SpawnOrbForCast(Pawn, Stats) : nullptr;
        if (!Ball) { ShadowModel->RefundUnreleasedCast(Stats.ManaCost, TEXT("fireball")); Reject(7); return; }
        PendingCastOrb = Ball; PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("iceSpike"))
    {
        const FIceSpikeCast Stats = ShadowModel->IceSpikeStats();
        if (!ShadowModel->BeginIceSpikeCast(Stats)) { Reject(6); return; }
        auto* Ability = Pawn->FindComponentByClass<UFPSIceSpikeComponent>();
        auto* Volley = Ability ? Ability->SpawnVolleyForCast(Pawn, Stats) : nullptr;
        if (!Volley) { ShadowModel->RefundUnreleasedCast(Stats.ManaCost, TEXT("iceSpike")); Reject(7); return; }
        PendingCastOrb = Volley; PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("iceWall"))
    {
        const FIceWallCast Stats = ShadowModel->IceWallStats();
        if (!ShadowModel->BeginIceWallCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
        PendingIceWallStats = Stats;
    }
    else if (Request.SkillId == TEXT("blizzard"))
    {
        const FBlizzardCast Stats = ShadowModel->BlizzardStats();
        if (!ShadowModel->BeginBlizzardCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
        PendingBlizzardStats = Stats;
    }
    else if(Request.SkillId==TEXT("lightningHaste"))
    {
        const auto Stats=ShadowModel->LightningHasteStats();const float Before=ShadowModel->Snapshot().Mana;
        if(!ShadowModel->BeginLightningHasteCast(Stats)){Reject(6);return;}
        PendingCastPaidMana=FMath::Max(0.f,Before-ShadowModel->Snapshot().Mana);PendingLightningHasteStats=Stats;
    }
        else if(Request.SkillId==TEXT("iceArmor"))
    {
        const auto Stats=ShadowModel->IceArmorStats();const float Before=ShadowModel->Snapshot().Mana;
        if(!ShadowModel->BeginIceArmorCast(Stats)){Reject(6);return;}
        PendingCastPaidMana=FMath::Max(0.f,Before-ShadowModel->Snapshot().Mana);PendingIceArmorStats=Stats;
    }
    else if (Request.SkillId == TEXT("holyLight"))
    {
        const FHolyLightCast Stats = ShadowModel->HolyLightStats();
        if (!ShadowModel->BeginHolyLightCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
        PendingHolyLightStats = Stats;
    }
    else if (Request.SkillId == TEXT("lightning"))
    {
        const FLightningCast Stats = ShadowModel->LightningStats();
        if (!ShadowModel->BeginLightningCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
        PendingLightningStats = Stats;
    }
    else if (FireMagic::IsSkill(Request.SkillId))
    {
        const FFireMagicCast Stats = ShadowModel->FireMagicStats(Request.SkillId);
        FVector Point=Request.AimPoint,Normal=Request.AimNormal;FString Failure;
        if(Request.SkillId==TEXT("meteor")&&!MeteorGround::Validate(Pawn,Stats.Range,Point,Normal,true,Failure))
        {Reject(7);return;}
        const float BeforeMana=ShadowModel->Snapshot().Mana;
        if (!ShadowModel->BeginFireMagicCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = FMath::Max(0.f,BeforeMana-ShadowModel->Snapshot().Mana);
        PendingFireMagicStats = Stats;
        if(Request.SkillId==TEXT("meteor")){PendingMeteorPoint=Point;PendingMeteorNormal=Normal;}
    }
    else if (ElectricMagic::IsSkill(Request.SkillId))
    {
        const FElectricMagicCast Stats = ShadowModel->ElectricMagicStats(Request.SkillId);
        if (!ShadowModel->BeginElectricMagicCast(Request.SkillId, Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.Hit.ManaCost;
        PendingElectricMagicStats = Stats;
    }
    PendingCastSkill = Request.SkillId; PendingCastAt = Now; PendingCastPawn=Pawn;
    PendingIdentifiedCastId=Identified?Request.CastId:0;
    // Snapshot first, then consume: match local casts, including later cancellation.
    if(auto* Status=Pawn->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
    Accept();
}

void AColdSteelPlayerState::ClientStarMarrowSpend_Implementation(AFPSGAMECharacter* Character,double Total)
{
    if(!Character||Character!=GetPawn())return;
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Model->ReconcileStarMarrowSpend(Total);
}

void AColdSteelPlayerState::ClientCastResult_Implementation(FName SkillId, uint8 Phase, uint8 Code,APawn* SourcePawn,uint32 Sequence,uint32 CastId)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    if (!Pawn||Pawn!=SourcePawn) return;
    if(SkillId==TEXT("starMarrowCharge")){if(auto* Core=Pawn->FindComponentByClass<UStarMarrowComponent>())Core->NetCastResult(Sequence,Code);return;}
    if(SkillId==TEXT("dragonBreath"))
    {
        if(auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>())Fire->NetDragonCastResult(Phase,Code,CastId);
        return;
    }
    if(SkillId==TEXT("stormDomain"))
    {
        if(auto* Electric=Pawn->FindComponentByClass<UFPSElectricMagicComponent>())Electric->NetDomainCastResult(Phase,Code,CastId);
        return;
    }
    if(SkillId==TEXT("flameArmor"))
    {
        if(auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>())Fire->NetArmorCastResult(Phase,Code,CastId);
        return;
    }
    if(SkillId==TEXT("iceArmor")){if(auto* Ice=Pawn->FindComponentByClass<UFPSIceArmorComponent>())Ice->NetCastResult(Phase,Code,CastId);return;}
    if(SkillId==TEXT("lightningHaste")){if(auto* Ice=Pawn->FindComponentByClass<UFPSLightningHasteComponent>())Ice->NetCastResult(Phase,Code,CastId);return;}
    if(SkillId==TEXT("meteor")){if(auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>())Fire->NetMeteorCastResult(Phase,Code,CastId);return;}
    if(Sequence<LocalCastSequence)return;
    // 把回执路由到发起技能的组件；各组件自己决定拒收/取消的本地收尾。
    const auto Receipt = [Phase, Code](auto* C)
    {
        if (!C) return;
        if (Code == 0 && (Phase == 2 || Phase == 3)) C->NetCastCancelled(Phase);
        else if (Code != 0) C->NetCastRejected(Phase, Code);
    };
    if (SkillId == TEXT("fireball")) Receipt(Pawn->FindComponentByClass<UFPSFireballComponent>());
    else if (SkillId == TEXT("iceSpike")) Receipt(Pawn->FindComponentByClass<UFPSIceSpikeComponent>());
    else if (SkillId == TEXT("iceWall")) Receipt(Pawn->FindComponentByClass<UFPSIceWallComponent>());
    else if (SkillId == TEXT("blizzard"))
    {
        auto* Blizzard=Pawn->FindComponentByClass<UFPSBlizzardComponent>();
        if(Blizzard&&Code==0&&Phase<2)Blizzard->NetCastAccepted(Phase);
        else Receipt(Blizzard);
    }
    else if (SkillId == TEXT("holyLight"))
    {
        auto* C=Pawn->FindComponentByClass<UFPSHolyLightComponent>();
        if(C&&Code==0&&Phase<2)C->NetCastAccepted(Phase);else Receipt(C);
    }
    else if (SkillId == TEXT("lightning"))
    {
        auto* C=Pawn->FindComponentByClass<UFPSLightningComponent>();
        if(C&&Code==0&&Phase<2)C->NetCastAccepted(Phase);else Receipt(C);
    }
    else if (FireMagic::IsSkill(SkillId))
    {
        auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
        Receipt(Fire);
    }
    else if (ElectricMagic::IsSkill(SkillId)) Receipt(Pawn->FindComponentByClass<UFPSElectricMagicComponent>());
}

// ============================================================================
// 命中转发器（ColdSteelNet 模块注册到 ColdSteelSkills::NetHitForward()）
// ============================================================================

