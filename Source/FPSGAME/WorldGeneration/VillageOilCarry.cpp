#include "VillageOilCarry.h"
#include "VillageHotOil.h"
#include "VillageOilMotion.h"
#include "VillageOilArmSolver.h"
#include "VillageSiegeControl.h"
#include "TemperateHillsWorld.h"
#include "VillageSiegeUpgrades.h"
#include "EngineUtils.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../Movement/FPSFootstepAudioComponent.h"
#include "../Building/FPSForgeWorkComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "../Characters/FPSPlayerBodyGrip.h"
#include "VillageOilArmsMeshComponent.h"
#include "../Weapons/WoodenTorchArmsComponent.h"
#include "../Weapons/Staff/StaffGripPose.h"
#include "../Weapons/WeaponPresentationMaterials.h"
#include "../Skills/FPSMagicPreview.h"
#include "../Skills/MeteorAssets.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Net/UnrealNetwork.h"

namespace
{
using namespace VillageOilMotion;
double Clock(const UWorld* W){const auto* G=W?W->GetGameState():nullptr;return G?G->GetServerWorldTimeSeconds():(W?W->GetTimeSeconds():0.);}

template <typename T>
void StepSpring(T& Val,T& Vel,float Target,float Stiffness,float Damping,float Delta)
{
    const float Force=(Target-float(Val))*Stiffness-float(Vel)*Damping;
    Vel+=Force*Delta;
    Val+=Vel*Delta;
}
}

bool UVillageOilCarry::IsStowingEquipment(const AActor* Owner)
{
    const auto* Carry=Owner?Owner->FindComponentByClass<UVillageOilCarry>():nullptr;
    return Carry && Carry->IsPresentationActive();
}

bool UVillageOilCarry::IsBlockingWeaponActions(const AActor* Owner)
{
    const auto* Carry=Owner?Owner->FindComponentByClass<UVillageOilCarry>():nullptr;
    return Carry && Carry->IsPendingOrOccupied();
}

UVillageOilCarry::UVillageOilCarry()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
}
AFPSGAMECharacter* UVillageOilCarry::Player() const {return Cast<AFPSGAMECharacter>(GetOwner());}
USkeletalMeshComponent* UVillageOilCarry::GetFirstPersonArms() const {return Arms.Get();}
UDecalComponent* UVillageOilCarry::GetPourPreviewDecal() const {return PourPreviewDecal.Get();}
UMaterialInstanceDynamic* UVillageOilCarry::GetPourPreviewMID() const {return PourPreviewMID.Get();}
void UVillageOilCarry::RefreshPourPreview(float Delta) {UpdatePourPreview(Delta);}
void UVillageOilCarry::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UVillageOilCarry,State);
}

bool UVillageOilCarry::HandsInUse(bool bAllowInspect) const
{
    const auto* P=Player();
    const auto* PC=P?Cast<AFPSGAMEPlayerController>(P->GetController()):nullptr;
    if(!PC || PC->IsInBuildMode() || (PC->GetSiegeControl() && PC->GetSiegeControl()->Active()))return true;
    if(const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health && Health->IsDead())return true;
    if(UPlayerKnockdownComponent::IsKnockedDown(P) || P->IsTraversing())return true;
    if(UHorseRiderComponent::IsSeated(P) || UFPSFurnitureRestComponent::IsResting(P) ||
       UFPSForgeWorkComponent::IsWorking(P) || UBoundCongregateCaptureComponent::IsCaptured(P))return true;
    if(const auto* Ride=P->FindComponentByClass<UHorseRiderComponent>();Ride && Ride->Transferring())return true;

    if(!P->IsLocallyControlled())
    {
        // Only consult replicated body presentation on remote authority proxies, and ignore Equip/Inspect/stale actions.
        if(const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
        {
            const auto& S=Body->CurrentBodyState();
            const bool bFreshAction=!Occupied() || S.ActionStartedAt>=State.Since-.05f;
            if(S.ConsumeHands || S.RightHand.bReloading || S.LeftHand.bReloading || S.bAiming ||
               S.Motion==EFPSBodyMotion::Vault || S.Motion==EFPSBodyMotion::Mantle ||
               (bFreshAction && S.Action!=EFPSBodyAction::None && S.Action!=EFPSBodyAction::Equip && S.Action!=EFPSBodyAction::Inspect))
                return true;
        }
        return false;
    }

    if(const auto* Bow=P->FindComponentByClass<UBowWeaponComponent>();Bow && (Bow->IsAimHeld() || Bow->IsDrawing()))return true;
    const bool bWeaponReload=P->IsReloading() || P->IsOffhandReloadActive();
    const auto* Sword=P->FindComponentByClass<URuneSwordComponent>();
    const bool bInspectBlock=!bAllowInspect && (P->GetWeaponState()==EAKMWeaponState::Inspecting ||
        (Sword && Sword->IsInspecting()));
    return P->IsAiming() || bWeaponReload || bInspectBlock || P->IsCastingWithLeftHand() || P->IsSpellGestureBlocking();
}

bool UVillageOilCarry::CanTake(bool bAllowInspect,FString* OutReason) const
{
    const auto* P=Player();
    if(!P){if(OutReason)*OutReason=TEXT("无效角色");return false;}
    if(UHorseRiderComponent::IsSeated(P)){if(OutReason)*OutReason=TEXT("骑乘中无法取油");return false;}
    if(HandsInUse(bAllowInspect) || AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(P->GetController())))
    {if(OutReason)*OutReason=TEXT("双手正忙");return false;}
    if(P->IsLocallyControlled() && (P->IsLeftHandBusyForCast() || P->IsSwitchingWeapon() || P->IsWeaponFireHeld()))
    {if(OutReason)*OutReason=TEXT("双手正忙");return false;}
    return true;
}

bool UVillageOilCarry::CanTakeNow(FString* OutReason) const
{
    if(IsPendingOrOccupied()){if(OutReason)*OutReason=TEXT("已端着油锅");return false;}
    return CanTake(true,OutReason);
}

void UVillageOilCarry::RememberEquipment()
{
    OffhandSlotAtTake=INDEX_NONE;
    ToolItemAtTake.Reset();
    if(const auto* Model=ColdSteelAuthority::ForPawn(Player()))RefreshEquipment(*Model);
}

void UVillageOilCarry::RefreshEquipment(const UColdSteelStatusModel& Model)
{
    const int32 Slot=Model.ActiveOffhandSlot();
    const auto* Main=Model.Equipped();
    const auto* Off=Model.Equipped(Slot);
    const auto* Tool=Model.ActiveProductionTool();
    const FString MainId=Main?Main->InstanceId:FString();
    const FString OffId=Off?Off->InstanceId:FString();
    const FString ToolId=Tool?Tool->InstanceId:FString();
    if(OffhandSlotAtTake==INDEX_NONE)
    {
        OffhandSlotAtTake=Slot;
        MainItemAtTake=MainId;
        OffhandItemAtTake=OffId;
        ToolItemAtTake=ToolId;
        return;
    }
    if(Slot!=OffhandSlotAtTake || MainId!=MainItemAtTake || OffId!=OffhandItemAtTake || ToolId!=ToolItemAtTake)
        Cancel();
}

void UVillageOilCarry::ClearStaleWeaponActions()
{
    if(auto* P=Player())
    {
        P->PrepareForPanelInput();
        P->PrepareForConsumableUse();
    }
}

void UVillageOilCarry::Take(AVillageOilKettle* Kettle)
{
    if(bTakePending && Clock(GetWorld())-TakePendingSince>1.5)
    {
        bTakePending=false;
        OffhandSlotAtTake=INDEX_NONE;
        ToolItemAtTake.Reset();
    }
    if(!Kettle || Occupied() || bTakePending || !CanTake(true))return;
    ClearStaleWeaponActions();
    bTakePending=true;bLocalCancel=false;
    TakePendingSince=Clock(GetWorld());
    RememberEquipment();
    ServerTake(Kettle);
}
void UVillageOilCarry::ServerTake_Implementation(AVillageOilKettle* Kettle)
{
    if(auto* P=Player())P->InterruptWeaponInspection();
    const bool Ok=!Occupied() && CanTake(true) && IsValid(Kettle) && Kettle->GetHealth()>0 &&
        ColdSteelWorldInteraction::IsFocused(Player(),Kettle);
    if(Ok){RememberEquipment();SetState(EOilCarryPhase::Held);}
    ClientTakeResult(Ok);
}
void UVillageOilCarry::ClientTakeResult_Implementation(bool Accepted)
{
    if(!Accepted)
    {
        bTakePending=false;
        OffhandSlotAtTake=INDEX_NONE;
        ToolItemAtTake.Reset();
        return;
    }
    ClearStaleWeaponActions();
}
void UVillageOilCarry::SetState(EOilCarryPhase Phase)
{
    State.Phase=Phase;State.Since=Clock(GetWorld());bReleasedOil=false;bPourQueued=false;
    if(Phase==EOilCarryPhase::Empty)
    {
        bHasPreviewPoint=false;bHasPreviewCamera=false;
        bRightPressed=false;
        bLeftPressed=false;
        HidePourPreview();
    }
    else if(Phase!=EOilCarryPhase::Held)HidePourPreview();
    OnRep_Hands();Player()->ForceNetUpdate();
}
void UVillageOilCarry::OnRep_Hands()
{
    bTakePending=false;
    if(!Occupied())
    {
        bLocalCancel=false;
        OffhandSlotAtTake=INDEX_NONE;
        ToolItemAtTake.Reset();
        LookSway=LookSwayVel=OilSlosh=OilSloshVel=PrevOilShake=FVector2D::ZeroVector;
        LandingDip=LandingDipVel=0.f;
        bHasPrevControlRot=false;bWasFalling=false;bHasPreviewPoint=false;bHasPreviewCamera=false;
        HidePourPreview();
    }
    else if(State.Phase!=EOilCarryPhase::Held)HidePourPreview();
    if(Occupied())
    {
        ClearStaleWeaponActions();
        if(Player()->IsLocallyControlled() && !Player()->HasAuthority())
        {
            // A slot change can land between the pickup request and the server acknowledgement.
            if(const auto* Model=ColdSteelAuthority::ForPawn(Player()))RefreshEquipment(*Model);
        }
    }
    SetComponentTickEnabled(Occupied());
    if(GetNetMode()!=NM_DedicatedServer){if(Occupied())PrepareVisual();UpdateVisual();}
}
void UVillageOilCarry::ServerCancel_Implementation(){if(Occupied())SetState(EOilCarryPhase::Empty);}
void UVillageOilCarry::Cancel()
{
    if((!Occupied() && !bTakePending) || bLocalCancel)return;
    OffhandSlotAtTake=INDEX_NONE;
    ToolItemAtTake.Reset();
    bHasPreviewPoint=false;bHasPreviewCamera=false;
    HidePourPreview();
    if(Player()->HasAuthority()){bTakePending=false;if(Occupied())SetState(EOilCarryPhase::Empty);return;}
    if(!Player()->IsLocallyControlled())return;
    bLocalCancel=true;bTakePending=false;UpdateVisual();ServerCancel();
}
bool UVillageOilCarry::HandleInput(const FInputKeyEventArgs& E)
{
    const bool Primary=E.Key==EKeys::LeftMouseButton || E.Key==EKeys::Gamepad_RightTrigger;
    const bool Secondary=E.Key==EKeys::RightMouseButton || E.Key==EKeys::Gamepad_LeftTrigger;
    if(Primary && E.Event==IE_Released && bLeftPressed){bLeftPressed=false;return true;}
    if(Secondary && E.Event==IE_Released && bRightPressed){bRightPressed=false;return true;}
    if((!Occupied() && !bTakePending) || bLocalCancel)return false;
    if(Primary && AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player()->GetController())))return false;
    if(Primary)
    {
        if(E.Event==IE_Pressed)
        {
            bLeftPressed=true;
            if(State.Phase==EOilCarryPhase::Held && !HandsInUse())ServerPour();
        }
        return true;
    }
    // Block RMB aiming/ADS/block/offhand while holding the oil pot so hidden weapons cannot steal focus or cancel it.
    if(Secondary)
    {
        if(E.Event==IE_Pressed)bRightPressed=true;
        return true;
    }
    // A second interaction with the same supply cannot start another pickup. Other keys go to their action owner.
    if(E.Event==IE_Pressed && E.Key==EKeys::E &&
       Cast<AVillageOilKettle>(ColdSteelWorldInteraction::TraceTarget(Cast<APlayerController>(Player()->GetController()))))return true;
    return false;
}
void UVillageOilCarry::ServerPour_Implementation()
{
    if(State.Phase!=EOilCarryPhase::Held || HandsInUse())return;
    if(Clock(GetWorld())-State.Since<Raise)bPourQueued=true;
    else SetState(EOilCarryPhase::Pour);
}

FTransform UVillageOilCarry::PanPose(bool FirstPerson,bool bIncludeLocalSway) const
{
    const double Now=Clock(GetWorld());
    const double Age=FMath::Max(0.,Now-State.Since);
    const double Lift=State.Phase==EOilCarryPhase::Held?LiftCurve(Age):1.;
    const bool Pouring=State.Phase==EOilCarryPhase::Pour;
    const double Load=Pouring?AnticipationCurve(Age):0.;
    const double Tilt=Pouring?Tip(Age):0.;
    const double Push=Pouring?PushCurve(Age):0.;
    const double Down=Pouring?LowerCurve(Age):0.;
    const double Tremor=Pouring?PourTremor(Age):0.;

    // Lower, roomier carry stance (~18 cm below eyes) avoids cramping elbows in front of the chin.
    double X=(FirstPerson?38.5:31.0)+6.8*Push-4.4*Load-6.5*(1.-Lift+Down);
    double Y=-3.2*Tilt+.45*Tremor;
    double Z=(FirstPerson?-18.2:Player()->BaseEyeHeight-33.5)+4.2*Push-3.4*Load-(FirstPerson?27.:21.)*(1.-Lift)-(FirstPerson?31.:24.)*Down;
    double Pitch=-34.*Tilt+5.5*Load+1.4*Tremor;
    double Yaw=-9.*Tilt;
    double Roll=-22.*Tilt-.8*Tremor;

    if(FirstPerson && bIncludeLocalSway)
    {
        const auto* P=Player();
        const double SwayScale=Pouring?(1.-0.75*FMath::SmoothStep(.08,.35,Age)*(1.-FMath::SmoothStep(.84,1.18,Age))):Lift;
        const double BreathZ=.32*FMath::Sin(Now*1.75)+.14*FMath::Sin(Now*3.83);
        const double BreathPitch=.52*FMath::Sin(Now*1.75-.45);

        double StrideX=0.,StrideY=0.,StrideZ=0.,StridePitch=0.,StrideRoll=0.;
        if(P && P->IsLocallyControlled())
        {
            const float MoveAlpha=FMath::Clamp(P->GroundLocomotionWeight,0.f,1.f);
            const float CrouchScale=P->bIsCrouched?.55f:1.f;
            const float SprintScale=P->IsSprinting()?1.25f:1.f;
            const float BobAmp=MoveAlpha*CrouchScale*SprintScale*float(SwayScale);
            if(BobAmp>.005f)
            {
                const auto* Foot=P->FindComponentByClass<UFPSFootstepAudioComponent>();
                const float Phase=Foot?Foot->GetStridePhaseRadians():P->M4SprintPhase;
                // Asymmetric step bounce: brisk downward settle on heel strike, smoother rise.
                const float DoubleBeat=FMath::Sin(2.f*Phase-.35f);
                const float SharpBeat=DoubleBeat-.28f*FMath::Cos(4.f*Phase-.7f);
                StrideZ=BobAmp*(.95f*SharpBeat-.18f);
                StrideY=BobAmp*1.25f*FMath::Sin(Phase-.45f);
                StrideX=BobAmp*.45f*FMath::Cos(2.f*Phase);
                StridePitch=BobAmp*1.55f*DoubleBeat;
                StrideRoll=BobAmp*2.15f*FMath::Sin(Phase-.65f);
            }
        }
        X+=StrideX;
        Y+=StrideY+LookSway.X*SwayScale;
        Z+=BreathZ*SwayScale+StrideZ+LandingDip+LookSway.Y*.45*SwayScale;
        Pitch+=BreathPitch*SwayScale+StridePitch+LandingDip*1.15f-LookSway.Y*.85*SwayScale;
        Yaw+=LookSway.X*1.35*SwayScale;
        Roll+=StrideRoll-LookSway.X*1.25*SwayScale;
    }

    // The left palm supports the low handle; the right lifts the opposite handle over the left-front rim.
    return FTransform(FRotator(Pitch,Yaw,Roll),FVector(X,Y,Z));
}

void UVillageOilCarry::AdvanceLocomotionFeedback(float Delta)
{
    auto* P=Player();
    if(!P || !P->IsLocallyControlled() || Delta<=SMALL_NUMBER)return;
    const float SafeDt=FMath::Min(Delta,.05f);

    // 1. Control-rotation angular velocity drives damped look inertia sway.
    const FRotator Ctrl=P->GetControlRotation();
    float TargetSwayX=0.f,TargetSwayY=0.f;
    if(bHasPrevControlRot)
    {
        const FRotator DeltaRot=(Ctrl-PrevControlRot).GetNormalized();
        const float YawRate=FMath::Clamp(DeltaRot.Yaw/SafeDt,-360.f,360.f);
        const float PitchRate=FMath::Clamp(DeltaRot.Pitch/SafeDt,-360.f,360.f);
        TargetSwayX=FMath::Clamp(-YawRate*.011f,-2.5f,2.5f);
        TargetSwayY=FMath::Clamp(-PitchRate*.010f,-1.8f,1.8f);
    }
    PrevControlRot=Ctrl;
    bHasPrevControlRot=true;
    StepSpring(LookSway.X,LookSwayVel.X,TargetSwayX,95.f,15.5f,SafeDt);
    StepSpring(LookSway.Y,LookSwayVel.Y,TargetSwayY,105.f,16.5f,SafeDt);

    // 2. Landing impulse dip when touching ground after a fall/jump.
    if(const auto* Move=P->GetCharacterMovement())
    {
        const bool bFalling=Move->IsFalling();
        if(bWasFalling && !bFalling)
        {
            const float Impact=FMath::Clamp(-float(Move->Velocity.Z)/650.f,.25f,1.f);
            LandingDipVel-=22.f*Impact;
        }
        bWasFalling=bFalling;
    }
    StepSpring(LandingDip,LandingDipVel,0.f,130.f,17.f,SafeDt);
    LandingDip=FMath::Clamp(LandingDip,-4.5f,2.2f);

    // 3. Hot-oil slosh oscillator inside the bowl driven by look sway, stride, and landing.
    const FVector2D Accel=(FVector2D(LookSway.X,LandingDip*.55f)-PrevOilShake)/SafeDt;
    PrevOilShake=FVector2D(LookSway.X,LandingDip*.55f);
    const FVector2D SloshTarget(
        FMath::Clamp(-Accel.Y*.022f+LookSway.Y*.04f,-.22f,.22f),
        FMath::Clamp(Accel.X*.026f+LookSway.X*.06f,-.24f,.24f));
    float SX=float(OilSlosh.X),SY=float(OilSlosh.Y),VX=float(OilSloshVel.X),VY=float(OilSloshVel.Y);
    StepSpring(SX,VX,float(SloshTarget.X),48.f,6.2f,SafeDt);
    StepSpring(SY,VY,float(SloshTarget.Y),48.f,6.2f,SafeDt);
    OilSlosh=FVector2D(FMath::Clamp(SX,-.26,0.26),FMath::Clamp(SY,-.26,0.26));
    OilSloshVel=FVector2D(VX,VY);
}

bool UVillageOilCarry::ResolvePourTarget(FVector& OutGroundPoint,FVector& OutNormal) const
{
    const auto* P=Player();
    const UWorld* W=GetWorld();
    if(!P || !W)return false;
    const FVector Eye=P->GetPawnViewLocation();
    const FRotator Aim=P->GetController()?P->GetControlRotation():P->GetBaseAimRotation();
    const double Pitch=FRotator::NormalizeAxis(Aim.Pitch);
    const FVector FlatFwd=FRotator(0.,Aim.Yaw,0.).Vector();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(OilPour),false,P);
    FCollisionObjectQueryParams Objects(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);

    // At level/upward look keep the canonical 300 cm throw. When looking down from a battlement,
    // pull the horizontal reach inward so hot oil lands right at the wall base / gate defenders.
    double HorizontalReach=VillageHotOil::Reach;
    if(Pitch<-10.)
    {
        const double DownAlpha=FMath::SmoothStep(-10.,-68.,Pitch);
        HorizontalReach=FMath::Lerp(double(VillageHotOil::Reach),118.,DownAlpha);
    }

    auto TryDropAt=[&](double ReachDist,FVector& HitPt,FVector& HitN)
    {
        const FVector Column=Eye+FlatFwd*ReachDist;
        FHitResult Block,Ground;
        FVector End=Column;
        if(W->LineTraceSingleByObjectType(Block,Eye,Column,Objects,Q))
            End=Block.ImpactPoint-FlatFwd*12.;
        if(W->LineTraceSingleByObjectType(Ground,End,End-FVector(0,0,12000.),Objects,Q) &&
           Ground.IsValidBlockingHit() && Ground.ImpactNormal.Z>=.50)
        {
            HitPt=Ground.ImpactPoint;
            HitN=Ground.ImpactNormal;
            return true;
        }
        return false;
    };

    // Direct downward view ray when aiming steeply down over a parapet.
    if(Pitch<-28.)
    {
        FHitResult SightHit;
        const FVector SightDir=Aim.Vector();
        if(W->LineTraceSingleByObjectType(SightHit,Eye,Eye+SightDir*3200.,Objects,Q) &&
           SightHit.IsValidBlockingHit() && SightHit.ImpactNormal.Z>=.50 &&
           FVector::Dist2D(Eye,SightHit.ImpactPoint)<=VillageHotOil::Reach+40.)
        {
            OutGroundPoint=SightHit.ImpactPoint;
            OutNormal=SightHit.ImpactNormal;
            return true;
        }
    }

    for(const double Scale:{1.,.65,.35})
    {
        if(TryDropAt(HorizontalReach*Scale,OutGroundPoint,OutNormal))return true;
    }
    return false;
}

void UVillageOilCarry::HidePourPreview()
{
    if(PourPreviewDecal && !PourPreviewDecal->bHiddenInGame)PourPreviewDecal->SetHiddenInGame(true);
}

void UVillageOilCarry::UpdatePourPreview(float Delta)
{
    (void)Delta;
    auto* P=Player();
    UWorld* W=GetWorld();
    if(!P || !W || !P->IsLocallyControlled() || !IsPresentationActive() || State.Phase!=EOilCarryPhase::Held || GetNetMode()==NM_DedicatedServer)
    {HidePourPreview();return;}

    // Camera-delta dirty gate keeps 144+ Hz panning crisp while skipping redundant traces when aim is steady.
    const FVector Eye=P->GetPawnViewLocation();
    const FRotator Aim=P->GetController()?P->GetControlRotation():P->GetBaseAimRotation();
    const double Now=W->GetTimeSeconds();
    const bool bCameraMoved=!bHasPreviewCamera || FVector::DistSquared(Eye,LastPreviewEye)>.25 || !(Aim-LastPreviewAim).GetNormalized().IsNearlyZero(.08f);
    if(bCameraMoved || Now>=NextPreviewSampleAt)
    {
        NextPreviewSampleAt=Now+.25;
        LastPreviewEye=Eye;LastPreviewAim=Aim;bHasPreviewCamera=true;
        bHasPreviewPoint=ResolvePourTarget(CachedPreviewPoint,CachedPreviewNormal);
        if(!CachedHillsWorld.IsValid())
            for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){CachedHillsWorld=*It;break;}
    }
    if(!bHasPreviewPoint){HidePourPreview();return;}
    if(!PourPreviewMaterial)PourPreviewMaterial=Cast<UMaterialInterface>(FSoftObjectPath(MeteorSpellAssets::Preview).TryLoad());
    if(!PourPreviewMaterial){HidePourPreview();return;}

    const bool bCreateDecal=!PourPreviewDecal;
    if(bCreateDecal)
    {
        PourPreviewDecal=NewObject<UDecalComponent>(P,TEXT("OilPourAimDecal"),RF_Transient);
        P->AddInstanceComponent(PourPreviewDecal);
        PourPreviewDecal->SetDecalMaterial(PourPreviewMaterial);
        PourPreviewDecal->SetWorldRotation(FRotationMatrix::MakeFromX(-CachedPreviewNormal).Rotator());
        PourPreviewDecal->SetFadeScreenSize(0.f);
        PourPreviewDecal->RegisterComponent();
        PourPreviewMID=PourPreviewDecal->CreateDynamicMaterialInstance();
        if(PourPreviewMID)PourPreviewMID->SetVectorParameterValue(TEXT("Tint"),FPSMagicPreview::LineColor());
    }
    const FVector Location=CachedPreviewPoint+CachedPreviewNormal*4.f;
    const FRotator Rotation=FRotationMatrix::MakeFromX(-CachedPreviewNormal).Rotator();
    if(bCreateDecal || !PourPreviewDecal->GetComponentLocation().Equals(Location,.01f) || !PourPreviewDecal->GetComponentRotation().Equals(Rotation,.01f))
    {
        PourPreviewDecal->SetWorldLocationAndRotation(Location,Rotation);
        if(PourPreviewMID)
        {
            PourPreviewMID->SetVectorParameterValue(TEXT("Center"),FLinearColor(CachedPreviewPoint));
            PourPreviewMID->SetVectorParameterValue(TEXT("SurfaceNormal"),FLinearColor(CachedPreviewNormal));
        }
    }
    const float OilRadius=CachedHillsWorld.IsValid()
        ?float(VillageSiegeUpgrades::Installed(CachedHillsWorld->GetSiegeRanks(),VillageSiegeUpgrades::HotOil,VillageSiegeUpgrades::OilRadius))
        :float(VillageSiegeUpgrades::Value(VillageSiegeUpgrades::HotOil,VillageSiegeUpgrades::OilRadius,0));
    const FVector2D Radii(OilRadius,FMath::Min(92.f,OilRadius*.36f));
    if(bCreateDecal || CachedPreviewRadii!=Radii)
    {
        const FVector Size(104.f,Radii.X+16.f,Radii.X+16.f);
        if(PourPreviewDecal->DecalSize!=Size){PourPreviewDecal->DecalSize=Size;PourPreviewDecal->MarkRenderStateDirty();}
        if(PourPreviewMID)
        {
            PourPreviewMID->SetScalarParameterValue(TEXT("ImpactRadius"),Radii.X);
            PourPreviewMID->SetScalarParameterValue(TEXT("FieldRadius"),Radii.Y);
        }
        CachedPreviewRadii=Radii;
    }
    if(PourPreviewDecal->bHiddenInGame)PourPreviewDecal->SetHiddenInGame(false);
}

void UVillageOilCarry::TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Tick,Fn);
    auto* P=Player();if(!P || !Occupied())return;
    if((P->HasAuthority() || P->IsLocallyControlled()) && HandsInUse())
    {Cancel();return;}
    if(P->HasAuthority() && State.Phase==EOilCarryPhase::Held && bPourQueued && Clock(GetWorld())-State.Since>=Raise)
        SetState(EOilCarryPhase::Pour);
    if(P->HasAuthority() && State.Phase==EOilCarryPhase::Pour)
    {
        const double Age=Clock(GetWorld())-State.Since;
        if(!bReleasedOil && Age>=Release)
        {
            bReleasedOil=true;
            FVector GroundPoint,GroundNormal;
            if(ResolvePourTarget(GroundPoint,GroundNormal))
            {
                const FTransform At(FRotator::ZeroRotator,GroundPoint);
                if(auto* Field=GetWorld()->SpawnActorDeferred<AVillageOilField>(AVillageOilField::StaticClass(),At,P,P,
                    ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
                {
                    const FVector BodyLip=PanPose(false,false).TransformPosition(VillageOilMotion::Lip);
                    Field->Lip=P->GetActorTransform().TransformPosition(BodyLip);
                    Field->FinishSpawning(At);
                }
            }
        }
        if(Age>=Finish){SetState(EOilCarryPhase::Empty);return;}
    }
    if(GetNetMode()!=NM_DedicatedServer && !bLocalCancel)
    {
        AdvanceLocomotionFeedback(Delta);
        UpdateVisual();
        UpdatePourPreview(Delta);
    }
}
void UVillageOilCarry::PrepareVisual()
{
    auto* P=Player();
    if(!PourPreviewMaterial)PourPreviewMaterial=Cast<UMaterialInterface>(FSoftObjectPath(MeteorSpellAssets::Preview).TryLoad());
    auto Make=[&](USceneComponent* Parent,UStaticMesh* Mesh,bool OwnerOnly)
    {
        auto* C=NewObject<UStaticMeshComponent>(P,NAME_None,RF_Transient);
        P->AddInstanceComponent(C);C->SetupAttachment(Parent);C->SetStaticMesh(Mesh);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);
        C->SetOnlyOwnerSee(OwnerOnly);C->SetCastShadow(!OwnerOnly);C->SetReceivesDecals(false);
        C->RegisterComponent();return C;
    };
    if(!WorldPot)
    {
        auto* Pot=Cast<UStaticMesh>(VillageHotOil::Asset(TEXT("SM_OilHandPot")).TryLoad());
        auto* Surface=Cast<UStaticMesh>(VillageHotOil::Asset(TEXT("SM_OilSurface")).TryLoad());
        WorldPot=Make(P->GetRootComponent(),Pot,false);WorldOil=Make(WorldPot,Surface,false);
        WorldOil->SetMaterial(0,VillageHotOil::BodyMaterial());
    }
    if(!ViewPot && P->IsLocallyControlled() && P->FirstPersonCamera)
    {
        ViewPot=Make(P->FirstPersonCamera,WorldPot->GetStaticMesh(),true);
        ViewOil=Make(ViewPot,WorldOil->GetStaticMesh(),true);
        ViewOil->SetMaterial(0,WorldOil->GetMaterial(0));
    }
    if(!P->IsLocallyControlled() || Arms || !P->FirstPersonCamera)return;
    auto* Rig=Cast<USkeletalMesh>(FSoftObjectPath(StaffGripPose::ArmsMeshPath).TryLoad());if(!Rig)return;
    Arms=NewObject<UVillageOilArmsMeshComponent>(P,TEXT("VillageOilArms"),RF_Transient);P->AddInstanceComponent(Arms);
    Arms->SetupAttachment(P->FirstPersonCamera);Arms->SetSkeletalMeshAsset(Rig);
    Arms->SetOnlyOwnerSee(true);Arms->SetOwnerNoSee(false);Arms->SetCastShadow(false);
    Arms->SetCanEverAffectNavigation(false);Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetReceivesDecals(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->SetVisibility(false);Arms->SetComponentTickEnabled(false);
    Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));Arms->RegisterComponent();
    const auto& Ref=Rig->GetRefSkeleton();
    VillageOilArmSolver::BuildBindPose(Ref,BindPose);
    for(int Side=0;Side<2;++Side)
    {
        TArray<FTransform> Sample;
        BaseContact[Side]=UWoodenTorchArmsComponent::BuildStaffCarry(*Rig,Side,Sample,INDEX_NONE);
        if(!Side)RestPose=Sample;
        int32 Clavicle=Ref.FindBoneIndex(Side?TEXT("clavicle_l"):TEXT("clavicle_r"));
        if(Clavicle==INDEX_NONE)continue;
        for(int32 I=Clavicle;I<Ref.GetNum();++I)if(I==Clavicle || Ref.BoneIsChildOf(I,Clavicle))
        {ArmBones.Add(I);RestPose[I]=Sample[I];}
    }
    if(const auto* Render=Rig->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
        {
            const auto& Sections=Render->LODRenderData[L].RenderSections;
            for(int32 S=0;S<Sections.Num();++S)
            {
                const int32 M=Sections[S].MaterialIndex;
                Arms->ShowMaterialSection(M,S,WeaponPresentationMaterials::IsArmSection(Rig->GetMaterials()[M]),L);
            }
        }
    if(auto* Outfit=P->FindComponentByClass<UFPSModularOutfitComponent>())
    {
        Outfit->RefreshInventory();
        Outfit->RefreshSources(true);
    }
}
void UVillageOilCarry::PrepareWorldGrip(USkeletalMesh* BodyMesh)
{
    if(!BodyMesh || WorldGripMesh.Get()==BodyMesh)return;
    auto* Native=Cast<USkeletalMesh>(FSoftObjectPath(StaffGripPose::ArmsMeshPath).TryLoad());
    if(!Native)return;
    WorldGripMesh=BodyMesh;
    VillageOilArmSolver::BuildBindPose(BodyMesh->GetRefSkeleton(),WorldBindPose);
    WorldFingerPose=BodyMesh->GetRefSkeleton().GetRefBonePose();
    for(int Side=0;Side<2;++Side)
    {
        const FName Hand=Side?TEXT("hand_l"):TEXT("hand_r");
        FFPSBodyGripRig Rig;
        Rig.Initialize(Native->GetRefSkeleton(),BodyMesh->GetRefSkeleton(),Hand,Hand);
        WorldFingers[Side].Reset();
        if(!Rig.IsValid())continue;
        TArray<FTransform> Sample;
        const FTransform Contact=UWoodenTorchArmsComponent::BuildStaffCarry(*Native,Side,Sample);
        WorldHandleInWrist[Side]=Contact*Rig.Mount;
        Rig.Transfer(Sample,WorldFingerPose);
        WorldFingers[Side]=Rig.Descendants;
    }
}
void UVillageOilCarry::UpdateVisual()
{
    const bool Show=Occupied() && !bLocalCancel;
    auto* P=Player();const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool WantsFirst=P->IsLocallyControlled() && P->FirstPersonCamera && !(Body && Body->IsThirdPersonViewEnabled());
    if(Show && WantsFirst && !ViewPot)PrepareVisual();
    const bool First=WantsFirst && ViewPot;
    if(Show && P->GetMesh())PrepareWorldGrip(P->GetMesh()->GetSkeletalMeshAsset());
    if(WorldPot){WorldPot->SetVisibility(Show);WorldPot->SetOwnerNoSee(First);WorldPot->SetRelativeTransform(PanPose(false,false));}
    const auto Pose=PanPose(true,true);
    if(ViewPot){ViewPot->SetVisibility(Show && First);ViewPot->SetRelativeTransform(Pose);}
    const double Age=Clock(GetWorld())-State.Since;
    const double Fill=State.Phase==EOilCarryPhase::Pour?VillageOilMotion::Fill(Age):1.;
    for(auto* Oil:{WorldOil.Get(),ViewOil.Get()})if(Oil)
    {
        Oil->SetVisibility(Show && Fill>0. && (Oil!=ViewOil || First));
        if(Oil==WorldOil)Oil->SetOwnerNoSee(First);
        // Level liquid intersecting a parabolic bowl has a displaced circular footprint in pan XY.
        // The camera rig follows the eyes; superimpose damped slosh for 1P locomotion without draining on look-down.
        const FQuat Vessel=Oil==ViewOil?Pose.GetRotation():Oil->GetAttachParent()->GetComponentQuat();
        FVector Up=Vessel.UnrotateVector(FVector::UpVector);
        if(Oil==ViewOil)
        {
            Up.X+=OilSlosh.X;
            Up.Y+=OilSlosh.Y;
        }
        Up.Z=FMath::Max(.42,Up.Z);Up.Normalize();
        const FVector2D Slope(-Up.X/Up.Z,-Up.Y/Up.Z);
        const FVector2D Center=(Slope*7.25).GetClampedToMaxSize(10.8);
        const double Radius=(12.88-Center.Size())*.94*FMath::Pow(Fill,.28);
        const double Height=-5.32+(Radius*Radius+Center.SizeSquared())*.069;
        const FVector2D Axis=Slope.IsNearlyZero()?FVector2D(1.,0.):Slope.GetSafeNormal();
        const FQuat Rot=FRotationMatrix::MakeFromZX(Up,FVector(Axis,Slope.Size())).ToQuat();
        Oil->SetRelativeLocationAndRotation(FVector(Center,Height),Rot);
        Oil->SetRelativeScale3D(FVector(Radius/(50.*Up.Z),Radius/50.,1.));
        if(Show)Oil->SetCustomPrimitiveDataFloat(0,GetWorld()->GetTimeSeconds());
    }
    if(!Arms)return;
    Arms->SetVisibility(Show && First);
    if(auto* Outfit=P->FindComponentByClass<UFPSModularOutfitComponent>())Outfit->RefreshVisibilityForSource(Arms);
    if(!Show || !First || RestPose.IsEmpty())return;
    const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();
    TArray<FTransform> Frame=RestPose;
    const bool Pouring=State.Phase==EOilCarryPhase::Pour;
    const double Tilt=Pouring?Tip(Age):0.;
    const double Push=Pouring?PushCurve(Age):0.;
    const double Load=Pouring?AnticipationCurve(Age):0.;
    for(int Side=0;Side<2;++Side)
    {
        const auto Wrist=BaseContact[Side].Inverse()*VillageOilArmSolver::Grip(Side,Tilt,Load)*Pose;
        // Natural lowered carry elbows below chest; right elbow rises and flares smoothly on pour thrust.
        const FVector Elbow(
            14.+6.*Push-3.*Load,
            Side?(-31.-2.*Load+2.*Tilt):(31.+10.*Tilt+4.*Push),
            Side?(-43.-2.*Load+5.*Tilt):(-43.-2.*Load+31.*Tilt+5.*Push));
        VillageOilArmSolver::SolveErgonomicArm(Ref,BindPose,Frame,Side,Wrist.GetLocation(),Elbow,Wrist.GetRotation(),Tilt,Push,Load);
    }
    Arms->CommitStationPose(Frame,ArmBones);
}
bool UVillageOilCarry::PourLip(FVector& WorldPoint) const
{
    if(State.Phase!=EOilCarryPhase::Pour || bLocalCancel || Clock(GetWorld())-State.Since>=VillageOilMotion::Empty)return false;
    const bool First=ViewPot && ViewPot->IsVisible();
    const auto* Parent=First?static_cast<const USceneComponent*>(Player()->FirstPersonCamera.Get()):Player()->GetRootComponent();
    if(!Parent)return false;
    WorldPoint=(PanPose(First,First)*Parent->GetComponentTransform()).TransformPosition(VillageOilMotion::Lip);
    return true;
}
void UVillageOilCarry::PoseWorldArms(USkeletalMeshComponent& Mesh,TArray<FTransform>& Pose) const
{
    if(!Occupied() || bLocalCancel || !Mesh.GetSkeletalMeshAsset() || Pose.IsEmpty())return;
    const auto Frame=PanPose(false,false)*Player()->GetActorTransform();
    const auto& Ref=Mesh.GetSkeletalMeshAsset()->GetRefSkeleton();
    const double Age=Clock(GetWorld())-State.Since;
    const bool Pouring=State.Phase==EOilCarryPhase::Pour;
    const double Tilt=Pouring?Tip(Age):0.;
    const double Push=Pouring?PushCurve(Age):0.;
    const double Load=Pouring?AnticipationCurve(Age):0.;
    for(int Side=0;Side<2;++Side)
    {
        if(WorldGripMesh.Get()!=Mesh.GetSkeletalMeshAsset() || WorldFingers[Side].IsEmpty())continue;
        const FTransform Wrist=(WorldHandleInWrist[Side].Inverse()*VillageOilArmSolver::Grip(Side,Tilt,Load)*Frame).GetRelativeTransform(Mesh.GetComponentTransform());
        const FVector Pole=Mesh.GetComponentTransform().InverseTransformPosition(
            Frame.TransformPosition(FVector(-14.+5.*Push-2.*Load,Side?-30.:30.+9.*Tilt+3.*Push,Side?-34.+4.*Tilt:-34.+28.*Tilt+4.*Push)));
        VillageOilArmSolver::SolveErgonomicArm(Ref,WorldBindPose,Pose,Side,Wrist.GetLocation(),Pole,Wrist.GetRotation(),Tilt,Push,Load);
        for(const int32 Bone:WorldFingers[Side])
            if(Pose.IsValidIndex(Bone))Pose[Bone]=WorldFingerPose[Bone]*Pose[Ref.GetParentIndex(Bone)];
    }
}
void UVillageOilCarry::HideFirstPersonEquipment(const AActor* ViewTarget,TSet<FPrimitiveComponentId>& Hidden) const
{
    const auto* P=Player();
    if(!Occupied() || bLocalCancel || ViewTarget!=P || !P->FirstPersonCamera)return;
    const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    const auto* Legs=Body?Body->GetFirstPersonLowerBodyMesh():nullptr;
    P->ForEachComponent<UPrimitiveComponent>(false,[&](UPrimitiveComponent* C){
        if((Legs && (C==Legs || C->IsAttachedTo(Legs))) || (Arms && C->IsAttachedTo(Arms)))return;
        if(C!=Arms && C!=ViewPot && C!=ViewOil && C->IsRegistered() &&
            (C->IsAttachedTo(P->FirstPersonCamera) || (C->bOnlyOwnerSee && !C->IsA<UCapsuleComponent>())))
            Hidden.Add(C->GetPrimitiveSceneId());
    });
}
void UVillageOilCarry::EndPlay(const EEndPlayReason::Type Reason)
{
    for(USceneComponent* C:{static_cast<USceneComponent*>(Arms.Get()),static_cast<USceneComponent*>(PourPreviewDecal.Get()),
        static_cast<USceneComponent*>(ViewOil.Get()),static_cast<USceneComponent*>(WorldOil.Get()),
        static_cast<USceneComponent*>(ViewPot.Get()),static_cast<USceneComponent*>(WorldPot.Get())})
        if(IsValid(C))C->DestroyComponent();
    Super::EndPlay(Reason);
}
