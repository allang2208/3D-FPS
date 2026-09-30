#include "WeaponBipodDeploymentComponent.h"
#include "LMG201WeaponAssets.h"
#include "PKMBipodComponent.h"
#include "PKMLowpolyWeaponAssets.h"
#include "WeaponHandling.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Engine/World.h"

namespace
{
constexpr double BipodHintInterval=.25;
constexpr double BipodSupportInterval=.12;

bool IsBipodSupport(const FHitResult& Hit)
{
    const auto* Component=Hit.GetComponent();
    return Hit.bBlockingHit && !Hit.bStartPenetrating && Component
        && !Cast<APawn>(Hit.GetActor()) && !Component->IsSimulatingPhysics()
        && Component->GetComponentVelocity().SizeSquared()<=4.;
}
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

void UWeaponBipodDeploymentComponent::FireDeployCue(bool bSeat)
{
    auto* C=Character.Get();if(!C||!GetWorld())return;
    // 复用 PKM 换弹处理弹链的两段录音：抬带（起手）与坐带咔哒（落位）。
    const FString Path=PKMLowpolyWeaponAssets::ReloadSoundPath(bSeat?TEXT("BeltSeat"):TEXT("BeltLift"));
    auto* Sound=LoadObject<USoundBase>(nullptr,*Path);
    if(!Sound){UE_LOG(LogTemp,Warning,TEXT("PKM bipod %s cue missing: %s"),bSeat?TEXT("seat"):TEXT("lift"),*Path);return;}
    const FVector At=C->FirstPersonCamera?C->FirstPersonCamera->GetComponentLocation():C->GetActorLocation()+FVector(0,0,90);
    UGameplayStatics::PlaySoundAtLocation(this,Sound,At,bSeat?1.28f:.75f,FMath::FRandRange(.96f,1.05f));
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
    if(!C || !C->bInventoryWeaponReady || (!PKMLowpolyWeaponAssets::Matches(C->AKMViewmodel)&&!LMG201WeaponAssets::Matches(C->AKMViewmodel)))return nullptr;
    auto* Part=Cast<UPKMBipodComponent>(PKMLowpolyWeaponAssets::FindBipod(C));
    return Part && Part->IsVisible() && !Part->bHiddenInGame ? Part : nullptr;
}

bool UWeaponBipodDeploymentComponent::Eligible() const
{
    const auto* C=Character.Get();
    if(!C || !C->IsLocallyControlled() || !GetWorld() || GetWorld()->GetNetMode()!=NM_Standalone)return false;
    const auto* PC=Cast<APlayerController>(C->GetController());
    if(!PC || AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    if(!EquippedBipod() || !C->GetCharacterMovement()->IsMovingOnGround() || C->GetVelocity().SizeSquared()>100.f)return false;
    if(C->GetWeaponState()!=EAKMWeaponState::Idle || C->IsChoosingAmmo() || C->bSprintHeld || C->IsSprinting()
        || C->IsSliding() || C->IsDodging() || C->IsTraversing() || C->IsCastBlockingLeftHandAction()
        || C->bGunsmithInspection)return false;
    // Actual velocity above determines whether the player is stationary. Holding
    // forward against a solid obstacle must not veto an otherwise valid mount.
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
    FSupport Hint;
    return FindSupport(Part,Hint,true);
}

bool UWeaponBipodDeploymentComponent::FindSupport(UPKMBipodComponent& Part,FSupport& Out,bool bHintOnly) const
{
    const auto* C=Character.Get();if(!C)return false;
    const FRotator Aim=C->GetControlRotation();
    if(FMath::Abs(FRotator::NormalizeAxis(Aim.Pitch))>40.f)return false;
    const FVector Forward=FRotator(0.,Aim.Yaw,0.).Vector();
    const FVector Right=FVector::CrossProduct(FVector::UpVector,Forward);
    const FVector Hinge=Part.GetHingeWorld();
    const FVector RestFeet[]={Part.GetRestFootWorld(0),Part.GetRestFootWorld(1)};
    const float Offsets[]={0.f,ForwardSearch*.5f,-ForwardSearch*.5f,ForwardSearch,-ForwardSearch};
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    // Use the collision that blocks the character for both acquisition and
    // retention. A simple hull and the visible mesh need not share the same top.
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodTopSurface),false,C);
    bool bFound=false;
    double BestCost=TNumericLimits<double>::Max();
    const auto TryFeet=[&](const FVector& First,const FVector& Second,float HeightRange)
    {
        const FVector Probes[]={First,Second};
        FSupport Candidate;
        for(int32 Leg=0;Leg<2;++Leg)
        {
            const FVector Probe=Probes[Leg];
            FHitResult Hit;
            // Start above the accepted height window so a top exactly on the
            // upper limit does not count as an initial overlap.
            if(!GetWorld()->LineTraceSingleByChannel(Hit,Probe+FVector::UpVector*(HeightRange+5.f),
                Probe-FVector::UpVector*HeightRange,SupportChannel,Params)
                || !IsBipodSupport(Hit) || Hit.ImpactNormal.Z<MinNormal
                || FMath::Abs(Hit.ImpactPoint.Z-RestFeet[Leg].Z)>HeightRange)return false;
            Candidate.Feet[Leg]=Hit.ImpactPoint+FVector::UpVector*.12;
            Candidate.Components[Leg]=Hit.GetComponent();
            Candidate.Transforms[Leg]=Hit.GetComponent()->GetComponentTransform();
            if(bHintOnly)continue;
            // Keep real support under both foot centers, but tolerate an edge
            // or a seam: two of four nearby samples are enough, and an adjacent
            // stationary component can carry part of the same sole.
            int32 SupportedEdges=0;
            for(const FVector& Side:{Right*1.2,-Right*1.2,Forward*1.2,-Forward*1.2})
            {
                FHitResult Edge;const FVector Center=Hit.ImpactPoint+Side;
                if(GetWorld()->LineTraceSingleByChannel(Edge,Center+FVector::UpVector*3.,Center-FVector::UpVector*3.,SupportChannel,Params)
                    && IsBipodSupport(Edge) && Edge.ImpactNormal.Z>=MinNormal)
                    if(++SupportedEdges>=2)break;
            }
            if(SupportedEdges<2)return false;
        }
        const FVector Delta=(Candidate.Feet[0]+Candidate.Feet[1]-RestFeet[0]-RestFeet[1])*.5;
        if(Delta.SizeSquared()>FMath::Square(MaximumCameraReach))return false;
        Candidate.Anchor=Hinge+Delta;
        const double Cost=Delta.SizeSquared();
        if(Cost<BestCost){BestCost=Cost;Out=Candidate;}
        bFound=true;return true;
    };
    for(const float Offset:Offsets)
    {
        if(TryFeet(RestFeet[0]+Forward*Offset,RestFeet[1]+Forward*Offset,MaximumHeightSnap) && bHintOnly)return true;
    }
    if(bFound)return true;

    // Search around the pawn, not only along the barrel: when aiming along a
    // wall, a forward ray is parallel to its face and cannot find close cover.
    const FVector FeetCenter=(RestFeet[0]+RestFeet[1])*.5;
    const FVector PawnLocation=C->GetActorLocation();
    const float CloseReach=C->GetCapsuleComponent()->GetScaledCapsuleRadius()+ForwardSearch;
    const float CloseHeightRange=MaximumHeightSnap*1.5f;
    const FVector Directions[]={Forward,Right,-Right,(Forward+Right).GetSafeNormal(),
        (Forward-Right).GetSafeNormal(),(-Forward+Right).GetSafeNormal(),
        (-Forward-Right).GetSafeNormal(),-Forward};
    TArray<FHitResult,TInlineAllocator<24>> NearFaces;
    for(const float HeightOffset:{-CloseHeightRange-2.f,0.f,CloseHeightRange*.5f})
    {
        FVector Start=PawnLocation;Start.Z=FeetCenter.Z+HeightOffset;
        for(const FVector& SearchDirection:Directions)
        {
            FHitResult Face;
            if(!GetWorld()->LineTraceSingleByChannel(Face,Start,Start+SearchDirection*CloseReach,SupportChannel,Params)
                || !IsBipodSupport(Face) || FMath::Abs(Face.ImpactNormal.Z)>.7f)continue;
            // Several directions/heights can hit the same wall plane. Keep
            // its nearest witness so those hits do not multiply top queries.
            FHitResult* Existing=NearFaces.FindByPredicate([&](const FHitResult& Other)
            {
                return Other.GetComponent()==Face.GetComponent()
                    && FVector::DotProduct(Other.ImpactNormal,Face.ImpactNormal)>.995
                    && FMath::Abs(FVector::DotProduct(Face.ImpactPoint-Other.ImpactPoint,Other.ImpactNormal))<1.;
            });
            if(!Existing)NearFaces.Add(Face);
            else if(FVector::DistSquared2D(Face.ImpactPoint,FeetCenter)<FVector::DistSquared2D(Existing->ImpactPoint,FeetCenter))
                *Existing=Face;
        }
    }
    NearFaces.StableSort([&](const FHitResult& A,const FHitResult& B)
    {
        return FVector::DistSquared2D(A.ImpactPoint,FeetCenter)<FVector::DistSquared2D(B.ImpactPoint,FeetCenter);
    });
    FVector HalfFeet=(RestFeet[0]-RestFeet[1])*.5;HalfFeet.Z=0.;
    for(const FHitResult& Face:NearFaces)
    {
        // Move into the obstacle along its normal, never along a grazing view
        // direction. First retain the actual foot span; if a narrow ledge
        // cannot carry that orientation, fit the same span along its edge.
        const FVector Inward=-FVector(Face.ImpactNormal.X,Face.ImpactNormal.Y,0.).GetSafeNormal();
        FVector AlongEdge=FVector::CrossProduct(FVector::UpVector,Inward);
        if(FVector::DotProduct(AlongEdge,HalfFeet)<0.)AlongEdge=-AlongEdge;
        const double PreferredAlong=FVector::DotProduct(FeetCenter-Face.ImpactPoint,AlongEdge);
        const double NearAlong=FMath::Clamp(PreferredAlong,-ForwardSearch*.5,ForwardSearch*.5);
        const FVector Spans[]={HalfFeet,AlongEdge*HalfFeet.Size()};
        for(const FVector& HalfSpan:Spans)
        {
            const double InnerMargin=FMath::Abs(FVector::DotProduct(HalfSpan,Inward));
            for(const double Along:{PreferredAlong,NearAlong,0.})
            {
                for(const float Inset:{2.f,6.f,12.f})
                {
                    const FVector Center=Face.ImpactPoint+AlongEdge*Along+Inward*(InnerMargin+Inset);
                    FVector First=Center+HalfSpan;First.Z=RestFeet[0].Z;
                    FVector Second=Center-HalfSpan;Second.Z=RestFeet[1].Z;
                    if(TryFeet(First,Second,CloseHeightRange))return true;
                }
            }
        }
    }
    // Support decides deployment. Camera/weapon clearance only limits the
    // presentation correction, using the same safe backoff as an existing mount.
    // A blocked correction must not make touching valid cover fail to deploy.
    return bFound;
}

bool UWeaponBipodDeploymentComponent::SupportStillValid(bool bProbeSurface) const
{
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodRetainSupport),false,GetOwner());
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
                || !IsBipodSupport(Hit) || Hit.GetComponent()!=Comp || Hit.ImpactNormal.Z<MinNormal
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
    PawnAnchor=C->GetActorLocation();bRequested=true;bCandidate=false;bSeatFired=false;
    NextSupportProbe=GetWorld()->GetTimeSeconds()+BipodSupportInterval;
    // Consume the input accumulated before the ADS event. Otherwise a held W
    // can move the pawn once more before the new movement lock takes effect.
    C->MoveInput=FVector2D::ZeroVector;
    C->ConsumeMovementInputVector();
    C->GetCharacterMovement()->StopMovementImmediately();
    FireDeployCue(false); // 抬弹链：架起动作的起手机械声
    SetComponentTickEnabled(true);return true;
}

void UWeaponBipodDeploymentComponent::Release(bool bImmediate)
{
    bRequested=false;bCandidate=false;bSeatFired=false;SettleClock=-1.f;
    if(auto* Part=Bipod.Get())Part->SetLegsFrozen(false); // 解除即恢复两腿自然摆动，防止冻结泄漏
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
    // 锁定兜底：击退等外力给到的速度每帧掐掉，角色钉在架设点（>2cm 位移仍走解除）。
    if(bRequested){if(auto* M=C->GetCharacterMovement();!M->Velocity.IsNearlyZero())M->StopMovementImmediately();}
    Blend=FMath::FInterpConstantTo(Blend,bRequested?1.f:0.f,DeltaSeconds,bRequested?1.f/.32f:1.f/.16f);
    // 完全落位的瞬间：坐弹链咔哒 + 起枪身衰减抖（表现"架在固体上"的沉降）。
    if(bRequested&&!bSeatFired&&Blend>=.999f){bSeatFired=true;SettleClock=0.f;FireDeployCue(true);}
    if(SettleClock>=0.f){SettleClock+=DeltaSeconds;if(SettleClock>.9f)SettleClock=-1.f;}
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
    const FVector Full=(Support.Anchor-Part->GetHingeWorld())*FMath::SmoothStep(0.f,1.f,Blend);
    const FVector Eye=C->FirstPersonCamera->GetComponentLocation();
    // 窗口内的视角旋转会带动枪体姿态：净空扫掠失败不是支撑失效，不能解除架枪
    // （解除只由 Advance 里的结构性检查负责）。先把校正量减半退让，仍不行这一帧
    // 干脆不平移，保持架设状态；两腿固定默认下垂，脚掌落点仅用于支撑判定。
    FVector Delta=Full;bool bPlaced=false;
    for(int32 Attempt=0;Attempt<4;++Attempt)
    {
        if(ClearPlacement(Eye,Delta,Part->GetHingeWorld()+Delta,C->GetEffectiveMuzzleForward(),bAfterPose)){bPlaced=true;break;}
        Delta*=.5f;
        if(Delta.IsNearlyZero(1.f)){Delta=FVector::ZeroVector;break;}
    }
    // Both camera moves need a fresh sweep: the second follows skeletal and
    // world physics updates. The weapon corridor is checked once, at the final
    // pose, instead of also querying the previous bone pose before firing.
    if(bPlaced && !Delta.IsNearlyZero())
    {
        const FVector Before=C->FirstPersonCamera->GetRelativeLocation();
        C->FirstPersonCamera->SetWorldLocation(Eye+Delta);
        AppliedCameraOffset=C->FirstPersonCamera->GetRelativeLocation()-Before;
    }
    // 2026-09-23 用户要求：架设期间不再对脚架做动画——两腿固定在默认下垂姿态，不随
    // 枪体旋转/平移解算接触点（穿模可接受）；解除后恢复正常摆动表现。
    Part->SetLegsFrozen(bRequested);
    if(!bRequested)Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);
    // 落位沉降抖：骨骼姿态与相机修正都定稿之后再叠加，只动枪身——两腿钉死在默认
    // 下垂，视觉上是枪体坐实在架点上，镜头与手臂不受扰。
    if(bAfterPose&&SettleClock>=0.f&&C->AKMViewmodel)
    {
        const float Decay=FMath::Exp(-SettleClock*7.5f);
        if(Decay>.01f)
            C->AKMViewmodel->AddRelativeRotation(FRotator(
                FMath::Sin(SettleClock*38.f)*Decay*1.8f,0.f,FMath::Sin(SettleClock*27.f+1.7f)*Decay*1.05f));
        else SettleClock=-1.f;
    }
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
