#include "BowWeaponComponent.h"
#include "BowStats.h"
#include "BowMountainEchoComponent.h"
#include "BowCadenceComponent.h"
#include "../../Skills/FPSMagicArrowRainComponent.h"
#include "../../Skills/FPSElementalArrowComponent.h"
#include "../../Skills/FPSIlluminationArrowComponent.h"
#include "../../Characters/FPSComponentVisibility.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Combat/RangedAttackQuery.h"
#include "BowArrow.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "BowArmsMeshComponent.h"
#include "BowPartComponent.h"
#include "BowScopeOptics.h"
#include "BowQuickCombatMotion.h"
#include "BowStats.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../Movement/FPSDoorPushComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../WeaponStatEvaluation.h"
#include "../GunsmithSystem.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../UI/ColdSteelPickup.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Sound/SoundBase.h"

#include "BowWeaponPrivate.h"
using namespace BowWeaponPrivate;
bool UBowWeaponComponent::CanPresent(bool bAllowDoorPushPresentation) const
{
    auto* Pawn = Character.Get();
    if (!Pawn || !Pawn->IsLocallyControlled()) return false;
    const auto* PC = Cast<APlayerController>(Pawn->GetController());
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Building = PC ? PC->FindComponentByClass<UVoxelBuildComponent>() : nullptr;
    const auto* Bash = Pawn->QuickCombatPistol.Get();
    const bool bOwnQuickCombat = Stage == EBowStage::QuickCombat && Bash
        && Bash->GetStyle() == EQuickCombatStyle::Bow && Bash->IsOccupyingLeftHand();
    const bool bDoorPushPresentation = bAllowDoorPushPresentation && Pawn->IsDoorPushActive();
    const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
    const bool bCastCarry=Magic&&Magic->IsOccupyingLeftHand();
    const auto* Use=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const bool bConsumeCarry=Use&&(Use->UsesBowSupport()||Use->IsTwoHanded()||Use->IsReturningBow());
    return PC && bPresentationReady && !Pawn->IsTraversing()
        && (!Pawn->IsCastBlockingLeftHandAction() || bOwnQuickCombat || bDoorPushPresentation || bCastCarry || bConsumeCarry)
        && (!Health || !Health->IsDead()) && (!Building || !Building->IsBuilding() || Building->IsPanelOpen());
}

bool UBowWeaponComponent::CanUse(bool bAllowDoorPushPresentation, bool bContinuing) const
{
    const auto* PC = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr;
    const auto* Building = PC ? PC->FindComponentByClass<UVoxelBuildComponent>() : nullptr;
    const auto* Magic=GetOwner()->FindComponentByClass<UFPSFireballComponent>();
    const auto* Use=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    return CastTransferAlpha<=0.f&&!(Magic&&Magic->IsOccupyingLeftHand())&&!(Use&&(Use->IsActive()||Use->IsReturningBow()))&&CanPresent(bAllowDoorPushPresentation) && !(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC))
        && (!Building || !Building->IsBuilding());
}

float UBowWeaponComponent::DrawFraction() const
{
    if (Stage == EBowStage::Holding) return 1.f;
    if (Stage != EBowStage::Drawing || Elapsed < 0.f) return 0.f;
    const float T = FMath::Clamp(Elapsed / FMath::Max(.0001f, DrawSeconds), 0.f, 1.f);
    if (DrawCurve.Num() < 2) return T;
    const float Sample = T * (DrawCurve.Num() - 1);
    const int32 I = FMath::Min(FMath::FloorToInt(Sample), DrawCurve.Num() - 2);
    return FMath::Lerp(DrawCurve[I], DrawCurve[I + 1], Sample - I);
}

float UBowWeaponComponent::DrawElapsed() const
{
    return Stage == EBowStage::Holding ? DrawSeconds + Elapsed
        : Stage == EBowStage::Drawing ? Elapsed : 0.f;
}

bool UBowWeaponComponent::HasPerfectDrawSpeedBonus() const
{
    return bPerfectSpeedPending;
}

void UBowWeaponComponent::ConfirmNetworkDraw(const FString& Weapon,FGuid DrawId,float FullDrawSeconds,bool PerfectSpeed)
{
    if(Weapon!=InstanceId||DrawId!=ActiveDrawId||!IsDrawing()||!FMath::IsFinite(FullDrawSeconds)||FullDrawSeconds<=0.f)return;
    // Keep elapsed seconds, not the predicted fraction. The authority fixes the
    // action duration once, including a cadence stack expiring during transit.
    const float Age=DrawElapsed();DrawSeconds=FullDrawSeconds;bPerfectSpeedPending=PerfectSpeed;
    Stage=Age>=DrawSeconds?EBowStage::Holding:EBowStage::Drawing;
    Elapsed=Stage==EBowStage::Holding?Age-DrawSeconds:Age;
    HoldElapsed=Stage==EBowStage::Holding?Elapsed:0.f;
    if(const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        PiercingDrawStats=HeartPiercingArrow::ForModel(Profile,INDEX_NONE,DrawSeconds);
}
void UBowWeaponComponent::ConfirmNetworkRelease(const FString& Weapon,FGuid DrawId,bool Accepted,bool Perfect,bool Piercing)
{
    if(Weapon!=InstanceId||DrawId!=LastReleasedDrawId)return;
    bPerfectSpeedPending=Perfect;
    if(!IsDrawing()){bLastPerfectRelease=Accepted&&Perfect;bLastPiercingRelease=Accepted&&Piercing;}
}

bool UBowWeaponComponent::GetDrawRhythm(FBowDrawRhythm& Out) const
{
    if (!IsEquipped()) return false;
    Out = FBowDrawRhythm();
    Out.FullDrawSeconds = DrawSeconds;
    Out.PerfectWindowSeconds=PerfectWindowSeconds;
    Out.bPiercingAvailable=PiercingDrawStats.bLearned;
    Out.PiercingSeconds=PiercingDrawStats.ChargeSeconds;
    if(const auto* Rain=GetOwner()->FindComponentByClass<UFPSMagicArrowRainComponent>();Rain&&Rain->IsPrepared()&&IsDrawing())
    {
        Out.bMagicArrowRain=true;Out.bMagicRainValid=Rain->PreviewValid();
        Out.bPiercingAvailable=false;Out.Elapsed=DrawElapsed();return true;
    }
    const auto* Cadence=GetOwner()->FindComponentByClass<UBowCadenceComponent>();
    Out.bAutomaticRhythm=Cadence&&Cadence->HasAutomaticRhythmFor(InstanceId);
    if (IsDrawing())
    {
        Out.Elapsed = DrawElapsed();
        Out.bSpeedBoosted = HasPerfectDrawSpeedBonus();
        Out.bPerfect = Out.bAutomaticRhythm?DrawFraction()>=ColdSteelBow::MinimumFireDrawFraction:
            DrawFraction()>=1.f&&ColdSteelBow::IsPerfectRelease(Out.Elapsed,DrawSeconds,PerfectWindowSeconds);
        Out.bPiercingReady=IsDrawing()&&HeartPiercingArrow::IsCharged(PiercingDrawStats,Out.Elapsed,DrawFraction());
        return true;
    }
    if ((Stage == EBowStage::Release || Stage == EBowStage::Recover)
        && (bLastPerfectRelease || bLastPiercingRelease)
        && ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < FBowDrawRhythm::ReleaseFeedbackSeconds)
    {
        Out.Elapsed = LastReleaseElapsed;
        Out.bReleased = true;
        Out.bPerfect = bLastPerfectRelease;
        Out.bPiercingReady = bLastPiercingRelease;
        Out.ReleaseAge = ReleaseFeedbackAge;
        Out.bSpeedBoosted = HasPerfectDrawSpeedBonus();
        Out.Opacity = 1.f - ReleaseFeedbackAge / FBowDrawRhythm::ReleaseFeedbackSeconds;
        return true;
    }
    return false;
}

void UBowWeaponComponent::EndNetworkDraw()
{
    if (!bNetworkDrawActive) return;
    bNetworkDrawActive = false;
    if (auto* Pawn = Character.Get())
        if (auto* PS = Pawn->GetPlayerState<AColdSteelPlayerState>())
            PS->ServerSetBowDraw(Pawn, InstanceId, false, 0.f,ActiveDrawId);
}

int32 UBowWeaponComponent::ArrowsInPouch() const
{
    auto* World = GetWorld();
    auto* GameInstance = World ? World->GetGameInstance() : nullptr;
    const auto* Profile = GameInstance ? GameInstance->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!Profile || ArrowId.IsEmpty()) return 0;
    return static_cast<int32>(FMath::Clamp<int64>(Profile->PouchCount(ArrowId), 0, MAX_int32));
}

bool UBowWeaponComponent::ConsumeArrowFromPouch(FString& Reason, bool& bSpentOwnedArrow)
{
    bSpentOwnedArrow = false;
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile) return false;
    auto* Pawn = Character.Get();
    // 开发面板的"无限备弹"按弹种生效：arrow_wood 在 ammo_types.json 里允许无限，
    // 于是发射不扣箭袋，与枪械无限备弹同一口径。
    if (Pawn && Pawn->HasInfiniteReserveAmmoFor(ArrowId)) return true;
    if (Profile->PouchCount(ArrowId) <= 0)
    {
        Reason = FString::Printf(TEXT("箭袋里没有%s"), *Profile->AmmoLabel(ArrowId));
        return false;
    }
    if (!Profile->SpendAmmo(ArrowId, 1))
    {
        Reason = TEXT("箭支扣除未保存，未发射");
        return false;
    }
    bSpentOwnedArrow = true;
    return true;
}

void UBowWeaponComponent::StopDrawAudio()
{
    if (IsValid(DrawAudio)) DrawAudio->FadeOut(.018f, 0.f);
    DrawAudio = nullptr;
}

void UBowWeaponComponent::StopHandlingAudio()
{
    if (IsValid(HandlingAudio)) HandlingAudio->Stop();
    HandlingAudio = nullptr;
}

void UBowWeaponComponent::PlayHandlingSound(USoundBase* Sound, float Volume, float FitSeconds)
{
    StopHandlingAudio();
    if (!Sound) return;
    // Only speed up a short handling sample when the quick-entry window is
    // smaller. R nocking retains the original texture and pitch.
    const float Pitch = FitSeconds > 0.f ? FMath::Max(1.f, Sound->GetDuration() / FitSeconds) : 1.f;
    HandlingAudio = UGameplayStatics::SpawnSound2D(this, Sound, Volume, Pitch);
}

void UBowWeaponComponent::SetStage(EBowStage Next, float Seconds, float StartSeconds)
{
    // Capture before leaving Drawing/Holding, while the draw and hold clocks still describe the hands.
    if (Next == EBowStage::Release || Next == EBowStage::LetDown)
        EndDrawMotionWeight = DrawMotionWeight();
    StopDrawAudio();
    if (Next == EBowStage::Drawing)
    {
        // Predict immediately; the matching authority draw receipt fixes this
        // action's duration, and the shot receipt reconciles perfect success.
        const bool bSpeedBonus = HasPerfectDrawSpeedBonus();
        if (const auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        {
            if (const auto* Item = Profile->ActiveBow())
            {
                const auto Stats=ColdSteelBow::Evaluate(*Item,Profile);
                DrawSeconds=float(Stats.Draw)*ColdSteelBow::DrawSpeedScale(bSpeedBonus);
                PerfectWindowSeconds=float(Stats.RhythmWindow);
            }
            PiercingDrawStats=HeartPiercingArrow::ForModel(Profile,INDEX_NONE,DrawSeconds);
        }
        auto* Rain=GetOwner()->FindComponentByClass<UFPSMagicArrowRainComponent>();
        const bool MagicRain=Rain&&Rain->IsPrepared();
        if(MagicRain){DrawSeconds=Rain->ChargeSeconds();Seconds=DrawSeconds;PiercingDrawStats={};Rain->DrawStarted(StartSeconds);}
        bLastPerfectRelease = bLastPiercingRelease = false;
        if (auto* Pawn = Character.Get(); !MagicRain && Pawn && Pawn->GetNetMode() == NM_Client)
            if (auto* PS = Pawn->GetPlayerState<AColdSteelPlayerState>())
            {
                ActiveDrawId=FGuid::NewGuid();
                PS->ServerSetBowDraw(Pawn, InstanceId, true, FMath::Max(0.f, StartSeconds),ActiveDrawId);
                bNetworkDrawActive = true;
            }
    }
    StageActionRate=(Next==EBowStage::Drawing||Next==EBowStage::Holding||Next==EBowStage::Ready||Next==EBowStage::QuickCombat)?1.f:LightningHaste::ActionSpeed(GetOwner());
    Stage = Next;
    StageSeconds = Seconds;
    Elapsed = FMath::Max(0.f, StartSeconds);
    HoldElapsed = Next == EBowStage::Holding ? Elapsed : 0.f;
    bNockSoundPlayed = false;
    bTakeArrowSoundPlayed = false;
    // Start exactly when Drawing begins, after the 0.2 s entry. Direct-video
    // cues retain their native speed/pitch and may end before the draw motion;
    // do not stretch or loop the recording to fill the skill-adjusted clock.
    // Early release, cancellation and unequip still stop this voice.
    if (Next == EBowStage::Drawing && DrawSound && Elapsed < DrawSeconds)
    {
        const float Pitch = bOriginalAudioSpeed ? 1.f : FMath::Max(.01f, DrawSound->GetDuration() / DrawSeconds);
        const float StartTime = Elapsed * Pitch;
        if (StartTime < DrawSound->GetDuration())
            DrawAudio = UGameplayStatics::SpawnSound2D(this, DrawSound, bOriginalAudioSpeed ? .6f : .42f, Pitch, StartTime);
    }
}

void UBowWeaponComponent::BeginNock()
{
    if (!IsEquipped() || !CanUse()) return;
    if (Character.IsValid() && Character->IsChoosingAmmo()) return;
    if (Stage != EBowStage::Ready || bArrowNocked) return;
    if (Character.IsValid() && Character->IsCastBlockingLeftHandAction()) return;
    const auto* Pawn = Character.Get();
    if (ArrowsInPouch() <= 0 && (!Pawn || !Pawn->HasInfiniteReserveAmmoFor(ArrowId)))
    {
        ShowFeedback(TEXT("箭袋里没有可用的箭"));
        return;
    }
    // Nocking is a visual reservation. Spend once at successful launch, so
    // switching weapons, saving or interruption cannot destroy an unfired arrow.
    // Equipment may change while the bow's own data/signature stays unchanged.
    // Snapshot the current clock at action start, shared with server statistics.
    if (const auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if (const auto* Item = Profile->ActiveBow())
            NockSeconds = float(ColdSteelBow::Evaluate(*Item, Profile).Nock);
    SetStage(EBowStage::Nocking, NockSeconds);
    if (bUsesArms)
    {
        Viewmodel->CaptureCarry(FMath::Min(.07f, NockSeconds * .2f));
        PlayClip(ClipNock, 0.f, false);
    }
}

bool UBowWeaponComponent::SwitchArrow(const FString& Target)
{
    if (!IsEquipped() || !CanUse() || Stage != EBowStage::Ready) return false;
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const FString BowId = InstanceId;
    if (!Profile || !Profile->SelectBowAmmo(BowId, Target))
    {
        ShowFeedback(Profile ? Profile->ResultMessage() : TEXT("箭袋不可用"));
        return false;
    }
    RefreshEquipment(Profile);
    BeginNock();
    return true;
}

void UBowWeaponComponent::BeginPrimaryAttack()
{
    if(const auto* Light=GetOwner()->FindComponentByClass<UFPSIlluminationArrowComponent>();Light&&Light->IsPending())return;
    if(const auto* Element=GetOwner()->FindComponentByClass<UFPSElementalArrowComponent>();Element&&Element->IsPending())return;
    if(const auto* Rain=GetOwner()->FindComponentByClass<UFPSMagicArrowRainComponent>();Rain&&Rain->IsPending())return;
    if (!IsEquipped() || !CanUse()) return;
    if (Character.IsValid() && Character->IsChoosingAmmo()) return;
    if (Character.IsValid() && Character->IsCastBlockingLeftHandAction()) return;
    switch (Stage)
    {
    case EBowStage::Ready:
    case EBowStage::Release:
    case EBowStage::Recover:
        // Release/recovery are interruptible presentation, never a fire-input lock.
        BeginDrawEntry();
        return;
    case EBowStage::DrawEntry:
    case EBowStage::Nocking:
        return;                          // 搭箭进行中不接第二下，避免抢拍
    case EBowStage::Drawing:
    case EBowStage::Holding:
        return;                          // 已经拉开：等真实释放
    default:
        return;                          // 装备／近战／缓收弓仍由原动作占用
    }
}

void UBowWeaponComponent::BeginDrawEntry()
{
    const auto* Pawn = Character.Get();
    const auto* DrawProfile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!DrawProfile||DrawProfile->Stamina()<=0.f)
    {ShowFeedback(TEXT("体力不足，无法拉弓"));return;}
    if(ColdSteelBow::AuroraRiser(DrawProfile,DrawProfile->ActiveBow())&&!DrawProfile->HasInfiniteMana()&&DrawProfile->Mana()<=0.f)
    {ShowFeedback(TEXT("魔法不足，无法拉弓"));return;}
    if (!bArrowNocked && ArrowsInPouch() <= 0 && (!Pawn || !Pawn->HasInfiniteReserveAmmoFor(ArrowId)))
    {
        ShowFeedback(TEXT("箭袋里没有可用的箭"));
        return;
    }
    bChainEntry = Stage == EBowStage::Release || Stage == EBowStage::Recover;
    bEntryNeedsArrow = !bArrowNocked;
    // The matched loaded-ready pose already holds the string. Do not stop
    // there for a second entry phase after a manual nock or a let-down.
    if (bArrowNocked && bNockKeepsDrawPose)
    {
        SetStage(EBowStage::Drawing, 0.f);
        return;
    }
    // A second press may arrive before the release pose's first visible tick.
    if (bChainEntry) SampleArms();
    DrawEntrySeconds = BaseDrawEntrySeconds / (bEntryNeedsArrow ? ColdSteelBow::NockSpeedMultiplier(DrawProfile) : 1.f);
    SetStage(EBowStage::DrawEntry, DrawEntrySeconds);
    // Scale the authored quick/chain take only when fetching another arrow.
    // Already nocked arrows retain the original hand-to-string entry.
    if (bUsesArms)
    {
        const TCHAR* Entry = DrawEntryClip();
        if (Entry == ClipDraw) Viewmodel->CaptureEntry(DrawEntrySeconds);
        else Viewmodel->CaptureCarry(FMath::Min(.045f, DrawEntrySeconds * .225f));
        PlayClip(Entry, 0.f, false);
    }
}

const TCHAR* UBowWeaponComponent::DrawEntryClip() const
{
    const TCHAR* Wanted = bChainEntry ? TEXT("ChainNock") : TEXT("QuickNock");
    return bEntryNeedsArrow && ClipLength(Wanted) > 0.f ? Wanted : ClipDraw;
}

void UBowWeaponComponent::ReleasePrimaryAttack()
{
    // Door push starts only from Ready. A physical release during its gesture
    // must not turn that retained/nocked carry pose into a new equip cycle.
    if (Character.IsValid() && Character->IsDoorPushActive() && CanUse(true)) return;
    if (!IsEquipped() || !CanUse(false,true)) { CancelAction(); return; }
    // Releasing before reaching the string cancels without firing or spending.
    if (Stage == EBowStage::DrawEntry) { CancelAction(); return; }
    if (Stage != EBowStage::Drawing && Stage != EBowStage::Holding) return;
    // 仅输入释放可放箭；力竭、菜单与翻越等中断均收弓，不发射。
    ReleaseRatio = DrawFraction();
    if(auto* Rain=GetOwner()->FindComponentByClass<UFPSMagicArrowRainComponent>();Rain&&Rain->IsPrepared())
    {
        SampleArms();UpdatePoseLayers();UpdateBowGeometry();ReleasedNockCM=NockPoint();
        FVector Tail,Tip;if(GetMagicArrowEndpoints(Tail,Tip))Rain->Release(Tip);else CancelAction(false);
        return;
    }
    if (ReleaseRatio < ColdSteelBow::MinimumFireDrawFraction)
    {
        CancelAction(false);
        ShowFeedback(TEXT("至少拉弓至 50% 才能射出；已收弓，箭仍在弦上"));
        return;
    }
    SampleArms();
    UpdatePoseLayers();
    UpdateBowGeometry();
    ReleasedNockCM = NockPoint();
    const float ReleasedAt = DrawElapsed();
    const auto* Cadence=GetOwner()->FindComponentByClass<UBowCadenceComponent>();
    const bool bPerfect = (Cadence&&Cadence->HasAutomaticRhythmFor(InstanceId))
        || (ReleaseRatio>=1.f&&ColdSteelBow::IsPerfectRelease(ReleasedAt,DrawSeconds,PerfectWindowSeconds));
    if (LooseArrow(ReleaseRatio, bPerfect))
    {
        bLastPerfectRelease = bPerfect;
        bPerfectSpeedPending = bPerfect;
        LastReleaseElapsed = ReleasedAt;
        ReleaseFeedbackAge = 0.f;
        SetStage(EBowStage::Release, ReleaseSeconds);
    }
    else CancelAction(false);
    EndNetworkDraw();
}

void UBowWeaponComponent::CancelDrawForExhaustion(bool bMana)
{
    if(!IsDrawing())return;
    CancelAction(false);
    ShowFeedback(bMana?TEXT("魔法耗尽，已收弓；箭仍在弦上"):TEXT("体力耗尽，已收弓；箭仍在弦上"));
}

bool UBowWeaponComponent::BeginQuickCombat()
{
    if(CastTransferAlpha>0.f)return false;
    auto* Pawn = Character.Get();
    auto* Bash = Pawn ? Pawn->QuickCombatPistol.Get() : nullptr;
    if (!Pawn || !Bash || !IsEquipped() || !bPresentationReady || !bHasGripMarker
        || !Pawn->CanStartQuickCombatPriority()) return false;
    if (ClipLength(TEXT("QuickCombat")) <= KINDA_SMALL_NUMBER)
    {
        ShowFeedback(TEXT("弓的快速近战动作尚未加载"));
        return false;
    }
    const FString StartingInstance = InstanceId;
    Pawn->InterruptActionsForPriority(false);
    if (InstanceId != StartingInstance || !CanUse()) return false;
    Pawn->ExitSprintForWeapon();
    Bash->ConfigureForBow(ClipLength(TEXT("QuickCombat")));
    if (!Bash->BeginAction()) return false;
    bTriggerHeld = bSteadyHeld = false;
    SetStage(EBowStage::QuickCombat, Bash->GetSourceLength());
    Viewmodel->CaptureEntry(.06f);
    PlayClip(TEXT("QuickCombat"), 0.f, false);
    return true;
}

bool UBowWeaponComponent::GetQuickCombatStrikeProbe(FVector& Origin, float PoseSeconds)
{
    auto* Riser = Part(SlotRiser);
    if (Stage != EBowStage::QuickCombat || !Riser || !bHasGripMarker || !Viewmodel) return false;
    // Sample the contact pose even when the current frame skipped across it.
    PlayClip(TEXT("QuickCombat"), PoseSeconds, false);
    UpdatePoseLayers();
    UpdateBowGeometry();
    // The horizontal bow pushes forward between the two held contact points.
    Origin = Riser->GetComponentTransform().TransformPosition(
        FVector(0.f, .123f, BowQuickCombatMotion::StrikeLocalZCM));
    return true;
}

void UBowWeaponComponent::CancelAction(bool bImmediate)
{
    if(auto* Light=GetOwner()->FindComponentByClass<UFPSIlluminationArrowComponent>())Light->CancelFromBow();
    if(auto* Element=GetOwner()->FindComponentByClass<UFPSElementalArrowComponent>())Element->CancelFromBow();
    if(auto* Rain=GetOwner()->FindComponentByClass<UFPSMagicArrowRainComponent>())Rain->CancelFromBow();
    EndNetworkDraw();
    bLastPerfectRelease = bLastPiercingRelease = false;
    if (!bImmediate && IsDrawing() && bArrowNocked && CanUse())
    {
        LetDownPhase = Stage == EBowStage::Holding ? 1.f : FMath::Clamp(Elapsed / DrawSeconds, 0.f, 1.f);
        LetDownRatio = DrawFraction();
        bTriggerHeld = false;
        StopHandlingAudio();
        SetStage(EBowStage::LetDown, FMath::Lerp(.14f, .22f, LetDownRatio));
        Viewmodel->CaptureEntry(.035f);
        ShowFeedback(TEXT("缓收弓：箭仍在弦上"));
        return;
    }
    if (Stage == EBowStage::QuickCombat && Character.IsValid())
        if (auto* Bash = Character->QuickCombatPistol.Get(); Bash && Bash->GetStyle() == EQuickCombatStyle::Bow)
            Bash->Cancel();
    StopDrawAudio();
    StopHandlingAudio();
    bTriggerHeld = bSteadyHeld = false;
    EndDrawMotionWeight = ReleaseRatio = LetDownRatio = 0.f;
    ReleaseFeedbackAge = -1.f;
    if (auto* Riser = Part(SlotRiser)) Riser->ApplyStringLoad(BraceNockCM, BraceNockCM, FlexDistribution);
    if (Stage == EBowStage::Stowed) return;
    if ((Stage == EBowStage::Drawing || Stage == EBowStage::Holding) && bArrowNocked)
        ShowFeedback(TEXT("收弓：箭仍在弦上"));
    if (IsEquipped() && CanPresent(true)) SetStage(EBowStage::Ready, 0.f);
    else { Stage = EBowStage::Stowed; Elapsed = -1.f; HoldElapsed = 0.f; }
}
