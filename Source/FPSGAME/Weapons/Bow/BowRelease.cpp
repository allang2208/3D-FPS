#include "BowWeaponComponent.h"
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

namespace
{
constexpr float StringLongitudinalPhase = 3.f * PI;

float StringRingEnvelope(float Phase)
{
    return FMath::Exp(-1.45f * Phase) * (1.f - FMath::SmoothStep(.68f, 1.f, Phase));
}

float LongitudinalStringWave(float Phase)
{
    return FMath::Sin(StringLongitudinalPhase * Phase) * StringRingEnvelope(Phase);
}
}

float UBowWeaponComponent::ReleaseRing() const
{
    if (ReleaseFeedbackAge <= StringReturnSeconds || ReleaseFeedbackAge >= RingSeconds) return 0.f;
    const float Phase = (ReleaseFeedbackAge - StringReturnSeconds) / (RingSeconds - StringReturnSeconds);
    return ReleaseRatio * FeedbackScale * AimShakeScale() * LongitudinalStringWave(Phase);
}

FVector UBowWeaponComponent::NockPoint(const FVector* SampledHandInMount) const
{
    if(CastTransferAlpha>0.f)return FMath::Lerp(CastEntryNock,BraceNockCM,FMath::SmoothStep(0.f,.45f,CastTransferAlpha));
    // The string attaches to the finger contact marker only while held. After
    // release it returns to brace independently of the hand's follow-through.
    if (Stage == EBowStage::Release || Stage == EBowStage::Recover ||
        (Stage == EBowStage::DrawEntry && bEntryNeedsArrow && ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < RingSeconds))
    {
        if (ReleaseFeedbackAge >= RingSeconds) return BraceNockCM;
        const FVector Travel = BraceNockCM - ReleasedNockCM;
        const FVector Forward = Travel.GetSafeNormal();
        const float Strength = ReleaseRatio * FeedbackScale * AimShakeScale();
        const float RingDuration = RingSeconds - StringReturnSeconds;
        const float ReturnSlope = StringLongitudinalPhase * StringReturnSeconds / RingDuration;
        // Cap the Hermite end tangent at three stroke lengths for a monotone return.
        // Its speed at brace is also the initial speed of the free oscillation.
        const double AlongCM = FMath::Min(7.2 * Strength, 3. * Travel.Size() / ReturnSlope);
        if (ReleaseFeedbackAge <= StringReturnSeconds)
        {
            const float ReturnAlpha = FMath::Clamp(ReleaseFeedbackAge / StringReturnSeconds, 0.f, 1.f);
            return FMath::CubicInterp(ReleasedNockCM, FVector::ZeroVector, BraceNockCM,
                Forward * (AlongCM * ReturnSlope), ReturnAlpha);
        }

        const float Phase = (ReleaseFeedbackAge - StringReturnSeconds) / RingDuration;
        const FVector Across = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
        // Build the transverse vibration after crossing brace. It starts at zero
        // velocity and runs at a different frequency from the fore/aft swing.
        const float LateralWave = FMath::Sin(4.f * PI * Phase) * (1.f - FMath::Exp(-16.f * Phase))
            * StringRingEnvelope(Phase);
        return BraceNockCM + Forward * (AlongCM * LongitudinalStringWave(Phase))
            + Across * (2.8f * Strength * LateralWave);
    }
    const bool bEntryContact = Stage == EBowStage::DrawEntry && bEntryNeedsArrow && Elapsed >= DrawEntrySeconds * .90f;
    const bool bContacting = (Stage == EBowStage::Nocking && Elapsed >= NockSeconds * NockContactFraction) || bEntryContact;
    const bool bLoadedEntry = Stage == EBowStage::DrawEntry && !bEntryNeedsArrow && bArrowNocked && UsesCompoundOptic();
    if (!IsDrawing() && Stage != EBowStage::LetDown && !(Stage == EBowStage::Ready && bArrowNocked) && !bContacting && !bLoadedEntry) return BraceNockCM;
    if (SampledHandInMount || (bUsesArms && bHasGripMarker && bHasNockMarker && Viewmodel && Viewmodel->IsVisible()))
    {
        const FVector LocalPoint = SampledHandInMount ? *SampledHandInMount :
            AnimatedRiserMount().InverseTransformPosition((Viewmodel->GetSocketTransform(TEXT("bow_nock"), RTS_Component)
                * Viewmodel->GetRelativeTransform()).GetLocation());
        if (bContacting)
        {
            const float Contact = bEntryContact && !UsesCompoundOptic() ? 1.f : PickupSeatAlpha();
            return FMath::Lerp(BraceNockCM, LocalPoint, Contact);
        }
        return LocalPoint;
    }
    const float Ratio = Stage == EBowStage::LetDown
        ? LetDownRatio * (1.f - FMath::SmoothStep(0.f, 1.f, Elapsed / StageSeconds)) : DrawFraction();
    return FMath::Lerp(BraceNockCM, DrawAnchorCM, Ratio);
}

FVector UBowWeaponComponent::ArrowTipPoint() const
{
    // 箭尾落在弦结点，箭轴穿过箭台，沿弓体局部 +X 越过握把。
    const FVector Nock = NockPoint();
    return Nock + (ArrowRestCM - Nock).GetSafeNormal() * ArrowLengthCM;
}

void UBowWeaponComponent::SampleCompoundAimDepth()
{
    CompoundNearContactCM = -1.f;
    if (EquippedDefinition != TEXT("bow_frontier_compound") || AimAlpha() <= 0.f || !Camera || CastTransferAlpha > 0.f)
    {
        CompoundAimDepthCM = 0.;
        return;
    }
    // Keep the sampled release pose through follow-through.
    if (Stage == EBowStage::Release || Stage == EBowStage::Recover) return;
    if (!bArrowNocked && !IsDrawing() && Stage != EBowStage::Nocking && Stage != EBowStage::DrawEntry)
    {
        CompoundAimDepthCM = 0.;
        return;
    }
    CompoundAimDepthCM = RangeCM;
    const FVector Eye = Camera->GetComponentLocation();
    const FVector Forward = Camera->GetForwardVector();
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CompoundBowSight), true, GetOwner());
    if (!RangedAttackQuery::LineTraceSingle(GetWorld(), GetOwner(), Hit, Eye, Eye + Forward * RangeCM, ECC_Visibility, Query)) return;

    // A contact inside the held arrow is handled by the existing eye-to-tip
    // obstruction sweep. Do not turn the held shaft backwards at a wall.
    const FVector NominalNock = FMath::Lerp(BraceNockCM, DrawAnchorCM, DrawFraction());
    const double Overhang = FMath::Max(0., ArrowLengthCM - FVector::Distance(ArrowRestCM, NominalNock));
    const double RestDepth = bHasAimSight
        ? AimSightDistanceCM + AimBowRotation.RotateVector((ArrowRestCM - AimSightPointCM) * BowScale).X
        : AimRestLocationCM.X;
    if (Hit.Distance > RestDepth + Overhang * BowScale)
        CompoundAimDepthCM = Hit.Distance;
    else
        CompoundNearContactCM = Hit.Distance;
}

FVector UBowWeaponComponent::CompoundSightNock(const FVector& Nock) const
{
    if (UsesCompoundOptic())
    {
        // This is the optic's authored axis in bow space. The wrist follows the
        // draw clip along X; changes of target depth affect only the rigid pose.
        const FVector Axis = AimBowRotation.UnrotateVector(FVector::ForwardVector);
        return Axis.X > UE_SMALL_NUMBER
            ? ArrowRestCM + Axis * ((Nock.X - ArrowRestCM.X) / Axis.X) : Nock;
    }
    // Preserve draw length along X. Fit the fingers, nock and bowstring
    // together to the line through the real cradle and the sighted point.
    const FVector Anchor = bHasAimSight ? AimSightPointCM : ArrowRestCM;
    const FVector CameraAnchor = bHasAimSight ? FVector(AimSightDistanceCM, 0., 0.) : AimRestLocationCM;
    const FVector AimInBow = Anchor + AimBowRotation.UnrotateVector(
        FVector(CompoundAimDepthCM, 0., 0.) - CameraAnchor) / BowScale;
    const FVector ToAim = AimInBow - ArrowRestCM;
    if (ToAim.X <= UE_SMALL_NUMBER) return Nock;
    return ArrowRestCM + ToAim * ((Nock.X - ArrowRestCM.X) / ToAim.X);
}

bool UBowWeaponComponent::LooseArrow(float Ratio,bool bPerfect)
{
    const float ChargeDamage = ColdSteelBow::DrawDamageMultiplier(Ratio);
    if (ChargeDamage <= 0.f) return false;
    auto* Pawn = Character.Get();
    auto* Profile = GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Pawn || !Camera || !Profile || !bArrowNocked) return false;
    auto* Element=GetOwner()->FindComponentByClass<UFPSElementalArrowComponent>();
    const EArrowElement ArrowElement=Element?Element->ShotElement():EArrowElement::None;
    auto* Light=GetOwner()->FindComponentByClass<UFPSIlluminationArrowComponent>();
    const bool bIllumination=Light&&Light->ShotPrepared();FIlluminationArrowCast LightCast;FString LightReason;
    if(Pawn->HasAuthority()&&Light&&!Light->BuildShot(bIllumination,LightCast,LightReason)){ShowFeedback(LightReason);return false;}
    FElementalArrowCast ElementCast;FString ElementReason;
    if(Pawn->HasAuthority()&&Element&&!Element->BuildShot(ArrowElement,ElementCast,ElementReason))
    {ShowFeedback(ElementReason);return false;}
    const float Clamped = FMath::Clamp(Ratio, 0.f, 1.f);
    const float Cost = FMath::Max(0.f, StaminaCost * FMath::Lerp(.4f, 1.f, Clamped))*Profile->ActionStaminaMultiplier();
    if (!Profile->CanSpendStamina(Cost)) { ShowFeedback(TEXT("体力不足，已收弓")); return false; }
    const bool bAurora=ColdSteelBow::AuroraRiser(Profile,Profile->ActiveBow())!=nullptr;
    const float BeamMana=bAurora?Profile->AdjustedManaCost(Cost):0.f;
    const float SkillMana=bIllumination?LightCast.ManaCost:(ArrowElement!=EArrowElement::None?ElementCast.ManaCost:0.f);
    if(!Profile->CanSpendMana(BeamMana+(Pawn->HasAuthority()?SkillMana:0.f)))
    {ShowFeedback(TEXT("魔法不足，已收弓"));return false;}
    const auto Piercing=HeartPiercingArrow::ForModel(Profile,INDEX_NONE,DrawSeconds);
    const bool bPiercing=HeartPiercingArrow::IsCharged(Piercing,DrawElapsed(),Clamped);
    const float Speed = FullSpeedCM * FMath::Lerp(MinSpeedRatio, 1.f, Clamped)
        * (bPiercing?Piercing.SpeedMultiplier:1.f);
    // 从实际箭尖发射并朝准星落点收敛；近墙时另做相机到箭尖的阻挡扫掠。
    auto* Riser = Part(SlotRiser);
    auto* ArrowPart = Part(SlotArrow);
    const FVector CameraOrigin = Camera->GetComponentLocation();
    const FVector Nock = NockPoint();
    const FVector Tip = Nock + (ArrowRestCM - Nock).GetSafeNormal() * ArrowLengthCM;
    FVector Muzzle = Riser ? Riser->GetComponentTransform().TransformPosition(Tip) : CameraOrigin;
    FVector Tail = Riser ? Riser->GetComponentTransform().TransformPosition(Nock) : CameraOrigin;
    const bool bCompoundAim = CompoundAimDepthCM > 0. && AimAlpha() > 0.f && Riser && bHasGripMarker && Viewmodel && Viewmodel->IsVisible();
    if (bCompoundAim)
    {
        const auto* Shaft = ArrowPart ? ArrowPart->RodVisual(RodFor(SlotArrow, 0)) : nullptr;
        if (Shaft && Shaft->FirstPersonPrimitiveType == EFirstPersonPrimitiveType::FirstPerson && Camera->bEnableFirstPersonFieldOfView)
        {
            // The held shaft is rendered with the owner FOV. The free
            // projectile uses world projection. Match both ends at handoff.
            FMinimalViewInfo View;
            View.Location = CameraOrigin;
            View.Rotation = Camera->GetComponentRotation();
            View.FOV = Camera->FieldOfView;
            View.FirstPersonFOV = Camera->FirstPersonFieldOfView;
            Muzzle = View.TransformWorldToFirstPerson(Muzzle, true);
            Tail = View.TransformWorldToFirstPerson(Tail, true);
        }
    }
    FVector LaunchDirection;
    const bool bSightSettled = AimAlpha() >= 1.f - UE_SMALL_NUMBER;
    if (bCompoundAim && (bSightSettled || UsesCompoundOptic()))
    {
        // A scoped release during the raise follows the shaft that is on
        // screen, even before it finishes converging on the reticle.
        LaunchDirection = (Muzzle - Tail).GetSafeNormal();
        // A surface already crossed by the held arrow resolves immediately on
        // the authority's existing obstruction sweep, including a remote shot.
        if (bSightSettled && CompoundNearContactCM >= 0.f)
            Muzzle = CameraOrigin + Camera->GetForwardVector() * (CompoundNearContactCM + .1f);
    }
    else
    {
        // Trace the scattered ray itself so hip fire retains its spread.
        const float Spread = ShotSpread();
        FVector AimDirection = Camera->GetForwardVector();
        if (Spread > 0.f)
            AimDirection = (AimDirection + Camera->GetRightVector() * FMath::FRandRange(-Spread, Spread)
                + Camera->GetUpVector() * FMath::FRandRange(-Spread, Spread)).GetSafeNormal();
        FHitResult AimHit;
        const FVector FarAim = CameraOrigin + AimDirection * RangeCM;
        FCollisionQueryParams AimQuery(SCENE_QUERY_STAT(BowAim), true, Pawn);
        const bool bHitAim = RangedAttackQuery::LineTraceSingle(GetWorld(), GetOwner(), AimHit, CameraOrigin, FarAim, ECC_Visibility, AimQuery);
        const FVector AimVector = (bHitAim ? AimHit.ImpactPoint : FarAim) - Muzzle;
        LaunchDirection = FVector::DotProduct(AimVector, Camera->GetForwardVector()) > 0.f ? AimVector.GetSafeNormal() : AimDirection;
    }
    const FRotator Direction = LaunchDirection.Rotation();
    FActorSpawnParameters Spawn;
    Spawn.Owner = Pawn;
    Spawn.Instigator = Pawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(Pawn->GetNetMode()==NM_Client)
    {
        auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        FColdSteelInventoryRequest Request;Request.Action=EColdSteelInventoryAction::BowShot;
        Request.Item=InstanceId;Request.Eye=CameraOrigin;Request.Origin=Muzzle;Request.Direction=LaunchDirection;Request.Charge=Ratio;
        Request.BowReleaseElapsed=bPerfect?DrawElapsed():-1.f;
        Request.BowChargeElapsed=DrawElapsed();
        Request.BowDrawId=ActiveDrawId;
        Request.ArrowElement=ArrowElement;Request.bIlluminationArrow=bIllumination;
        if(!PS||!PS->RequestInventoryAction(Request)){ShowFeedback(TEXT("物品操作正在同步，请稍候"));return false;}
        LastReleasedDrawId=ActiveDrawId;
    }
    else if (auto* Arrow = GetWorld()->SpawnActor<ABowArrow>(Muzzle, Direction, Spawn))
    {
        FString Reason;
        bool bSpentOwnedArrow = false;
        if(bAurora||ArrowElement!=EArrowElement::None||bIllumination)
        {
            bSpentOwnedArrow=!Pawn->HasInfiniteReserveAmmoFor(ArrowId);
            if(bSpentOwnedArrow&&Profile->PouchCount(ArrowId)<1){Arrow->Destroy();ShowFeedback(TEXT("箭支不足"));return false;}
            auto After=Profile->Snapshot();
            if(bSpentOwnedArrow)--After.AmmoPouch.FindOrAdd(ArrowId);
            After.Stamina=FMath::Max(0.f,After.Stamina-Cost);
            After.StaminaRecoveryDelay=Profile->StaminaSettings().RecoveryDelay;
            if(!Profile->HasInfiniteMana())After.Mana-=BeamMana;
            if(bIllumination)Profile->StageIlluminationArrowCost(After,LightCast);
            else if(ArrowElement!=EArrowElement::None)Profile->StageElementalArrowCost(After,ElementCast);
            if(!Profile->CommitCampfireState(After,TEXT("Inventory"))){Arrow->Destroy();ShowFeedback(TEXT("箭支消耗未保存，未发射"));return false;}
        }
        else if (!ConsumeArrowFromPouch(Reason, bSpentOwnedArrow)) { Arrow->Destroy(); bArrowNocked = false; ShowFeedback(Reason); return false; }
        // 射击瞬间的修炼／符文快照与弹道组件同源；弓自己的暴击与破韧只在配了值时覆盖。
        FColdSteelSkillShot Shot = ColdSteelSkills::Snapshot(Pawn, Profile ? Profile->ActiveBow() : nullptr, true);
        Shot.bAuroraBeam=bAurora;
        Shot.bPerfectBowRelease = bPerfect;
        Shot.bHeartPiercingArrow=bPiercing;
        Shot.BowTargetPenetration=bPiercing?Piercing.TargetPenetration:0;
        Shot.DamageContext = FMath::Clamp(Ratio, 0.f, 1.f); // 联机上报：拉弦比，服务端按影子档案复算箭伤
        const auto* Item = Profile->ActiveBow();
        const float BaseDamage = Shot.DamagePanel.Total() > 0.f ? Shot.DamagePanel.Total() : FullDamage;
        const float Damage = BaseDamage * ChargeDamage * (bPiercing?Piercing.DamageMultiplier:1.f)
            * (Item ? Profile->AmmoDamageMultiplier(*Item) : 1.f);
        if (CriticalChance >= 0.f) Shot.CriticalChance = FMath::Max(Shot.CriticalChance, CriticalChance);
        if (ToughnessMultiplier > 0.f) Shot.ToughnessDamageMultiplier = ToughnessMultiplier;
        // 箭模取自 arrow 部件：已选箭种的弦上网格与飞行网格一致，箭台保持独立。
        Arrow->Configure(Damage, Speed, GravityCM, RangeCM, Shot,
                         ArrowPart ? ArrowPart->GetMesh() : nullptr,
                         ArrowHeadMesh ? ArrowHeadMesh.Get() : nullptr,
                         ArrowRadiusCM, ArrowLengthCM, ArrowId, bSpentOwnedArrow,
                         Item ? ColdSteelInventory::Number(*Item, TEXT("arrow_recovery_seconds"), 120.f) : 120.f);
        Arrow->SetElementalCast(ElementCast);
        if(bIllumination){Arrow->SetIlluminationCast(LightCast);Light->ShotCommitted();}
        if(Element&&ArrowElement!=EArrowElement::None)Element->ShotCommitted();
        if(Profile&&(bAurora||bIllumination||ArrowElement!=EArrowElement::None))Profile->NotifyMagicReleased();
        if(auto* Echo=Character->FindComponentByClass<UBowMountainEchoComponent>())Echo->CommitArrow(Arrow,InstanceId,Clamped,CameraOrigin);
        if(auto* Cadence=Character->FindComponentByClass<UBowCadenceComponent>())Cadence->CommitRelease(InstanceId,bPerfect);
        Arrow->ResolveLaunchObstruction(CameraOrigin);
    }
    else return false;
    // Capture the actual manual launch decision. Do not
    // infer a successful piercing shot from a later HUD clock or equipment state.
    bLastPiercingRelease=bPiercing;
    bArrowNocked = false;
    ShotBloom = FMath::Min(ShotSpreadStep * 3.f, ShotBloom + ShotSpreadStep * (1.f - AimAlpha()));
    StopDrawAudio();
    StopHandlingAudio();
    USoundBase* ShotSound = ReleaseSound.Get();
    float ShotPitch = bOriginalAudioSpeed ? 1.f : 1.f + .06f * Clamped;
    if (bPiercing)
        if (auto* SkillSound = Cast<USoundBase>(PiercingReleaseSoundPath().ResolveObject()))
        {
            ShotSound = SkillSound;
            ShotPitch = 1.f; // Preserve the selected E+F+G mix; do not layer the normal release again.
        }
    if (ShotSound) UGameplayStatics::PlaySound2D(this, ShotSound, bPiercing ? .95f : .6f, ShotPitch);
    if(Pawn->GetNetMode()!=NM_Client&&!bAurora&&ArrowElement==EArrowElement::None&&!bIllumination)Profile->SpendStamina(Cost);
    if(Pawn->GetNetMode()==NM_Client&&bIllumination)Light->PredictRelease();
    if(Pawn->GetNetMode()==NM_Client&&Element&&ArrowElement!=EArrowElement::None)Element->PredictRelease();
    return true;
}

