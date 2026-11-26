#include "RuneSwordComponent.h"
#include "HighlandBreakSweep.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "HighlandRidgeThrust.h"
#include "HighlandRidgeGatherComponent.h"
#include "RuneSwordGuardTuning.h"
#include "StarMarrowChargeMotion.h"
#include "../Characters/FPSComponentVisibility.h"
#include "../Skills/LightningHasteSpeed.h"
#include "BeiweiSwordTrailComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelGenericMelee.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "SprintCameraMotion.h"
#include "TangDaoGuardComponent.h"
#include "PanChiGuardComponent.h"
#include "RuneSwordMeshComponent.h"
#include "RuneSwordWhirlwindFeel.h"
#include "RuneSwordOverheadFeel.h"
#include "RuneSwordUppercutMotion.h"
#include "../Skills/ChainSlashAssets.h"
#include "RuneSwordInspectFeel.h"
#include "RuneSwordRisingDragon.h"
#include "MeleeRuneVisual.h"
#include "MeleeGuardAssets.h"
#include "ModularSwordVisual.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "RuneSwordCombatTuning.h"
#include "MeleeSmallTargetQuery.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/QuickCombatPistolMotion.h"
#include "../Skills/QuickCombatImpactShake.h"
#include "ColdSteelEnchantmentCombat.h"
#include "FPSRiftSlashProjectile.h"
#include "SwordWaveTuning.h"
#include "GunsmithSystem.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "NiagaraSystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "WeaponGripProfile.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/ScopeExit.h"

FRuneSwordBladeSample URuneSwordComponent::ReadBlade(const FTransform& AimFrame) const
{
    const FQuat ImportBasis=FRotator(0,90,0).Quaternion();
    FRuneSwordBladeSample Sample;
    // The rune sword already animates its Blade_Base/Tip tracks at the accepted
    // 80 percent size. Preserve those tracks when only splitting its surface.
    if(ModularSword&&!ModularSword->ComponentHasTag(TEXT("SwordTraceFromAnimation")))
    {
        const FTransform Frame=ModularSword->GetRelativeTransform()*Viewmodel->GetSocketTransform(TEXT("WPN_root"),RTS_Component);
        const auto Point=[&](FVector P){return AimFrame.TransformPosition(ImportBasis.RotateVector(Frame.TransformPosition(P)));};
        Sample={Point(ModularBladeBase),Point(ModularTraceTip),AimFrame.GetLocation(),AimFrame.GetUnitAxis(EAxis::X)};
    }
    else
    {
        const auto Point=[&](FName Bone){return AimFrame.TransformPosition(ImportBasis.RotateVector(
            Viewmodel->GetSocketTransform(Bone,RTS_Component).GetLocation()));};
        Sample={Point(TEXT("Blade_Base")),Point(TEXT("Blade_Tip")),AimFrame.GetLocation(),AimFrame.GetUnitAxis(EAxis::X)};
    }
    if(bPommelAttack)
    {
        // The fourth hit strikes with the counterweight, which sits behind the
        // guard: sample that end of the hilt instead of the blade, so the swept
        // volume is the striking face rather than a blade that is out of view.
        const FVector Axis=(Sample.Tip-Sample.Base).GetSafeNormal(SMALL_NUMBER,Sample.Forward);
        const FVector Guard=Sample.Base-Axis*RuneSwordPommelRhythm::BladeBaseCM;
        Sample.Base=Guard;
        Sample.Tip=Guard-Axis*PommelDepthCM;
    }
    return Sample;
}

void URuneSwordComponent::SweepBlade(const FRuneSwordBladeSample& From,const FRuneSwordBladeSample& To)
{
    const bool RisingDragon=IsRisingDragonFinisher();
    if((bThrustAttack||bUppercut) && !HitActors.IsEmpty())return;
    FRuneSwordTraceSettings Trace;
    Trace.Radius=RuneSwordCombat::BladeRadius*SwingRangeMultiplier;
    if(bPommelAttack)
    {
        // Blunt head, narrow forward corridor, one target: the counterweight does
        // not cleave like a blade pass and gets no thrust reach bonus.
        Trace.Radius=RuneSwordPommelRhythm::HeadRadius*SwingRangeMultiplier;
        Trace.ForwardCorridorRadius=RuneSwordPommelRhythm::CorridorRadius*SwingRangeMultiplier;
        Trace.bCleavePawns=false;
    }
    if(bThrustAttack||bUppercut||RisingDragon)
    {
        Trace.Radius=RuneSwordThrustRhythm::BladeRadius*SwingRangeMultiplier;
        Trace.ForwardCorridorRadius=RuneSwordThrustRhythm::CorridorRadius*SwingRangeMultiplier;
        // Tengyun's combo finisher cleaves within its existing swept corridor.
        // The separately activated uppercut and factory thrust remain single-target.
        Trace.bCleavePawns=RisingDragon;
        Trace.bAreaDamage=RisingDragon;
    }
    auto* Pawn=Character.Get();
    if(bAzureDragonEquipped&&!bOverheadAttack&&!bThrustAttack&&!bPommelAttack&&!bUppercut&&!IsRisingDragonFinisher())
    {
        // Learn which way this clip's blade travels (aim space), so Azure Dragon raises the matching claw.
        const auto Lateral=[](const FRuneSwordBladeSample& S)
        {return float(FVector::DotProduct(S.Tip-S.Origin,FVector::CrossProduct(FVector::UpVector,S.Forward).GetSafeNormal()));};
        AzureDragonSwingLateral+=Lateral(To)-Lateral(From);
        if(FMath::Abs(AzureDragonSwingLateral)>20.f)AzureDragonClipSide.Add(CurrentClip,AzureDragonSwingLateral<0.f?int8(1):int8(-1));
    }
    Trace.bIgnoreFriendlyUnits=SwingAzureDragonReachMultiplier>1.f;
    auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,From,To,AzureDragonRange(SwingReach),HitActors,Trace);
    // Blade motion was authored against the shared 180 cm base reach. Extend
    // its contact path with base tuning as well as the distance cap; retain
    // the existing sweep width and independent counterweight contact.
    const float BaseReachScale=bPommelAttack?1.f:Reach/180.f;
    const float TipExtension=SwingRangeMultiplier*SwingAzureDragonReachMultiplier*BaseReachScale;
    float ClawNear=0.f,ClawFar=0.f;
    if(AzureDragonClawSwing()&&AzureDragonClawBand(To.Origin,ClawNear,ClawFar))
    {
        // Azure Dragon (V10.11): the blade line runs from the player out to the claws' farthest talon
        // point, swept along the sword's own path. Its pitch stays near level so a long stroke does not
        // dive into the floor; walls still stop it and single-target strokes keep the nearest hit.
        // V10.12: only the distance band that actually holds targets is swept (none = no sweep).
        const auto ClawLine=[&](FRuneSwordBladeSample S)
        {
            FRotator Direction=(S.Tip-S.Origin).GetSafeNormal(SMALL_NUMBER,S.Forward).Rotation();
            Direction.Pitch=FMath::Clamp(FRotator::NormalizeAxis(Direction.Pitch),AzureDragonReach::MinPitch,AzureDragonReach::MaxPitch);
            S.Base=S.Origin+Direction.Vector()*ClawNear;S.Tip=S.Origin+Direction.Vector()*ClawFar;
            return S;
        };
        FRuneSwordTraceSettings ClawTrace=Trace;
        ClawTrace.bIgnoreFriendlyUnits=true;
        ClawTrace.Radius=FMath::Max(Trace.Radius,AzureDragonReach::TraceRadiusCM);
        auto ClawHits=RuneSwordCombat::Query(GetWorld(),Pawn,ClawLine(From),ClawLine(To),AzureDragonReach::ClawReachCM,HitActors,ClawTrace);
        // Report the eye as the origin: the lane start can be metres out, which the server's hit
        // validation rejects as origin drift.
        for(FHitResult& Hit:ClawHits){Hit.TraceStart=To.Origin;Hit.TraceEnd=Hit.ImpactPoint;}
        Hits.Append(ClawHits);
    }
    else if(TipExtension>1.f||(bUppercut&&UppercutReachGrowth>1.f))
    {
        // Extend the tip's distance from the stable eye, retaining the hilt.
        // Keep the original blade pass as well so close contacts are not lost
        // when the expanded segment changes its angle around the hilt.
        auto ExtendedFrom=From,ExtendedTo=To;
        ExtendedFrom.Tip=From.Origin+(From.Tip-From.Origin)*TipExtension;
        ExtendedTo.Tip=To.Origin+(To.Tip-To.Origin)*TipExtension;
        if(bUppercut)
        {
            // Level growth extends the forward sweep, not its width or height.
            const double FromDepth=FMath::Max(0.,FVector::DotProduct(ExtendedFrom.Tip-From.Origin,From.Forward));
            const double ToDepth=FMath::Max(0.,FVector::DotProduct(ExtendedTo.Tip-To.Origin,To.Forward));
            ExtendedFrom.Tip+=From.Forward*FromDepth*(UppercutReachGrowth-1.f);
            ExtendedTo.Tip+=To.Forward*ToDepth*(UppercutReachGrowth-1.f);
        }
        Hits.Append(RuneSwordCombat::Query(GetWorld(),Pawn,ExtendedFrom,ExtendedTo,AzureDragonRange(SwingReach),HitActors,Trace));
    }
    if((bThrustAttack || bPommelAttack || bUppercut) && Hits.Num()>1)
    {
        Hits.Sort([&](const FHitResult& A,const FHitResult& B)
        {
            return FVector::DotProduct(A.ImpactPoint-To.Origin,To.Forward)<
                FVector::DotProduct(B.ImpactPoint-To.Origin,To.Forward);
        });
        Hits.SetNum(1);
    }
    const FVector Direction=((To.Base+To.Tip)-(From.Base+From.Tip)).GetSafeNormal(SMALL_NUMBER,To.Forward);
    ApplySwingHits(Hits,Direction);
}

void URuneSwordComponent::ApplySwingHits(const TArray<FHitResult>& Hits,const FVector& Direction)
{
    auto* Pawn=Character.Get();
    for(const FHitResult& Hit:Hits)
    {
            AActor* Target=Hit.GetActor();
            if(!IsValid(Target) || HitActors.Contains(Target))continue;
            if(bDashAttack)if(const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&Combat->IsDead())continue;
            HitActors.Add(Target);
            auto HitSkills=SwingSkills;
            if(HighlandRidgeThrust::IsRelease(CurrentClip))
                HitSkills.ArmorPenetration=HighlandRidgeThrust::AddPenetration(HitSkills.ArmorPenetration,HitSkills.AttackMeta);
            if(SwingTrainingHits==1)if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())HitSkills.ExtraMasteryExperience=Profile->MasteryDefinition(TEXT("swordMastery")).MultiHitExperience;
            auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            const bool AzureEnemyWasAlive=Combat&&!Combat->IsDead();
            const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Target);
            FWeaponDamageResult DamageResult;
            auto ApplyDamage=[&](){return ColdSteelSkills::ApplyHit(Pawn,Hit,SwingDamage,Direction,HitSkills,&DamageResult);};
            // 近战不带伤害类型：用作用域标注命中形式（配重锤=钝器，其余=锐器）。
            const MonsterToughness::FScopedForm FormScope(HitSkills.AttackForm);
            const float Applied=Combat?Combat->ApplyHitWithReactionScale(SwingHitReactionMultiplier,ApplyDamage):ApplyDamage();
            ConfirmOathHit(HitSkills,Applied,Hit.ImpactPoint);
            // The contact cue belongs to the contact, not to the damage number: a
            // blow that kills still has to sound like a hit, and the damage pipeline
            // can report nothing once the victim dies to this very hit.
            const bool bKilled=Combat&&Combat->IsDead();
            if(Eligible&&(Applied>0.f||DamageResult.bKilled))++SwingTrainingHits;
            if(AzureEnemyWasAlive&&(Applied>0.f||bKilled))OnAzureDragonHit();
            // The fourth hit already sounded when its strike was released; every other
            // attack reports at the impact point, including a blow that kills.
            USoundBase* ImpactCue=bPommelAttack?nullptr:HitSound;
            if((Applied>0.f || bKilled) && ImpactCue)
                UGameplayStatics::PlaySoundAtLocation(this,ImpactCue,Hit.ImpactPoint,bOverheadAttack?.95f:(bHeavyAttack?.90f:.65f),
                    bOverheadAttack?.86f:(bHeavyAttack?.85f:(bThrustAttack?1.1f:(bPommelAttack?.9f:1.f))));
            const bool bSweepKilled=CurrentClip==HighlandBreakSweep::Clip && Pawn->HasAuthority() &&
                (DamageResult.bKilled || (AzureEnemyWasAlive && bKilled));
            if((Applied>0.f || (bOverheadAttack && bKilled) || bSweepKilled) && !bImpactFeedbackPlayed)
            {
                bImpactFeedbackPlayed=true;ImpactAge=0.f;
                bThrustImpact=bThrustAttack||bPommelAttack||HighlandRidgeThrust::IsRelease(CurrentClip);
                ImpactDirection=CurrentClip==TEXT("Slash2")?1.f:-1.f;
                ImpactStrength=bOverheadAttack?1.25f:(bHeavyAttack?1.5f:(bPommelAttack?1.75f:1.f));
                if(CurrentClip==HighlandBreakSweep::Clip){ImpactStrength=HighlandBreakSweep::ImpactStrength;SweepHitPause=HighlandBreakSweep::HitPauseSeconds;}
            }
            if(Applied>0 || ((bDashAttack||bUppercut)&&bKilled&&Eligible))
            {
                // 金色符文强化：本挥首次确认命中即缩减全部魔法技能CD，一次挥击只触发一次。
                if(SwingCooldownReduceSeconds>0.f&&!bSwingCooldownReduced)
                {
                    bSwingCooldownReduced=true;
                    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->ReduceRuneSwordHitCooldowns(SwingCooldownReduceSeconds);
                }
                if(bDashAttack&&Eligible){++DashHits;if(bKilled)++DashKills;}
                // 上挑/升龙已在权威命中入口击飞，不再追加普通推退或覆盖腾空反应。
                if(Combat&&(!(bUppercut||IsRisingDragonFinisher()||CurrentClip==HighlandBreakSweep::Clip)||!Combat->CanReceiveLaunchOrKnockdown()))
                {
                    const FVector Away=(Target->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
                    const bool bLaunched=bHeavyAttack && !bQuickCombatStrike && !bDashAttack &&
                        Combat->ReceiveKnockdown(Pawn,Away*420.f+FVector(0,0,280.f),.75f);
                    if(!bLaunched)Combat->ReceiveMeleeKnockback(Pawn,bQuickCombatStrike?QuickCombatKnockbackCM:SwingKnockbackCM);
                }
                // 快速进战击杀修炼：可修炼目标被本次打击直接击杀，挥击结束统一提交。
                if(bQuickCombatStrike&&Eligible&&bKilled)QuickCombatKillPending=true;
                if(Combat&&!Combat->IsDead())
                {
                    // 双通道：配重锤快速近战走凝碧星核，其余剑刃攻击走导魔符文。
                    const float Vulnerability=bQuickCombatStrike?0.f:SwingRuneVulnerability;
                    const float VulnerabilitySeconds=SwingRuneVulnerabilitySeconds;
                    if(Vulnerability>0)
                        if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddRuneMagicVulnerability(Vulnerability,VulnerabilitySeconds);
                }
                if(bHeavyTrainingPending&&Eligible){++HeavyTrainingHits;if(!IsValid(Target)||Combat->IsDead())++HeavyTrainingKills;}
                Pawn->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult);ColdSteelCombat::OnHit(Target,Pawn,SwingPoison);
            }
    }
}

