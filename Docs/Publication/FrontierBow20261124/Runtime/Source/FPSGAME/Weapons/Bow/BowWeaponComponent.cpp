#include "BowWeaponComponent.h"
#include "../../Movement/HorseRiderComponent.h"
#include "BowWeaponPrivate.h"
using namespace BowWeaponPrivate;

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

namespace BowWeaponPrivate
{
    const FSoftObjectPath& PiercingReleaseSoundPath()
    {
        static const FSoftObjectPath Path(TEXT("/Game/Skills/HeartPiercingArrow/Audio20261026/S_HeartPiercingArrow_Release.S_HeartPiercingArrow_Release"));
        return Path;
    }
    const TCHAR* const NockRoles[] = {TEXT("Nock"), TEXT("QuickNock"), TEXT("ChainNock")};
    const TCHAR* const NockKeys[] = {TEXT("bow_nock_animation"), TEXT("bow_draw_entry_animation"), TEXT("bow_chain_entry_animation")};
    const TCHAR* const GaitRoles[] = {TEXT("Walk"), TEXT("Run"), TEXT("LoadedWalk"), TEXT("LoadedRun"), TEXT("LoadedIdle")};
    /** 与采集工具同一拼接口径：`<前缀><角色名>` 的包内资产名。 */
    FSoftObjectPath BowAssetPath(const FString& Prefix, const TCHAR* Clip)
    {
        const FString Package = Prefix + Clip;
        return FSoftObjectPath(Package + TEXT(".") + FPackageName::GetLongPackageAssetName(Package));
    }

    /**
     * 三分量向量在 JSON 里写成 "x,y,z" 字符串：物品 Data 是扁平 JSON 文本，
     * 这里不引入第二套解析口径，读不到就保留代码里的实测默认值。
     * 5.8 的 `LexFromString` 只覆盖标量、`FParse::ParseVector` 已移除，故 cvar 也走这个解析器。
     */
    bool ReadVector3Text(const FString& Text, FVector& Out)
    {
        if (Text.IsEmpty()) return false;
        TArray<FString> Parts;
        Text.ParseIntoArray(Parts, TEXT(","), false);
        if (Parts.Num() < 3) return false;
        Out = FVector(FCString::Atof(*Parts[0]), FCString::Atof(*Parts[1]), FCString::Atof(*Parts[2]));
        return true;
    }

    bool ReadVector3(const FColdSteelItem* Item, const TCHAR* Key, FVector& Out)
    {
        return ReadVector3Text(ColdSteelInventory::Text(*Item, Key), Out);
    }

    // 弓体是移除旧烘焙弦后的静态网格；锚点在弓局部空间，长度沿 Z、出膛沿 +X。
    // 下面两个 cvar 是**叠加在数据表之上的实机对点偏移**，默认 0，不改存档也不改 JSON。
    // `TAutoConsoleVariable` 只支持标量／字符串，向量按 "x,y,z" 文本解析（与数据表同一口径）。
    TAutoConsoleVariable<FString> CVarBowLocation(TEXT("fps.Bow.LocationOffset"), TEXT("0,0,0"),
        TEXT("Additive camera-space offset (cm) on the bow viewmodel, \"x,y,z\"."));
    TAutoConsoleVariable<FString> CVarBowRotation(TEXT("fps.Bow.RotationOffset"), TEXT("0,0,0"),
        TEXT("Additive camera-space rotation (degrees, pitch,yaw,roll) on the bow viewmodel."));
    TAutoConsoleVariable<float> CVarBowSway(TEXT("fps.Bow.Sway"), 1.f,
        TEXT("Scale on the hold sway and the draw camera motion."));
}

const TCHAR* UBowWeaponComponent::ClipIdle = TEXT("Idle");
const TCHAR* UBowWeaponComponent::ClipDraw = TEXT("Draw");
const TCHAR* UBowWeaponComponent::ClipHold = TEXT("Hold");
const TCHAR* UBowWeaponComponent::ClipRelease = TEXT("Release");
const TCHAR* UBowWeaponComponent::ClipNock = TEXT("Nock");

// 三个默认部件槽。数据表用 `bow_part_slots` 覆盖这个清单（改造系统加瞄具／稳定器时只加键）。
const TCHAR* UBowWeaponComponent::SlotRiser = TEXT("riser");
const TCHAR* UBowWeaponComponent::SlotString = TEXT("string");
const TCHAR* UBowWeaponComponent::SlotArrow = TEXT("arrow");

namespace BowWeaponPrivate
{
    /** 逗号分隔的槽名清单；为空时回到默认三件（弓体／弓弦／弦上箭）。 */
    TArray<FName> BowSlotNames(const FString& Text)
    {
        TArray<FName> Slots;
        TArray<FString> Names;
        Text.ParseIntoArray(Names, TEXT(","), false);
        for (FString& Raw : Names)
        {
            Raw.TrimStartAndEndInline();
            if (!Raw.IsEmpty()) Slots.Add(FName(*Raw));
        }
        if (Slots.IsEmpty()) Slots = { FName(TEXT("riser")), FName(TEXT("string")), FName(TEXT("arrow")) };
        return Slots;
    }
}

UBowWeaponComponent::UBowWeaponComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UBowWeaponComponent::BeginPlay()
{
    Super::BeginPlay();
    Character=Cast<AFPSGAMECharacter>(GetOwner());
    if(Character.IsValid()&&Character->IsLocallyControlled())
    {
        InitializePresentation();
        if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        {RefreshEquipment(Profile);}
    }
    else SetComponentTickEnabled(false);
}
void UBowWeaponComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Optics) Optics->Release(*this);
    StopDrawAudio();
    StopHandlingAudio();
    if (LoadHandle)
    {
        LoadHandle->CancelHandle();
        LoadHandle.Reset();
    }
    if (Prompt)
    {
        Prompt->RemoveFromParent();
        Prompt = nullptr;
    }
    Super::EndPlay(Reason);
}

UBowArmsMeshComponent* UBowWeaponComponent::ArmsMesh() const { return Viewmodel.Get(); }

bool UBowWeaponComponent::BeginCastHandoff()
{
    if(!IsEquipped()||!bPresentationReady||!Viewmodel)return false;
    // Cancel draw without releasing or spending its reserved arrow. Keep the
    // current complete pose for the short transfer into ordinary carry.
    if(CastTransferAlpha<=0.f)
    {
        CastEntryNock=NockPoint();CancelAction();Viewmodel->CaptureCarry(.18f);
        Stage=EBowStage::Ready;Elapsed=0.f;
    }
    return true;
}

void UBowWeaponComponent::AdvanceActionBeforeCamera(float Delta)
{
    // A contact query refreshes the camera with Delta=0. Do not re-enter the action clock.
    if (!Character.IsValid() || !Character->IsLocallyControlled() || !IsEquipped() || Delta <= 0.f) return;
    // One displayed power drives the lens, mouse sensitivity and mechanical ring.
    // 95% of a wheel step settles in 150 ms, independent of frame rate.
    DisplayedOpticalMagnification = FMath::Lerp(DisplayedOpticalMagnification, OpticalMagnification, 1.f-FMath::Exp(-20.f*Delta));
    if (FMath::Abs(DisplayedOpticalMagnification-OpticalMagnification)<.001f) DisplayedOpticalMagnification=OpticalMagnification;
    UpdateScopeRing();
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
        {ClearPerfectSpeedPending();LastReleasedDrawId.Invalidate();}
    const auto* Magic=Character->FindComponentByClass<UFPSFireballComponent>();
    const auto* Use=Character->FindComponentByClass<UFPSPotionUseComponent>();
    const bool CastCarry=(Magic&&Magic->IsOccupyingLeftHand())||(Use&&Use->UsesBowSupport())||Viewmodel->IsReturningLeftHand();
    const float PreviousTransfer=CastTransferAlpha;
    CastTransferAlpha=FMath::Clamp(CastTransferAlpha+Delta*(CastCarry?1.f:-1.f)/FBowCastHandPose::Seconds,0.f,1.f);
    if(CastTransferAlpha>=.45f||!CastCarry)CastEntryNock=BraceNockCM;
    if(PreviousTransfer>0.f&&CastTransferAlpha<=0.f)Viewmodel->CaptureCarry(.12f);
    Viewmodel->CastTransfer=CastTransferAlpha;
    const auto AdvanceWeight = [Delta](float& Weight, bool bTarget, float In, float Out)
    {
        Weight = FMath::Clamp(Weight + FMath::Max(0.f, Delta) * (bTarget ? 1.f / In : -1.f / Out), 0.f, 1.f);
    };
    AdvanceWeight(CrouchProgress, CanPresent(true) && Character->bIsCrouched,CrouchInSeconds, CrouchOutSeconds);
    if(CastCarry||CastTransferAlpha>0.f)
    {
        AdvanceAimWeight(Delta,false);HipAimProgress=FMath::Max(0.f,HipAimProgress-Delta/FBowCastHandPose::Seconds);
        AdvanceLocomotion(Delta,false);Viewmodel->AdvanceEntry(Delta);VisualTime+=Delta;
        return;
    }
    // Door push owns input and its separate V7 fist, but the original bow
    // pose/locomotion clocks remain live for the shared return trajectory.
    const bool bUsable = CanUse(true,true);
    // Aim is advanced once before the camera reads its shaped weight.
    AdvanceAimWeight(Delta, bUsable && bSteadyHeld);
    AdvanceLocomotion(Delta, bUsable);
    // Keep the right/lower resting position. Rotate into the crosshair during
    // the same entry clock, retain the alignment for a nocked arrow, and let
    // it go with the existing release follow-through rather than snapping.
    const bool bFollowThrough = Stage == EBowStage::Release
        && Elapsed < (ReleaseSeconds + RecoverSeconds) * .15625f;
    const bool bAlignHip = Stage == EBowStage::DrawEntry || IsDrawing() || Stage == EBowStage::LetDown
        || (Stage == EBowStage::Ready && bArrowNocked)
        || (Stage == EBowStage::Nocking && Elapsed >= NockSeconds * NockContactFraction)
        || bFollowThrough;
    AdvanceWeight(HipAimProgress, bUsable && bAlignHip, DrawEntrySeconds,
        (ReleaseSeconds + RecoverSeconds) * .84375f);
    const auto* Pawn = Character.Get();
    const auto* Movement = Pawn ? Pawn->GetCharacterMovement() : nullptr;
    const float MoveTarget = Pawn ? FMath::Clamp(float(Pawn->GetVelocity().Size2D()) / 500.f, 0.f, 1.f) * MoveSpreadMax : 0.f;
    const float AirTarget = Movement && !Movement->IsMovingOnGround() && !UHorseRiderComponent::IsSeated(GetOwner()) ? AirSpreadMax : 0.f;
    MoveSpread = FMath::Lerp(MoveSpread, MoveTarget, 1.f - FMath::Exp(-6.f * FMath::Max(0.f, Delta)));
    AirSpread = FMath::Lerp(AirSpread, AirTarget, 1.f - FMath::Exp(-10.f * FMath::Max(0.f, Delta)));
    ShotBloom = FMath::Max(0.f, ShotBloom - FMath::Max(0.f, Delta) * SpreadRecovery);
    if (!bUsable)
    {
        CancelAction();
        if (CanPresent(true))
        {
            // Keep the manual idle clock live under UI. No draw/release stage
            // advances here, and a retained arrow stays in the inventory.
            if (Stage == EBowStage::Stowed) SetStage(EBowStage::Ready, 0.f);
            Viewmodel->AdvanceEntry(Delta);
            VisualTime += Delta;
        }
        return;
    }
    if (ReleaseFeedbackAge >= 0.f) ReleaseFeedbackAge += Delta;
    if (Stage == EBowStage::Stowed) SetStage(EBowStage::Equip, EquipSeconds);
    if (Elapsed < 0.f) return;
    if (Character.IsValid() && Character->IsSprinting() && Stage != EBowStage::Ready && Stage != EBowStage::Equip)
        CancelAction();
    Viewmodel->AdvanceEntry(Delta);
    if (Stage == EBowStage::QuickCombat)
    {
        auto* Bash = Character->QuickCombatPistol.Get();
        if (Bash && Bash->GetStyle() == EQuickCombatStyle::Bow)
        {
            Bash->AdvanceAction(Delta);
            Elapsed = Bash->GetActionAge();
        }
        VisualTime += Delta;
        if (!Bash || Bash->GetStyle() != EQuickCombatStyle::Bow || !Bash->IsOccupyingLeftHand())
            SetStage(EBowStage::Ready, 0.f);
        return;
    }
    Elapsed += Delta*StageActionRate;
    VisualTime += Delta;
    switch (Stage)
    {
    case EBowStage::Equip:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Ready, 0.f);
        break;
    case EBowStage::DrawEntry:
        if (bEntryNeedsArrow && !bTakeArrowSoundPlayed && Elapsed >= DrawEntrySeconds * .30f)
        {
            bTakeArrowSoundPlayed = true;
            if (Elapsed < DrawEntrySeconds * .90f) PlayHandlingSound(TakeArrowSound, .4f);
        }
        if (bEntryNeedsArrow && !bNockSoundPlayed && Elapsed >= DrawEntrySeconds * .90f)
        {
            bNockSoundPlayed = true;
            PlayHandlingSound(NockSound, .5f);
        }
        if (Elapsed >= StageSeconds)
        {
            const float Remainder = (Elapsed - StageSeconds)/StageActionRate;
            bArrowNocked = true;
            // Preserve the part of this frame beyond 0.2 s, so entry length
            // does not grow by an extra rendered frame at low frame rates.
            SetStage(EBowStage::Drawing, 0.f, Remainder);
        }
        break;
    case EBowStage::Nocking:
        if (!bTakeArrowSoundPlayed && Elapsed >= NockSeconds * TakeArrowContactFraction)
        {
            bTakeArrowSoundPlayed = true;
            // A long frame that already reached nock contact must not start
            // the earlier handling event after the arrow is on the string.
            if (Elapsed < NockSeconds * NockContactFraction)
                PlayHandlingSound(TakeArrowSound, .4f,
                    NockSeconds * NockContactFraction - Elapsed);
        }
        if (!bNockSoundPlayed && Elapsed >= NockSeconds * NockContactFraction)
        {
            bNockSoundPlayed = true;
            PlayHandlingSound(NockSound, .5f);
        }
        // 搭箭完成：左键仍按着就顺势开始拉弓，否则停在已上弦的 Ready。
        if (Elapsed >= StageSeconds)
        {
            const float Remainder = (Elapsed - StageSeconds)/StageActionRate;
            bArrowNocked = true;
            if (bTriggerHeld && bNockKeepsDrawPose)
                SetStage(EBowStage::Drawing, 0.f, Remainder);
            else
            {
                SetStage(EBowStage::Ready, 0.f);
                if (bTriggerHeld) BeginDrawEntry();
            }
        }
        break;
    case EBowStage::Drawing:
        if (Elapsed >= DrawSeconds) SetStage(EBowStage::Holding, 0.f, Elapsed - DrawSeconds);
        break;
    case EBowStage::Holding:
        HoldElapsed = Elapsed;
        break;
    case EBowStage::Release:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Recover, RecoverSeconds);
        break;
    case EBowStage::Recover:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Ready, 0.f);
        break;
    case EBowStage::LetDown:
        if (Elapsed >= StageSeconds) SetStage(EBowStage::Ready, 0.f);
        break;
    default:
        break;
    }
    // Full draw can be held until the player releases. TickStamina owns the
    // continuous cost; zero stamina cancels without launching or spending ammo.
    if(IsDrawing())
        if(const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Profile&&Profile->Stamina()<=0.f)
            CancelDrawForExhaustion();
}

void UBowWeaponComponent::TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta, Type, Tick);
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!Viewmodel)return;
    const bool Present = IsEquipped() && CanPresent(true);
    if (!Present)
    {
        if (Stage != EBowStage::Stowed) CancelAction();
        for (auto& Pair : Parts) if (Pair.Value) Pair.Value->SetPartVisible(false);
        Viewmodel->SetVisibility(false);
    }
    else
    {
        // Publish this frame's arms before querying grip/nock sockets. The
        // equip lift belongs to Equip, never to every newly entered stage.
        SampleArms();
        UpdatePoseLayers();
        UpdateBowGeometry();
        UpdateDoorPushPresentation();
    }
    if (Optics) Optics->Update(*this, Delta, Present);
    FeedbackSeconds = FMath::Max(0.f, FeedbackSeconds - Delta);
    HintCountdown -= Delta;
    if (HintCountdown <= 0.f)
    {
        HintCountdown = .15f;
        UpdateHint();
    }
}

void UBowWeaponComponent::ShowFeedback(const FString& Message)
{
    // 2026-09-28 用户要求删除弓的白色提示后这里只留状态写入（各调用点的返回流程
    // 依赖此函数存在），不再有任何显示；需要恢复提示时重建 UpdateHint 的控件路径。
    Feedback = Message;
    FeedbackSeconds = 2.5f;
}

void UBowWeaponComponent::UpdateHint()
{
    // 2026-09-28 用户要求：弓的白色提示字段（弹出式操作反馈，74% 高度）全部删除；
    // 常驻状态行 StatusLine 原本就是永不显示的死代码，实现与声明已一并移除。
    if (Prompt) Prompt->SetVisibility(ESlateVisibility::Collapsed);
}
