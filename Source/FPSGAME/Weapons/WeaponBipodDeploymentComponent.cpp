#include "WeaponBipodDeploymentComponent.h"
#include "PKMBipodComponent.h"
#include "PKMLowpolyWeaponAssets.h"
#include "WeaponHandling.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"

namespace
{
constexpr double BipodHintInterval=.25;
constexpr double BipodSupportInterval=.12;
}

UWeaponBipodDeploymentComponent::UWeaponBipodDeploymentComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
}

FWeaponHandling UWeaponBipodDeploymentComponent::ApplyStability(const FWeaponHandling& Base) const
{
    return Blend>0.f ? Base.WithStabilityMultiplier(FMath::Lerp(1.f,MountedStabilityMultiplier,Blend)) : Base;
}

void UWeaponBipodDeploymentComponent::BeginPlay()
{
    Super::BeginPlay();Character=Cast<AFPSGAMECharacter>(GetOwner());
    if(auto* C=Character.Get())
    {
        AddTickPrerequisiteActor(C);
        if(C->AKMViewmodel)AddTickPrerequisiteComponent(C->AKMViewmodel);
    }
}

void UWeaponBipodDeploymentComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Release(true);Character.Reset();Super::EndPlay(Reason);
}

UPKMBipodComponent* UWeaponBipodDeploymentComponent::EquippedBipod() const
{
    auto* C=Character.Get();
    if(!C || !C->bInventoryWeaponReady || !PKMLowpolyWeaponAssets::Matches(C->AKMViewmodel))return nullptr;
    auto* Part=Cast<UPKMBipodComponent>(PKMLowpolyWeaponAssets::FindBipod(C));
    return Part && Part->IsVisible() && !Part->bHiddenInGame ? Part : nullptr;
}

bool UWeaponBipodDeploymentComponent::Eligible() const
{
    const auto* C=Character.Get();
    if(!C || !C->IsLocallyControlled() || !GetWorld() || GetWorld()->GetNetMode()!=NM_Standalone)return false;
    const auto* PC=Cast<APlayerController>(C->GetController());
    if(!PC || AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    if(!EquippedBipod() || !C->GetCharacterMovement()->IsMovingOnGround() || C->GetVelocity().SizeSquared()>25.f)return false;
    if(C->GetWeaponState()!=EAKMWeaponState::Idle || C->IsChoosingAmmo() || C->bSprintHeld || C->IsSprinting()
        || C->IsSliding() || C->IsDodging() || C->IsTraversing() || C->IsCastBlockingLeftHandAction()
        || C->bGunsmithInspection || !C->MoveInput.IsNearlyZero(.05f))return false;
    if(const auto* Health=C->FindComponentByClass<UFPSCombatHealthComponent>();Health && Health->IsDead())return false;
    if(const auto* Body=C->FindComponentByClass<UFPSPlayerBodyComponent>();Body && Body->IsThirdPersonViewEnabled())return false;
    return true;
}

bool UWeaponBipodDeploymentComponent::ClearPlacement(const FVector& Eye,const FVector& Delta,
    const FVector& Hinge,const FVector& Forward,bool bCheckWeapon) const
{
    if(Delta.SizeSquared()>FMath::Square(MaximumCameraReach))return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodClearance),false,GetOwner());
    FHitResult Hit;
    if(GetWorld()->SweepSingleByChannel(Hit,Eye,Eye+Delta,FQuat::Identity,SupportChannel,
        FCollisionShape::MakeSphere(5.f),Params))return false;
    if(!bCheckWeapon)return true;
    // Preserve the barrel/receiver corridor. Feet may touch the obstacle, the
    // weapon above them may not be moved through it by the placement correction.
    return !GetWorld()->SweepSingleByChannel(Hit,Hinge-Forward*36.f,Hinge+Forward*30.f,
        FQuat::Identity,SupportChannel,FCollisionShape::MakeSphere(3.2f),Params);
}

bool UWeaponBipodDeploymentComponent::HasSupportHint(UPKMBipodComponent& Part) const
{
    const auto* C=Character.Get();if(!C)return false;
    const FRotator Aim=C->GetControlRotation();
    if(FMath::Abs(FRotator::NormalizeAxis(Aim.Pitch))>30.f)return false;
    const FVector Forward=FRotator(0.,Aim.Yaw,0.).Vector();
    const FVector Feet[]={Part.GetRestFootWorld(0),Part.GetRestFootWorld(1)};
    const float Offsets[]={0.f,ForwardSearch*.5f,-ForwardSearch*.5f,ForwardSearch,-ForwardSearch};
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    // Simple collision and foot centers only: at most ten short rays, often two.
    // No edge, reach or clearance checks until the player actually enters ADS.
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodSupportHint),false,C);
    for(const float Offset:Offsets)
    {
        bool Valid=true;
        for(const FVector& Foot:Feet)
        {
            const FVector Probe=Foot+Forward*Offset;
            FHitResult Hit;
            if(!GetWorld()->LineTraceSingleByChannel(Hit,Probe+FVector::UpVector*MaximumHeightSnap,
                Probe-FVector::UpVector*MaximumHeightSnap,SupportChannel,Params)
                || Hit.bStartPenetrating || Hit.ImpactNormal.Z<MinNormal || !Hit.GetComponent()
                || Cast<APawn>(Hit.GetActor()) || Hit.GetComponent()->IsSimulatingPhysics()
                || Hit.GetComponent()->GetComponentVelocity().SizeSquared()>1.){Valid=false;break;}
        }
        if(Valid)return true;
    }
    return false;
}

bool UWeaponBipodDeploymentComponent::FindSupport(UPKMBipodComponent& Part,FSupport& Out) const
{
    const auto* C=Character.Get();if(!C)return false;
    const FRotator Aim=C->GetControlRotation();
    if(FMath::Abs(FRotator::NormalizeAxis(Aim.Pitch))>30.f)return false;
    const FVector Forward=FRotator(0.,Aim.Yaw,0.).Vector();
    const FVector Right=FVector::CrossProduct(FVector::UpVector,Forward);
    const FVector Hinge=Part.GetHingeWorld();
    const FVector RestFeet[]={Part.GetRestFootWorld(0),Part.GetRestFootWorld(1)};
    const float Offsets[]={0.f,ForwardSearch*.5f,-ForwardSearch*.5f,ForwardSearch,-ForwardSearch};
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodTopSurface),true,C);
    struct FCandidate
    {
        FSupport Contact;
        FVector Delta;
        float Cost;
    };
    TArray<FCandidate,TInlineAllocator<5>> Candidates;
    for(const float Offset:Offsets)
    {
        FSupport Candidate;bool Valid=true;
        for(int32 Leg=0;Leg<2 && Valid;++Leg)
        {
            const FVector Probe=RestFeet[Leg]+Forward*Offset;
            FHitResult Hit;
            if(!GetWorld()->LineTraceSingleByChannel(Hit,Probe+FVector::UpVector*MaximumHeightSnap,
                Probe-FVector::UpVector*MaximumHeightSnap,SupportChannel,Params)
                || Hit.bStartPenetrating || Hit.ImpactNormal.Z<MinNormal || !Hit.GetComponent()
                || Cast<APawn>(Hit.GetActor()) || Hit.GetComponent()->IsSimulatingPhysics()
                || Hit.GetComponent()->GetComponentVelocity().SizeSquared()>1.){Valid=false;break;}
            Candidate.Feet[Leg]=Hit.ImpactPoint+FVector::UpVector*.12;
            Candidate.Components[Leg]=Hit.GetComponent();
            Candidate.Transforms[Leg]=Hit.GetComponent()->GetComponentTransform();
            // Confirm finite sole area so an edge or thin rail cannot support
            // a foot that would otherwise hang mostly in empty space.
            for(const FVector& Side:{Right*1.2,-Right*1.2,Forward*1.2,-Forward*1.2})
            {
                FHitResult Edge;const FVector Center=Hit.ImpactPoint+Side;
                if(!GetWorld()->LineTraceSingleByChannel(Edge,Center+FVector::UpVector*2.,Center-FVector::UpVector*2.,SupportChannel,Params)
                    || Edge.GetComponent()!=Hit.GetComponent() || Edge.ImpactNormal.Z<MinNormal){Valid=false;break;}
            }
        }
        if(!Valid)continue;
        const FVector Delta=(Candidate.Feet[0]+Candidate.Feet[1]-RestFeet[0]-RestFeet[1])*.5;
        Candidate.Anchor=Hinge+Delta;
        if(!Part.CanReachContacts(Candidate.Feet[0],Candidate.Feet[1],Delta))continue;
        const float Cost=static_cast<float>(Delta.SizeSquared())+FMath::Abs(Offset)*2.f;
        Candidates.Add(FCandidate{Candidate,Delta,Cost});
    }
    // Preserve the minimum-correction choice, but sweep the cheapest candidate
    // first and stop on success. Do not sweep all five clear placements.
    Candidates.StableSort([](const FCandidate& A,const FCandidate& B){return A.Cost<B.Cost;});
    for(const FCandidate& Candidate:Candidates)
        if(ClearPlacement(C->FirstPersonCamera->GetComponentLocation(),Candidate.Delta,
            Candidate.Contact.Anchor,C->GetEffectiveMuzzleForward()))
        {Out=Candidate.Contact;return true;}
    return false;
}

bool UWeaponBipodDeploymentComponent::SupportStillValid(bool bProbeSurface) const
{
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodRetainSupport),true,GetOwner());
    for(int32 Leg=0;Leg<2;++Leg)
    {
        const auto* Comp=Support.Components[Leg].Get();
        if(!Comp || !Comp->IsRegistered() || Comp->GetCollisionEnabled()==ECollisionEnabled::NoCollision
            || Comp->GetCollisionResponseToChannel(SupportChannel)!=ECR_Block || Comp->IsSimulatingPhysics())return false;
        const FTransform Now=Comp->GetComponentTransform();
        if(!Now.GetLocation().Equals(Support.Transforms[Leg].GetLocation(),.5)
            || Now.GetRotation().AngularDistance(Support.Transforms[Leg].GetRotation())>.0087
            || !Now.GetScale3D().Equals(Support.Transforms[Leg].GetScale3D(),.001))return false;
        if(bProbeSurface)
        {
            FHitResult Hit;
            if(!GetWorld()->LineTraceSingleByChannel(Hit,Support.Feet[Leg]+FVector::UpVector*2.,
                Support.Feet[Leg]-FVector::UpVector*2.,SupportChannel,Params)
                || Hit.GetComponent()!=Comp || Hit.ImpactNormal.Z<MinNormal
                || FVector::DistSquared(Hit.ImpactPoint,Support.Feet[Leg])>1.)return false;
        }
    }
    return true;
}

void UWeaponBipodDeploymentComponent::ClampAim() const
{
    const auto* C=Character.Get();if(!C || !C->Controller)return;
    FRotator Aim=C->Controller->GetControlRotation();
    Aim.Yaw=InitialAim.Yaw+FMath::Clamp(FMath::FindDeltaAngleDegrees(InitialAim.Yaw,Aim.Yaw),-YawLimitDegrees,YawLimitDegrees);
    Aim.Pitch=InitialAim.Pitch+FMath::Clamp(FMath::FindDeltaAngleDegrees(InitialAim.Pitch,Aim.Pitch),-PitchLimitDegrees,PitchLimitDegrees);
    Aim.Roll=0.;C->Controller->SetControlRotation(Aim);
}

bool UWeaponBipodDeploymentComponent::TryDeployFromADS()
{
    auto* C=Character.Get();auto* Part=EquippedBipod();
    if(!Eligible() || !C || !C->bIsAiming || C->bFireHeld || !Part)return false;
    if(bRequested)return true;
    // A quick release/re-aim is another deliberate ADS entry. Finish the old
    // release before measuring new support instead of losing that input.
    if(Blend>UE_SMALL_NUMBER)Release(true);
    RestoreCameraOffset();FSupport Candidate;
    if(!FindSupport(*Part,Candidate)){bCandidate=false;return false;}
    Bipod=Part;Support=Candidate;InitialAim=C->GetControlRotation();InitialAim.Pitch=FRotator::NormalizeAxis(InitialAim.Pitch);
    PawnAnchor=C->GetActorLocation();bRequested=true;bCandidate=false;
    NextSupportProbe=GetWorld()->GetTimeSeconds()+BipodSupportInterval;
    C->GetCharacterMovement()->StopMovementImmediately();
    SetComponentTickEnabled(true);return true;
}

void UWeaponBipodDeploymentComponent::Release(bool bImmediate)
{
    bRequested=false;bCandidate=false;
    if(bImmediate)
    {
        Blend=0.f;RestoreCameraOffset();
        if(auto* Part=Bipod.Get())Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);
        Bipod.Reset();SetComponentTickEnabled(false);
    }
}

void UWeaponBipodDeploymentComponent::Advance(float DeltaSeconds)
{
    auto* C=Character.Get();if(!C)return;
    const bool Allowed=Eligible();const double Now=GetWorld()->GetTimeSeconds();
    const bool Probe=bRequested && Now>=NextSupportProbe;
    if(Probe)NextSupportProbe=Now+BipodSupportInterval;
    if(bRequested && (!Allowed || !C->bIsAiming || Bipod.Get()!=EquippedBipod()
        || FVector::DistSquared(C->GetActorLocation(),PawnAnchor)>4. || !SupportStillValid(Probe)))Release();
    if(bRequested)ClampAim();
    Blend=FMath::FInterpConstantTo(Blend,bRequested?1.f:0.f,DeltaSeconds,bRequested?1.f/.32f:1.f/.16f);
    if(!bRequested && Blend<=UE_SMALL_NUMBER)
    {
        if(Bipod.IsValid() || !AppliedCameraOffset.IsNearlyZero())Release(true);
        if(Allowed && Now>=NextHintProbe)
        {
            NextHintProbe=Now+BipodHintInterval;
            if(auto* Part=EquippedBipod())bCandidate=HasSupportHint(*Part);
            else bCandidate=false;
        }
    }
    if(!Allowed)bCandidate=false;
    SetComponentTickEnabled(Blend>UE_SMALL_NUMBER || bRequested);
}

void UWeaponBipodDeploymentComponent::RestoreCameraOffset()
{
    if(auto* C=Character.Get();C && C->FirstPersonCamera && !AppliedCameraOffset.IsNearlyZero())
        C->FirstPersonCamera->SetRelativeLocation(C->FirstPersonCamera->GetRelativeLocation()-AppliedCameraOffset);
    AppliedCameraOffset=FVector::ZeroVector;
}

void UWeaponBipodDeploymentComponent::ApplyPresentation(bool bAfterPose)
{
    RestoreCameraOffset();auto* C=Character.Get();auto* Part=Bipod.Get();
    if(Blend<=UE_SMALL_NUMBER && !bRequested)return;
    if(!C || !Part || Part!=EquippedBipod()){Release(true);return;}
    if(Blend<=UE_SMALL_NUMBER)return;
    if(bRequested && (!C->bIsAiming || !Eligible()))Release();
    const FVector Delta=(Support.Anchor-Part->GetHingeWorld())*FMath::SmoothStep(0.f,1.f,Blend);
    const FVector Eye=C->FirstPersonCamera->GetComponentLocation();
    // Both camera moves need a fresh sweep: the second follows skeletal and
    // world physics updates. The weapon corridor is checked once, at the final
    // pose, instead of also querying the previous bone pose before firing.
    if(!ClearPlacement(Eye,Delta,Part->GetHingeWorld()+Delta,C->GetEffectiveMuzzleForward(),bAfterPose)
        || (bRequested && !Part->CanReachContacts(Support.Feet[0],Support.Feet[1],Support.Anchor-Part->GetHingeWorld())))
    {Release(true);return;}
    // Translate camera and the complete arms/weapon hierarchy together. This
    // pins the measured hinge while retaining ADS alignment and hand contacts.
    const FVector Before=C->FirstPersonCamera->GetRelativeLocation();
    C->FirstPersonCamera->SetWorldLocation(Eye+Delta);
    AppliedCameraOffset=C->FirstPersonCamera->GetRelativeLocation()-Before;
    Part->SetDeploymentContacts(Support.Feet[0],Support.Feet[1],FMath::SmoothStep(0.f,1.f,Blend));
}

void UWeaponBipodDeploymentComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(DeltaTime,TickType,Tick);ApplyPresentation(true);
}

EWeaponBipodDeploymentState UWeaponBipodDeploymentComponent::GetDeploymentState() const
{
    if(bRequested)return IsDeployed()?EWeaponBipodDeploymentState::Deployed:EWeaponBipodDeploymentState::Deploying;
    if(Blend>UE_SMALL_NUMBER)return EWeaponBipodDeploymentState::Releasing;
    return bCandidate?EWeaponBipodDeploymentState::Available:EWeaponBipodDeploymentState::Unavailable;
}

FString UWeaponBipodDeploymentComponent::GetHint() const
{
    if(!EquippedBipod())return FString();
    if(bRequested)return IsDeployed()?TEXT("脚架已部署 · 取消瞄准解除")
        :TEXT("脚架部署中 · 取消瞄准解除");
    if(Blend>UE_SMALL_NUMBER)return TEXT("正在解除架设");
    if(bCandidate)
        return Character.IsValid() && Character->bIsAiming ? TEXT("附近有支撑面 · 重新瞄准尝试架枪")
            :TEXT("附近有支撑面 · 瞄准尝试架枪");
    return TEXT("脚架：靠近箱体、矮墙或窗台");
}

FString AFPSGAMECharacter::GetBipodDeploymentHint() const
{
    return BipodDeployment?BipodDeployment->GetHint():FString();
}
