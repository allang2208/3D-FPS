#include "ProductionToolComponent.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/BeiweiSwordTrailComponent.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/FrostSwordRunes.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Skills/LightningHasteSpeed.h"
#include "WarhammerCombat.h"
#include "WarhammerAudioPaths.h"
#include "WarhammerQuickCombatMotion.h"
#include "WarhammerConicalThrustMotion.h"
#include "ConicalHammerSeat.h"
#include "../Skills/LeapStrikeMotion.h"
#include "../Skills/MeteorAssets.h"
#include "WarhammerGuardMotion.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "ProductionBluntCombo.h"
#include "WarhammerUppercutMotion.h"
#include "WarhammerHeavyMotion.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerZhenTing.h"
#include "ThunderHammerStaticField.h"
#include "ThunderHammerCoil.h"
#include "ThunderHammerPommel.h"
#include "ThunderHammerThrown.h"
#include "ThunderHammerRecallAudio.h"
#include "Components/LineBatchComponent.h"
#include "Components/DecalComponent.h"
#include "../Skills/FPSMagicPreview.h"
#include "RuneboundHammerTuning.h"
#include "ProductionToolMeshComponent.h"
#include "WarhammerHeadMarker.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelGenericMelee.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "ProductionToolAppearance.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "ProductionPickaxeImpactMotion.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/WeaponGripProfile.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "ProductionHarvestSubsystem.h"
#include "ProductionTreeHealth.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "HAL/IConsoleManager.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"
#include "Components/AudioComponent.h"

#include "ProductionToolEquipmentPrivate.h"
using namespace ProductionToolEquipmentPrivate;

namespace ProductionToolEquipmentPrivate
{
    const FSoftObjectPath WarhammerOrdinarySwingSoundPath(TEXT("/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing.S_Warhammer_NormalSwing"));
}

namespace
{
    // The uppercut recording builds for about 250 ms before its strong whoosh.
    // Charged hammer release is only 75 ms to contact, so skip that lead-in
    // for heavy attacks without changing the uppercut's own playback.
    // The shovel digs where the crosshair points; the heightfield keeps its 20 cm
    // layer rule, so one swing is one whole layer instead of a melee poke.
    // The shovel is an aiming tool, not a melee reach: without this it could only hit
    // ground inside 3.2 m, i.e. straight down at the player's feet.
    static TAutoConsoleVariable<float> ToolDigReach(
        TEXT("fps.Tool.DigReach"), 600.f,
        TEXT("Shovel aim trace length in cm. The multiplayer authority clamps its own trace to 600; the client default matches so a visible dig is never rejected by the server."));
}

UProductionToolComponent::UProductionToolComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UProductionToolComponent::BeginPlay()
{
    Super::BeginPlay();LoadEnchantmentAnchors();InitializeLocalTool();
}
bool UProductionToolComponent::CanPresent() const
{
    auto* Pawn=Character.Get();
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return PC && Pawn->IsLocallyControlled() && !Pawn->IsTraversing() && (!Health || !Health->IsDead())
        && (!Building || !Building->IsBuilding() || Building->IsPanelOpen());
}

bool UProductionToolComponent::CanUse(bool bContinuing) const
{
    const auto* PC=Character.IsValid()?Cast<APlayerController>(Character->GetController()):nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return CanPresent() && (bContinuing||!IsThunderRecallLocked()) && !(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC)) && (!Building || !Building->IsBuilding())
        &&(!IsThunderHammerAway()||UsesThunderThrowHeavy());
}

void UProductionToolComponent::PlayPojunSwing(float Volume,float Pitch) const
{
    if(auto* Layer=Cast<USoundBase>(FSoftObjectPath(PojunGrip::SwordAttackLayer).ResolveObject()))
        UGameplayStatics::PlaySound2D(this,Layer,1.f,1.f);
    if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,Volume,Pitch);
}

void UProductionToolComponent::BeginUse()
{
    if(IsPojunChainOccupied()||IsQuickCombatActive())return;
    if(IsLeapStrikeActive())return;
    if(IsThunderHammerAway()||ThunderCatchAge>=0.f||ThunderCallReleaseAge>=0.f)return;
    if(Character.IsValid()&&Character->RuneSword&&Character->RuneSword->IsToolGuardRequested())return;
    if(bBluntUppercut&&PojunAttack==PojunGrip::EAttack::Tengyun&&BluntUppercutTime>=WarhammerUppercutMotion::StrikeFinish)
        bQueuedBluntAttack=true;
    if(bBluntCharging||bBluntReturningCharge||bBluntWhirlwind||bBluntUppercut)return;
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction()){bQueuedBluntAttack=false;return;}
    if (!IsEquipped() || !CanUse(bBluntReleaseCharge)) return;
    if(Elapsed>=0.f)
    {
        if(Kind==TEXT("warhammer")&&Elapsed>=RealContactSeconds()&&!bQueuedBluntAttack)
        {
            bQueuedBluntAttack=true;
        }
        return;
    }
    if (!HasReadyPresentation()) { Feedback=TEXT("正在加载工具…"); FeedbackSeconds=1.f; return; }
    if(EquipElapsed>=0)return;
    if(!bBluntReleaseCharge)bBluntHeavy=bBluntSprintAttack;
    if(Kind==TEXT("warhammer"))
    {
        if(GetWorld()->GetTimeSeconds()-LastBluntEnd>ProductionBluntCombo::ResetSeconds)NextBluntStage=0;
        BluntStage=bBluntSprintAttack?2:NextBluntStage;
    }
    AxeStrike={};
    uint32 GenericReceipt=0;
    ThunderMagicSnapshot=-1.f;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        if(const auto* Item=Profile->ActiveProductionTool())
        {
            // 改造数值每次挥动重新求值：属性、配件与附魔变化都不能沿用上一次的快照。
            ApplyToolStats(Item,Profile);
            if(Kind!=TEXT("warhammer")&&GetNetMode()!=NM_Standalone)
            {
                auto* Net=Character->GetPlayerState<AColdSteelPlayerState>();
                if(!Net)return;
                GenericReceipt=Net->RequestGenericMeleeStart(Character.Get(),Item->InstanceId,ColdSteelGenericMelee::Tool,0);
                if(!GenericReceipt)return;
            }
            const bool Zhufeng=bBluntSprintAttack&&PojunGrip::Attack(*Item,false,true,2)==PojunGrip::EAttack::Zhufeng;
            const double AttackCost=Zhufeng?Profile->DashAttackStats().StaminaCost:Kind==TEXT("warhammer")&&bBluntHeavy&&!bBluntSprintAttack?
                ToolStats.HeavyReleaseStaminaCost:ToolStats.StaminaCost;
            if(GetNetMode()==NM_Standalone&&!Profile->SpendStamina(float(FMath::Max(0.,AttackCost))))
            {Feedback=TEXT("体力不足，稍作休息再采集");FeedbackSeconds=1.5f;return;}
            if(UsesTwoHandMotion()||Kind==TEXT("shovel"))
            {
                // Capture after the stamina transaction, which can replace inventory data.
                const auto* AttackItem=Profile->ActiveProductionTool();
                AxeStrike=ColdSteelSkills::Snapshot(Character.Get(),AttackItem);
                AxeStrike.GenericMeleeSerial=GenericReceipt;
                AxeStrike.bMelee=true;
                AxeStrike.DamagePanel=Kind==TEXT("warhammer")?
                    WarhammerCombat::Damage(ToolStats.Damage,Profile,bBluntSprintAttack,bBluntHeavy,BluntHeavyMultiplier,BluntStage,ToolStats.PofengFinisherMultiplier):ToolStats.Damage;
                AxeStrike.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage);
                if(bBluntHeavy&&!bBluntSprintAttack&&AttackItem&&AttackItem->Definition==ThunderHammer::Definition)
                {
                    ThunderMagicSnapshot=ThunderHammer::LightningMagic(*AttackItem,Profile);
                    // Standalone contacts use this snapshot directly, without
                    // passing through ServerBeginBluntAttack's heavy commit.
                    ThunderHammerZhenTing::Commit(AxeStrike,AttackItem,Character->GetViewRotation().Vector());
                    ThunderHammerStaticField::Commit(AxeStrike,AttackItem);
                    ThunderHammerCoil::Commit(AxeStrike,AttackItem,Profile);
                }
                AxeStrike.CriticalChance=float(FMath::Clamp(double(AxeStrike.CriticalChance)+ToolStats.CriticalChanceAdd,0.,100.));
                // Listen hosts also enter the authoritative RPC below. Only
                // standalone consumes procs here, after all item reads finish.
                if(GetNetMode()==NM_Standalone&&bBluntHeavy&&!bBluntSprintAttack)
                {
                    const auto Committed=AxeStrike;
                    ThunderHammerStaticField::Released(Character.Get(),Committed,bThunderThrowSeat||bThunderCallSeat);
                    ThunderHammerCoil::Released(Character.Get(),Committed,bThunderThrowSeat||bThunderCallSeat);
                }
            }
        }
        else if(GetNetMode()==NM_Standalone&&!Profile->SpendStamina(Profile->StaminaSettings().HarvestCost*Profile->ActionStaminaMultiplier()))
        {Feedback=TEXT("体力不足，稍作休息再采集");FeedbackSeconds=1.5f;return;}
    }
    if(bPojunGrip)
    {
        auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
        const auto Attack=Item?PojunGrip::Attack(*Item,bBluntHeavy,bBluntSprintAttack,BluntStage):PojunGrip::EAttack::Ordinary;
        if(Attack!=PojunGrip::EAttack::Ordinary)
        {
            const bool Sprint=bBluntSprintAttack;
            if(!bBluntReleaseCharge)++BluntAttackId;
            if(GetNetMode()==NM_Standalone||!Character->HasAuthority())StartPojunAttack(Attack,Profile);
            else
            {
                // A listen host resolves the stage in the RPC. Keep an ordinary swing
                // available if the authoritative combo expired before this input.
                Elapsed=0.f;BluntStartClip=0.f;
                bContacted=bHitConfirmed=bSwingSoundPlayed=bQueuedBluntAttack=bBluntFloorTarget=false;
            }
            if(GetNetMode()!=NM_Standalone)ServerBeginBluntAttack(BluntAttackId,bBluntReleaseCharge,Sprint,EquippedId);
            return;
        }
    }
    // Restored ordinary cuts share the original idle endpoints. Buffered
    // continuation does not switch to the rejected V3 arm/link solutions.
    if(Kind==TEXT("warhammer"))SelectBluntMotion();
    else
    {
        Motions.Add(TEXT("ActiveSwing"),Motions.FindRef(TEXT("Swing")));
        Motions.Add(TEXT("ActiveHitRecover"),Motions.FindRef(TEXT("HitRecover")));
    }
    Elapsed=0; bContacted=false; bHitConfirmed=false; bSwingSoundPlayed=false;
    bQueuedBluntAttack=false;BluntStartClip=0.f;
    FinalTollActionRate=HasteActionRate;
    FinalTollStrikes=0;FinalTollHeavySerial=UsesFinalTollHeavy()?AxeStrike.MasteryAttackSerial:0;
    FinalTollCommitUntil=RuneboundClock()+FinalTollHeavy::Duration/FinalTollActionRate+.1;
    if(UsesFinalTollHeavy()){SwingSeconds=FinalTollHeavy::Duration;ContactSeconds=FinalTollHeavy::FirstContact;bBluntFloorTarget=false;}
    if(UsesThunderThrowHeavy())
    {
        SwingSeconds=ThunderHammerThrow::Duration;ContactSeconds=ThunderHammerThrow::Release;bBluntFloorTarget=false;
        Character->StopMovementForMeleeSkill();
    }
    else if(bBluntHeavy&&!UsesFinalTollHeavy())
    {
        SwingSeconds=WarhammerHeavy::Duration;ContactSeconds=WarhammerHeavy::Contact;
        BluntSlamRotation=FRotator(0.f,Character->GetControlRotation().Yaw,0.f).Quaternion();
        BluntSlamEye=Character->GetMeleeAimTransform().GetLocation();
        BluntSprintAnchorLocation=Character->GetActorLocation();
        BluntSprintDirection=BluntSlamRotation.GetForwardVector().GetSafeNormal2D();
        bBluntFloorTarget=false;
        FHitResult Floor;bBluntFloorTarget=FindBluntGround(Floor);
        if(bBluntFloorTarget){BluntFloorPoint=Floor.ImpactPoint;BluntFloorNormal=Floor.ImpactNormal;}
        Character->StopMovementForMeleeSkill();
    }
    if(Kind==TEXT("warhammer")&&GetNetMode()!=NM_Standalone)
    {
        if(!bBluntReleaseCharge)++BluntAttackId;
        ServerBeginBluntAttack(BluntAttackId,bBluntReleaseCharge,bBluntSprintAttack,EquippedId);
    }
    if(Kind==TEXT("warhammer")&&bBluntHeavy&&!bBluntSprintAttack&&Elapsed>=0.f&&bUsesArms&&Character->IsLocallyControlled())
    {
        // Start with the release input, rather than waiting for the next action
        // tick. Mark it consumed so AdvanceActionBeforeCamera cannot replay it.
        bSwingSoundPlayed=true;
        if(bPojunGrip)PlayPojunSwing(.95f,.9f);
        else if(auto* Sound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject()))
            UGameplayStatics::PlaySound2D(this,Sound,.72f,1.f,WarhammerAudioPaths::HeavyStartSeconds);
    }
}

void UProductionToolComponent::SelectBluntMotion()
{
    Motions.Add(TEXT("ActiveSwing"),Motions.FindRef(UsesThunderThrowHeavy()?FName(TEXT("ThunderThrow")):UsesFinalTollHeavy()?FName(TEXT("FinalTollHeavy")):bBluntHeavy?FName(TEXT("HeavyRelease")):ProductionBluntCombo::Swing(BluntStage)));
    Motions.Add(TEXT("ActiveHitRecover"),Motions.FindRef(ProductionBluntCombo::Recovery(BluntStage)));
}

void UProductionToolComponent::FinishUse()
{
    const bool Queued=Kind==TEXT("warhammer")&&bQueuedBluntAttack;
    const bool Chain=Queued&&bBluntChain;const int32 ChainStage=BluntChainStage;const float ChainClip=BluntChainStartClip;
    bBluntChain=false;BluntStartClip=0.f;
    if(Kind==TEXT("warhammer"))
    {
        NextBluntStage=bBluntHeavy||bBluntSprintAttack?0:(BluntStage+1)%3;
        LastBluntEnd=GetWorld()->GetTimeSeconds();
    }
    FinalTollHeavySerial=0;FinalTollStrikes=0;
    Elapsed=-1.f;bContacted=bHitConfirmed=bSwingSoundPlayed=bQueuedBluntAttack=bBluntHeavy=false;bBluntFloorTarget=false;
    bBluntSprintAttack=false;BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    bBluntSprintLungeBlocked=true;
    if(UsesTwoHandMotion())VisualTime=0.f;
    if(Pivot)Pivot->SetRelativeRotation(FRotator::ZeroRotator);
    if(Queued)BeginUse();
    // The chained cut has already shown its early load: continue from there.
    // A refused cut simply blends back to idle from the visible pose.
    if(Chain&&Elapsed>=0.f&&!bBluntHeavy)
    {
        if(BluntStage==ChainStage)BluntStartClip=ChainClip;
        else HandOffBluntPose();
    }
}

void UProductionToolComponent::CancelUse()
{
    if(IsPojunChainOccupied())Character->RuneSword->CancelAction();
    SetLeapAimPreview(false);
    ThunderCallReleaseAge=-1.f;bThunderCallCharging=false;bThunderCallHoldConfirmed=false;ClearThunderCallVisual();FinishThunderCallResources();
    FPSMagicPreview::Clear(ThunderPreview);ThunderCatchAge=-1.f;
    bThunderRecallPending=false;ThunderReachAge=-1.f;
    if(Character.IsValid())
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Character->GetCharacterMovement()))
        {
            Move->CancelHammerSprintMove(Character->HasAuthority()&&!Character->IsLocallyControlled()?BluntServerAttackId:BluntAttackId);
            if(bBluntSprintAttack&&Character->IsLocallyControlled())Move->RestoreMeleeDashMomentum(false);
        }
    if(Character.IsValid()&&Character->RuneSword)Character->RuneSword->CancelToolGuard();
    if(IsQuickCombatActive())Character->QuickCombatPistol->Cancel();
    if(Kind==TEXT("warhammer")&&(Elapsed>=0.f||NextBluntStage!=0||bBluntCharging||bBluntWhirlwind||bBluntUppercut)&&GetNetMode()==NM_Client)
        ServerCancelBluntAttack(BluntAttackId);
    FinishBluntWhirlwind();
    FinishBluntUppercut();
    FinishLeapStrike();
    if(GetWorld()){GetWorld()->GetTimerManager().ClearTimer(BluntContactTimer);GetWorld()->GetTimerManager().ClearTimer(FinalTollContactTimer);}
    FinalTollHeavySerial=0;FinalTollStrikes=0;
    if((UsesTwoHandMotion()) && (Elapsed>=0.f || EquipElapsed>=0.f))VisualTime=0.f;
    Elapsed=-1; EquipElapsed=-1; CancelInspect(); bContacted=false; bHitConfirmed=false; bSwingSoundPlayed=false;
    BluntStage=NextBluntStage=BluntServerNextStage=0;LastBluntEnd=-100.;bQueuedBluntAttack=false;
    bBluntChain=false;BluntStartClip=0.f;
    BluntServerComboExpires=0.;BluntServerGroundSlamUntil=0.;
    BluntServerReadyAt=0.;
    bBluntCharging=bBluntHeavy=bBluntReleaseCharge=bBluntServerCharging=bBluntFloorTarget=false;
    bBluntReturningCharge=false;
    bBluntSprintAttack=false;BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;BluntSprintInstance.Reset();
    bBluntSprintLungeBlocked=true;bBluntServerSprintAttack=false;BluntServerSprintContactAt=0.;
    if (Pivot) Pivot->SetRelativeRotation(FRotator::ZeroRotator);
}

void UProductionToolComponent::ShowFeedback(const FString& Message)
{
    Feedback=Message; FeedbackSeconds=4.f;
}

bool UProductionToolComponent::TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const
{
    if(Kind==TEXT("warhammer"))return false;
    if(UsesTwoHandMotion())
        return TraceAxeContact(Resource,Hit,Reason) && !Resource.Id.IsEmpty();
    if (!Camera || !Character.IsValid()) return false;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionTool),false,Character.Get());
    const FTransform Aim=Camera->GetComponentTransform();
    const FVector Start=Aim.GetLocation();
    const float Length=Kind==TEXT("shovel")?ToolDigReach.GetValueOnGameThread():Reach;
    if (!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Aim.GetRotation().GetForwardVector()*Length,ECC_Visibility,Q))
    { Reason=TEXT("靠近树干、独立岩块或干燥地面（3.2 米内）"); return false; }
    if (FProductionResource::ResolveHit(GetWorld(),Hit,Resource,Reason)) return true;
    if (Reason.IsEmpty()) Reason=TEXT("此物体不可采集，前往温带丘陵寻找资源");
    return false;
}

bool UProductionToolComponent::ResolveContact()
{
    // Multiplayer blunt contact is traced and settled once by its server timer.
    if(Kind==TEXT("warhammer")&&GetNetMode()!=NM_Standalone)
    {
        if(UsesThunderThrowHeavy()&&!GetOwner()->HasAuthority())ThunderAwayInstance=EquippedId;
        return false;
    }
    if(UsesThunderThrowHeavy())return LaunchThunderHammer(AxeStrike,ThunderMagicSnapshot);
    if(Kind==TEXT("warhammer"))
    {
        if(bBluntHeavy)return BeginBluntShockwave(bBluntSprintAttack,bBluntSprintAttack?0.f:BluntHeavyStunSeconds,ThunderMagicSnapshot);
        return ResolveBluntContact(0.f,BluntStage==2&&ToolStats.PofengFinisherMultiplier.IsSet());
    }
    FProductionResource Target; FHitResult Hit; FString Reason;
    const bool bCombatTool=UsesTwoHandMotion();
    const bool Found=bCombatTool?TraceAxeContact(Target,Hit,Reason):TraceResource(Target,Hit,Reason);
    // The shovel's trace still returns its blocking hit even when it is not soil.
    if(UWardBreakableGlass::BreakHit(Hit,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal()))
    {Feedback=TEXT("玻璃已击碎");FeedbackSeconds=1.2f;return true;}
    if (!Found)
    {
        // The shovel is an equippable weapon since 2026-10-17: its self-defense
        // swing resolves against enemies exactly like the axe/pickaxe, using the
        // same combat trace (aim transform, combat reach) - never the dig trace.
        if(Kind==TEXT("shovel"))
        {
            FProductionResource Unused;FHitResult CombatHit;
            if(TraceShovelEnemyContact(CombatHit))return ResolveShovelEnemyContact(CombatHit);
        }
        Feedback=Reason; FeedbackSeconds=2; return false;
    }
    if(bCombatTool && Target.Id.IsEmpty())return ResolveAxeEnemyContact(Hit);
    if (Kind!=Target.RequiredTool)
    {
        Feedback=Target.RequiredTool==TEXT("axe")?TEXT("砍树需要伐木斧：在背包右键装备到主手，再用 G / 滚轮切换"):
            Target.RequiredTool==TEXT("pickaxe")?TEXT("开采岩块需要矿镐：在背包右键装备到主手，再用滚轮切换"):TEXT("挖掘表土需要铁铲：在背包右键装备到主手，再用滚轮切换");
        FeedbackSeconds=2; return false;
    }
    if(GetNetMode()!=NM_Standalone)
    {
        FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Harvest;R.Eye=Hit.TraceStart;R.Direction=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal();
        if(auto* PS=Character->GetPlayerState<AColdSteelPlayerState>())return PS->RequestInventoryAction(R);return false;
    }
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    bool Depleted=false;
    Target.Direction=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal();
    if(Target.Layer==0 && !Target.bStump)
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->PrepareFall(Target);
    if (!Profile->CommitHarvestStrike(Target,Depleted)) { Feedback=Profile->ResultMessage(); FeedbackSeconds=3; return false; }
    Feedback=Profile->ResultMessage(); FeedbackSeconds=2;
    if (HitSound) UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.65f);
    if (ImpactDust&&(!Depleted||Target.Layer==2)) UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactDust,Hit.ImpactPoint,Hit.ImpactNormal.Rotation(),FVector(.25f),true,EPSCPoolMethod::AutoRelease);
    Target.ApplySuccessfulStrike(Hit,Depleted);
    if (Depleted && Target.Layer==2)
    {
        // The world just removed one 20 cm layer; say so instead of only "collected".
        Feedback=TEXT("表土挖低 20 cm（继续左键下挖，右键回填）");
        FeedbackSeconds=3.f;
    }
    return true;
}

void UProductionToolComponent::BeginRefill()
{
    if(!IsEquipped()||IsBusy())return;
    if(Kind==TEXT("warhammer"))return;
    if(Kind!=TEXT("shovel")){ShowFeedback(TEXT("回填地面需要铁铲：在背包右键装备到主手"));return;}
    if(!Camera||!Character.IsValid())return;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionTool),false,Character.Get());
    const FVector Start=Camera->GetComponentLocation();
    FHitResult Hit;
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Camera->GetForwardVector()*ToolDigReach.GetValueOnGameThread(),ECC_Visibility,Q))
    {ShowFeedback(TEXT("瞄准地面再回填"));return;}
    if(GetNetMode()!=NM_Standalone)
    {FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::SoilRefill;R.Eye=Start;R.Direction=Camera->GetForwardVector();
     if(auto* PS=Character->GetPlayerState<AColdSteelPlayerState>())PS->RequestInventoryAction(R);return;}
    FString Message;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->ApplySoilRefill(Hit.ImpactPoint,Message))break;
    if(Message.IsEmpty())Message=TEXT("这里不是可回填的地形");
    ShowFeedback(Message);
}

void UProductionToolComponent::AdvanceActionBeforeCamera(float Delta)
{
    // The owner calls this once, before its camera and before our presentation
    // tick. Contact audio, camera impulses and sampled arms see the same age.
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!Pivot)return;
    if(!IsEquipped()||!CanPresent()){CancelUse();return;}
    if(IsWarhammerEquipped()&&Character->RuneSword)
    {
        Character->RuneSword->AdvanceToolGuard(Delta);
        if(IsGuardActive())return;
    }
    if(!CanUse(true))
    {
        // Awaiting/receiving a recalled hammer is an active hand presentation.
        if(IsThunderHammerAway()){if(Elapsed>=0.f)FinishUse();return;}
        CancelUse();return;
    }
    if(IsPojunChainOccupied())return;
    if(IsQuickCombatActive()){Character->QuickCombatPistol->AdvanceAction(Delta);return;}
    if(bLeapStrike){TickLeapStrike(Delta);return;}
    if(bBluntWhirlwind){TickBluntWhirlwind(Delta);return;}
    if(bBluntUppercut){TickBluntUppercut(Delta);return;}
    AdvanceBluntSprintReadiness(Delta);
    AdvanceBluntCharge(Delta);
    if(ThunderCallReleaseAge>=0.f)
    {
        ThunderCallReleaseAge+=Delta*HasteActionRate;
        if(ThunderCallReleaseAge>=ThunderHammerCall::ReleaseSeconds){ThunderCallReleaseAge=-1.f;VisualTime=0.f;}
        return;
    }
    if(Elapsed>=0.f&&UsesFinalTollHeavy()){AdvanceFinalTollHeavy(Delta);return;}
    if (Elapsed>=0)
    {
        const float PreviousElapsed=Elapsed;
        Elapsed+=Delta;
        if(bBluntSprintAttack)AdvanceBluntSprintLunge(PreviousElapsed,Elapsed);
        // 挥砍速度改造只压缩真实时钟：作者节奏与镜头关键帧按 RateScale 换算，
        // RateScale=1 时逐帧等于改造前。
        const float Contact=RealContactSeconds(), Swing=RealSwingSeconds();
        // The overhead pickaxe starts accelerating 100 ms before contact;
        // its whoosh belongs to that downstroke, after the raised hold.
        // Ordinary hammer air swishes follow each cut's downswing clock.
        const float WhooshTime=bBluntHeavy?BluntLiftSeconds():Kind==TEXT("warhammer")?
            ProductionBluntCombo::RealForWindupClip(ProductionBluntCombo::WhooshClip(BluntStage),Contact,ContactSeconds,RateScale,BluntStage,BluntStartClip):
            (Kind==TEXT("axe")?AxeMotion.SwingSoundSeconds:
            (Kind==TEXT("shovel")?FMath::Max(0.f,ContactSeconds-.14f):
            (UsesPickaxeMotion()?FMath::Max(0.f,ContactSeconds-.10f):ContactSeconds*.65f)))/RateScale;
        if(bUsesArms && !bSwingSoundPlayed && Elapsed>=WhooshTime)
        {
            bSwingSoundPlayed=true;
            const bool OrdinaryHammer=Kind==TEXT("warhammer")&&!bBluntHeavy;
            const bool HammerRelease=Kind==TEXT("warhammer")&&bBluntHeavy&&!bBluntSprintAttack;
            // Restore the ordinary air swish; only charged heavy release uses
            // the uppercut recording and its shortened lead-in. Both assets
            // are retained by the equipment load handle before the strike.
            if(bPojunGrip)PlayPojunSwing(bBluntHeavy?.95f:.72f,bBluntHeavy?.9f:1.f);
            else
            {
                USoundBase* Sound=SwingSound.Get();
                if(OrdinaryHammer)Sound=Cast<USoundBase>(WarhammerOrdinarySwingSoundPath.ResolveObject());
                else if(HammerRelease)Sound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject());
                if(Sound)UGameplayStatics::PlaySound2D(this,Sound,HammerRelease?.72f:.38f,(OrdinaryHammer||HammerRelease)?1.f:Kind==TEXT("axe")?.86f:.76f,
                    HammerRelease?WarhammerAudioPaths::HeavyStartSeconds:0.f);
            }
        }
        // The shovel keeps its original procedural arc. Skeletal tools use the same
        // one-contact clock and resolve against the camera ray at the contact time.
        if(!bUsesArms)
        {
            float Angle;
            if (Elapsed<Contact) Angle=FMath::Lerp(-.45f,.95f,FMath::Square(Elapsed/FMath::Max(1e-3f,Contact)));
            else { const float T=FMath::Clamp((Elapsed-Contact)/FMath::Max(1e-3f,Swing-Contact),0.f,1.f); Angle=FMath::Lerp(.95f,0.f,T*T*(3-2*T)); }
            Pivot->SetRelativeRotation(FRotator(-FMath::RadiansToDegrees(Angle),0,FMath::RadiansToDegrees(Angle*.26f)));
        }
        if (!bContacted && Elapsed>=Contact)
        {
            bContacted=true; bHitConfirmed=ResolveContact();
            // Networked ordinary hammer cuts settle on the server timer; predict
            // the hit locally (presentation only) so the impact is not delayed.
            if(!bHitConfirmed&&Kind==TEXT("warhammer")&&!bBluntHeavy&&GetNetMode()!=NM_Standalone)
                bHitConfirmed=PredictBluntEnemyContact();
            // Start the confirmed impact at zero age, even on a late frame, so
            // a hitch cannot skip the lodged pose and its first camera impulse.
            if(bHitConfirmed && UsesTwoHandMotion()&&!bBluntHeavy)Elapsed=Contact;
        }
        const float End=bBluntHeavy?Swing:bHitConfirmed && Kind==TEXT("axe")?Contact+AxeMotion.HitRecoverSeconds/RateScale:
            bHitConfirmed && Kind==TEXT("warhammer")?Contact+ProductionBluntCombo::HitRecoverSeconds/RateScale:
            bHitConfirmed && UsesPickaxeMotion()?Contact+ProductionPickaxeImpact::HitRecoverSeconds/RateScale:
            bHitConfirmed && Kind==TEXT("shovel")?Contact+.5f/RateScale:Swing;
        AdvanceBluntChain(Delta,End);
        if (Elapsed>=End) FinishUse();
    }
}

void UProductionToolComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    InitializeLocalTool();TickRunebound(Delta);TickAuthorityBluntCharge();TickThunderThrow(Delta);TickThunderCall(Delta);
    if(bLeapAirborne&&!IsLeapControlImmune())SetLeapAirborne(false);
    if(bLeapAimPreview)RefreshLeapAimPreview(Delta);
    if(Character.IsValid()&&Character->HasAuthority()&&!Character->IsLocallyControlled()&&bBluntServerSprintAttack)
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(Now<BluntServerReadyAt)
        {
            if(PojunAttack!=PojunGrip::EAttack::Zhufeng)UpdateBluntSprintAnchor(Now<BluntServerSprintContactAt);
        }
        else bBluntServerSprintAttack=false;
    }
    if(Character.IsValid()&&Character->HasAuthority()&&!Character->IsLocallyControlled())
    {
        if(bLeapStrike)TickLeapStrike(Delta);
        else if(bBluntWhirlwind)TickBluntWhirlwind(Delta);
        else if(bBluntUppercut)TickBluntUppercut(Delta);
        else AdvanceBluntSprintReadiness(Delta);
    }
    if(!Pivot){UpdateRuneboundPresentation(Delta,!RuneboundInstance.IsEmpty());UpdateStormDriveLightning(Delta);return;}
    if(!Character.IsValid()||!Character->IsLocallyControlled())
    {UpdateRuneboundPresentation(Delta,!RuneboundInstance.IsEmpty());UpdateStormDriveLightning(Delta);return;}
    const bool Present=IsEquipped() && CanPresent();
    ThunderHammerPommel::UpdateVisual(Character.Get(),LeiXiCoreMaterial.Get(),bLeiXiCoreActive);
    const bool Usable=IsEquipped() && CanUse(true);
    const bool Away=IsThunderHammerAway();
    const bool Catching=ThunderCatchAge>=0.f||(Away&&(bThunderRecallPending||(ThrownHammer&&(ThrownHammer->IsReturning()||ThrownHammer->IsCatching()))));
    if (ToolMesh) ToolMesh->SetVisibility(Present && !Away && (!bUsesArms||ToolMesh->GetAttachParent()==Viewmodel) && ToolMesh->GetStaticMesh(),true);
    if (Viewmodel) Viewmodel->SetVisibility(Present && bUsesArms && HasReadyPresentation()&&(!Away||UsesThunderThrowHeavy()||Catching));
    const bool GuardBreakPresentation=Present&&Character->RuneSword&&Character->RuneSword->IsToolGuardBreakActive();
    if (!Usable&&!GuardBreakPresentation&&!Away&&!Catching) CancelUse();
    if(Present && bUsesArms && HasReadyPresentation())UpdateHandPresentation(Delta);
    UpdatePojunRuneTrail(Present);
    TickWarhammerRifts(Delta,Present);
    FeedbackSeconds=FMath::Max(0.f,FeedbackSeconds-Delta);
    HintCountdown-=Delta;
    if (HintCountdown<=0) { HintCountdown=.15f; UpdateHint(); }
    UpdateRuneboundPresentation(Delta,!RuneboundInstance.IsEmpty());
    UpdateStormDriveLightning(Delta);
}

void UProductionToolComponent::UpdateHint()
{
    // 2026-09-28 用户要求：使用采集工具时下方的白色提示字段全部删除——不再创建/显示
    // 提示控件（工具名与操作说明、瞄准详情、挥砍反馈都随之消失；采集结果仍走音效与
    // 画面表现）。保留空函数与 EndPlay 清理，回退时把旧实现搬回来即可。
    if (Prompt) Prompt->SetVisibility(ESlateVisibility::Collapsed);
}

void UProductionToolComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    SetLeapAirborne(false);
    SetLeapAimPreview(false);
    if(LeapAimDecal)LeapAimDecal->DestroyComponent();
    InspectAir.Stop(0.f);
    bThunderCallCharging=false;FinishThunderCallResources();StopThunderCallAudio();
    if(ThunderCallChargeAudio){ThunderCallChargeAudio->DestroyComponent();ThunderCallChargeAudio=nullptr;}
    if(ThunderCallDecal)ThunderCallDecal->DestroyComponent();
    if(ThunderPreview)ThunderPreview->DestroyComponent();
    if(GetOwner()->HasAuthority()&&ThrownHammer)
    {
        ThrownHammer->ReturnToStorage();
    }
    if(PojunRuneTrail){PojunRuneTrail->DestroyComponent();PojunRuneTrail=nullptr;}
    ClearWarhammerRifts(true);
    ClearRuneboundPresentation();
    ClearStormDriveLightning();
    FinishLeapStrike();
    FinishBluntWhirlwind();
    FinishBluntUppercut();
    if(GetWorld()){GetWorld()->GetTimerManager().ClearTimer(BluntContactTimer);GetWorld()->GetTimerManager().ClearTimer(FinalTollContactTimer);}
    if (LoadHandle) { LoadHandle->CancelHandle(); LoadHandle.Reset(); }
    if (Prompt) { Prompt->RemoveFromParent(); Prompt=nullptr; }
    ColdSteelModularSword::Clear(ToolMesh);
    Super::EndPlay(Reason);
}

