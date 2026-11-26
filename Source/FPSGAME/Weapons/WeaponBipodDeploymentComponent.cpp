#include "WeaponBipodDeploymentComponent.h"
#include "LMG201WeaponAssets.h"
#include "M249WeaponAssets.h"
#include "M249Bipod.h"
#include "M249BipodAnimation.h"
#include "M24Bipod.h"
#include "M24WeaponAssets.h"
#include "M24Attachments.h"
#include "WeaponGripProfile.h"
#include "FPSGunplayAnimInstance.h"
#include "GunsmithSystem.h"
#include "PKMBipodComponent.h"
#include "PKMLowpolyWeaponAssets.h"
#include "WeaponHandling.h"
#include "PKMBipodContacts.h"
#include "../Building/VoxelBuildGrounding.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"
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

// A stance change adds only vertical travel; lateral reach stays bounded.
bool WithinBipodReach(FVector Offset,double Reach,double Lowering,double Rising)
{
    if(Offset.Z<0.)Offset.Z=FMath::Min(0.,Offset.Z+Lowering);
    else Offset.Z=FMath::Max(0.,Offset.Z-Rising);
    return Offset.SizeSquared()<=FMath::Square(Reach);
}

bool CanSeeBipodContact(UWorld& World,const FVector& Eye,const FVector& Contact,
    double MaxRise,ECollisionChannel Channel,const FCollisionQueryParams& Params)
{
    const FVector Above=Contact+FVector::UpVector*4.;
    FHitResult Block;
    if(!World.LineTraceSingleByChannel(Block,Eye,Above,Channel,Params))return true;
    // From a crouch the near lip may hide its own top. The camera must have a
    // clear path up and the raised eye must see the contact over the lip.
    const double Rise=Above.Z-Eye.Z;
    if(Rise<=0.||Rise>MaxRise)return false;
    const FVector RaisedEye(Eye.X,Eye.Y,Above.Z);
    return !World.SweepSingleByChannel(Block,Eye,RaisedEye,FQuat::Identity,Channel,FCollisionShape::MakeSphere(5.f),Params)
        &&!World.LineTraceSingleByChannel(Block,RaisedEye,Above,Channel,Params);
}

bool FeetShareSurface(const FVector& A,const FVector& B,float SlopeDegrees)
{
    const double Rise=FVector::Dist2D(A,B)*FMath::Tan(FMath::DegreesToRadians(SlopeDegrees));
    return FMath::Abs(A.Z-B.Z)<=Rise+3.; // allow seams, not two different tiers of a parapet
}

bool BipodPartInstalled(const FString& Definition,const FString& Part)
{
    if(Definition==M249WeaponAssets::Definition)return M249WeaponAssets::HasFactoryBipod(Part);
    return Definition==M24WeaponAssets::Definition?Part==M24Bipod::Id:
        Definition==PKMLowpolyWeaponAssets::Definition?Part==TEXT("pkm_bipod"):
        Definition==LMG201WeaponAssets::Definition&&LMG201WeaponAssets::HasFactoryBipod(Part);
}

bool IsBipodSupport(const FHitResult& Hit)
{
    // Damageable village defenses are pawns. Their masonry and portal frame
    // carry the fixed-structure tag; the portcullis and moving gate leaves do not.
    return Hit.bBlockingHit && !Hit.bStartPenetrating && VoxelGrounding::IsFixedBuildingSurface(Hit)
        && Hit.GetComponent()->GetComponentVelocity().SizeSquared()<=4.;
}

bool HasBipodFootArea(UWorld& World,const FVector& Contact,float MinNormal,
    ECollisionChannel Channel,const FCollisionQueryParams& Params)
{
    int32 Edges=0;
    for(const FVector& Offset:{FVector(1.2,0,0),FVector(-1.2,0,0),FVector(0,1.2,0),FVector(0,-1.2,0)})
    {
        FHitResult Edge;
        const FVector At=Contact+Offset;
        if(World.LineTraceSingleByChannel(Edge,At+FVector::UpVector*3.,At-FVector::UpVector*3.,Channel,Params)
            &&IsBipodSupport(Edge)&&Edge.ImpactNormal.Z>=MinNormal&&++Edges>=2)return true;
    }
    return false;
}
}

UWeaponBipodDeploymentComponent::UWeaponBipodDeploymentComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
}

bool UWeaponBipodDeploymentComponent::IsM24() const
{
    const auto* C=Character.Get();
    return C&&(C->IsLocallyControlled()?C->IsM24Weapon():EquippedDefinition()==M24WeaponAssets::Definition);
}

bool UWeaponBipodDeploymentComponent::HasHandDeployment() const
{
    const auto* C=Character.Get();
    return IsM24()||(C&&(C->IsLocallyControlled()?C->ActiveInventoryWeaponDefinition==M249WeaponAssets::Definition
        :EquippedDefinition()==M249WeaponAssets::Definition));
}

float UWeaponBipodDeploymentComponent::TransitionDuration(bool bDeploy) const
{return IsM24()?M24Bipod::Duration:HasHandDeployment()?M249BipodAnimation::Duration:(bDeploy?.32f:.16f);}

float UWeaponBipodDeploymentComponent::PlacementBlend() const
{return HasHandDeployment()?M24Bipod::Seat(Blend):Blend;}

float UWeaponBipodDeploymentComponent::AimPresentationWeight() const
{return HasHandDeployment()&&(bRequested||Blend>UE_SMALL_NUMBER)?PlacementBlend():1.f;}

bool UWeaponBipodDeploymentComponent::BlocksFire() const
{return (bRequested||(HasHandDeployment()&&Blend>UE_SMALL_NUMBER))&&!IsDeployed();}

void UWeaponBipodDeploymentComponent::ApplyHandPose(UFPSGunplayAnimInstance& Animation) const
{
    const auto* C=Character.Get();
    if(!HasHandDeployment()||!C||Blend<=UE_SMALL_NUMBER||Blend>=.9999f||C->WeaponState!=EAKMWeaponState::Idle)return;
    const auto* Entry=C->WeaponGripProfiles.Find(TEXT("bipod"));
    auto* Profile=Entry?Entry->Get():nullptr;
    const int32 Index=IsM24()&&C->MagazineAttachmentId==M24Attachments::ExtendedMagazine?1:0;
    if(!Profile||!Profile->Clips.IsValidIndex(Index))return;
    Animation.ActionClip=Profile->Clips[Index].Playback();
    Animation.ActionTime=Blend*M24Bipod::PoseDuration;
    Animation.ActionAlpha=M24Bipod::Ease(0.f,.025f,Animation.ActionTime)
        *(1.f-M24Bipod::Ease(.44f,M24Bipod::PoseDuration,Animation.ActionTime));
    // M24 keeps its grip-family deltas. M249 contains its native grip,
    // complete arms and weapon pullback in one reversible sequence.
    Animation.ActionGripProfile=IsM24()?Animation.GripProfile.Get():Profile;
    if(M249WeaponAssets::Matches(C->AKMViewmodel)&&Animation.GripProfile
        &&Animation.GripProfile->Find(Profile->Clips[Index].Base))
        Animation.ActionGripProfile=Animation.GripProfile;
    Animation.bGripAction=false;Animation.bGripActionAim=false;
}

bool UWeaponBipodDeploymentComponent::DeferReload()
{
    auto* C=Character.Get();if(!HasHandDeployment()||!C||(!bRequested&&Blend<=UE_SMALL_NUMBER))return false;
    // The left hand finishes folding before it becomes the magazine hand.
    C->bAimHeld=false;C->SetAimingState(false);Release();
    PendingReloadWeapon=C->ActiveInventoryWeapon;bPendingReaim=false;
    return true;
}

FWeaponHandling UWeaponBipodDeploymentComponent::ApplyStability(const FWeaponHandling& Base) const
{
    const float Weight=HandlingBlend();
    return Weight>0.f ? Base.WithStabilityMultiplier(FMath::Lerp(1.f,MountedStabilityMultiplier,Weight)) : Base;
}

void UWeaponBipodDeploymentComponent::FireDeployCue(bool bSeat)
{
    auto* C=Character.Get();if(!C||!GetWorld())return;
    if(HasHandDeployment())
    {
        // Cached weapon mechanical clicks share the hand/hinge clock.
        USoundBase* Sound=bSeat?C->MagSeatSound.Get():C->MagOutSound.Get();
        if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound,C->FirstPersonCamera->GetComponentLocation(),bSeat?.42f:.25f,1.12f);
        return;
    }
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
    if(!C || !C->bInventoryWeaponReady || (!PKMLowpolyWeaponAssets::Matches(C->AKMViewmodel)&&!LMG201WeaponAssets::Matches(C->AKMViewmodel)&&!M24Bipod::Matches(C->AKMViewmodel)&&!M249WeaponAssets::Matches(C->AKMViewmodel)))return nullptr;
    auto* Part=Cast<UPKMBipodComponent>(PKMLowpolyWeaponAssets::FindBipod(C));
    return Part && Part->IsVisible() && !Part->bHiddenInGame ? Part : nullptr;
}

bool UWeaponBipodDeploymentComponent::Eligible(bool bContinuing) const
{
    const auto* C=Character.Get();
    if(!C || !C->IsLocallyControlled() || !GetWorld())return false;
    const auto* PC=Cast<APlayerController>(C->GetController());
    if(!PC || (bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC)))return false;
    if(const auto* Push=C->FindComponentByClass<UFPSDoorPushComponent>();Push&&Push->IsActive())return false;
    if(!EquippedBipod() || !C->GetCharacterMovement()->IsMovingOnGround() || C->GetVelocity().SizeSquared()>100.f)return false;
    if(C->GetWeaponState()!=EAKMWeaponState::Idle || C->IsChoosingAmmo() || C->bSprintHeld || C->IsSprinting()
        || C->IsSliding() || C->IsDodging() || C->IsTraversing() || C->IsCastBlockingLeftHandAction()
        || C->bGunsmithInspection)return false;
    // Actual velocity above determines whether the player is stationary. Holding
    // forward against a solid obstacle must not veto an otherwise valid mount.
    if(const auto* Health=C->FindComponentByClass<UFPSCombatHealthComponent>();Health && Health->IsDead())return false;
    return true;
}

bool UWeaponBipodDeploymentComponent::ClearPlacement(const FVector& Eye,const FVector& Delta,
    const FVector& Hinge,const FVector& Forward,bool bCheckWeapon) const
{
    const auto* C=Character.Get();
    if(!WithinBipodReach(Delta,MaximumCameraReach,StanceAdjustment,C&&C->bIsCrouched?StanceAdjustment:0.f))return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodClearance),false,GetOwner());
    FHitResult Hit;
    const auto Camera=FCollisionShape::MakeSphere(5.f);
    if(GetWorld()->SweepSingleByChannel(Hit,Eye,Eye+Delta,FQuat::Identity,SupportChannel,Camera,Params))
    {
        // Match the raised sightline at a parapet: rise past the lip before
        // translating across it. Both segments must clear the camera sphere.
        const FVector LiftedEye=Eye+FVector::UpVector*Delta.Z;
        if(Delta.Z<=0.||GetWorld()->SweepSingleByChannel(Hit,Eye,LiftedEye,FQuat::Identity,SupportChannel,Camera,Params)
            ||GetWorld()->SweepSingleByChannel(Hit,LiftedEye,Eye+Delta,FQuat::Identity,SupportChannel,Camera,Params))return false;
    }
    if(!bCheckWeapon)return true;
    // Preserve the barrel/receiver corridor. Feet may touch the obstacle, the
    // weapon above them may not be moved through it by the placement correction.
    const FVector Center=Hinge+(IsM24()?FVector::UpVector*(11.4-M24Bipod::Hinge.Z):FVector::ZeroVector);
    return !GetWorld()->SweepSingleByChannel(Hit,Center-Forward*(IsM24()?65.f:36.f),Center+Forward*(IsM24()?70.f:30.f),
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
    const FVector Forward=FRotator(0.,Aim.Yaw,0.).Vector();
    const FVector Right=FVector::CrossProduct(FVector::UpVector,Forward);
    // Unpitch the actual weapon geometry into the pawn's level eye frame.
    // Looking up/down must not move the search band, shorten its horizontal
    // reach or put the bipod probes behind the cover. Keep the real foot span
    // and the current stance, but exclude camera bob and old mount offsets.
    const FTransform CameraFrame=C->FirstPersonCamera->GetComponentTransform();
    const FTransform LevelFrame(FRotator(0.,Aim.Yaw,0.),C->GetMeleeAimTransform().GetLocation());
    const auto LevelPoint=[&](const FVector& WorldPoint)
    { return LevelFrame.TransformPosition(CameraFrame.InverseTransformPosition(WorldPoint)); };
    const FVector Hinge=LevelPoint(Part.GetHingeWorld());
    const FVector RestFeet[]={LevelPoint(Part.GetRestFootWorld(0)),LevelPoint(Part.GetRestFootWorld(1))};
    const FVector FeetCenter=(RestFeet[0]+RestFeet[1])*.5;
    const auto* Capsule=C->GetCapsuleComponent();
    const double FloorZ=Capsule->GetComponentLocation().Z-Capsule->GetScaledCapsuleHalfHeight();
    const float SearchHeightRange=FMath::Min(MaximumHeightSnap,MaximumCameraReach);
    const float Rising=C->bIsCrouched?StanceAdjustment:0.f;
    const float Offsets[]={0.f,ForwardSearch*.5f,-ForwardSearch*.5f,ForwardSearch,-ForwardSearch};
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    // Use the collision that blocks the character for both acquisition and
    // retention. A simple hull and the visible mesh need not share the same top.
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BipodTopSurface),false,C);
    bool bFound=false;
    double BestCost=TNumericLimits<double>::Max();
    const auto TryFeet=[&](const FVector& First,const FVector& Second,float HeightRange,
        double Turn=0.,bool bRaisedOnly=false)
    {
        const FVector Probes[]={First,Second};
        FSupport Candidate;
        for(int32 Leg=0;Leg<2;++Leg)
        {
            const FVector Probe=Probes[Leg];
            FHitResult Hit;
            // Start above the accepted height window so a top exactly on the
            // upper limit does not count as an initial overlap.
            if(!GetWorld()->LineTraceSingleByChannel(Hit,Probe+FVector::UpVector*(HeightRange+Rising+5.f),
                Probe-FVector::UpVector*(HeightRange+StanceAdjustment),SupportChannel,Params)
                || !IsBipodSupport(Hit) || Hit.ImpactNormal.Z<MinNormal)return false;
            const bool Raised=Hit.ImpactPoint.Z>FloorZ+5.;
            const double Height=Hit.ImpactPoint.Z-RestFeet[Leg].Z;
            if((bRaisedOnly&&!Raised)||Height>HeightRange+(Raised?Rising:0.f)
                ||Height<-(HeightRange+(Raised?StanceAdjustment:0.f)))return false;
            Candidate.Feet[Leg]=Hit.ImpactPoint+FVector::UpVector*.12;
            Candidate.Components[Leg]=Hit.GetComponent();
            Candidate.Transforms[Leg]=Hit.GetComponent()->GetComponentTransform();
            // Match the authority's contact visibility check for every weapon.
            // This is support occlusion, not the presentation's gun/camera sweep.
            if(!CanSeeBipodContact(*GetWorld(),LevelFrame.GetLocation(),Hit.ImpactPoint,
                MaximumCameraReach+Rising,SupportChannel,Params))return false;
            if(bHintOnly)continue;
            // Keep real support under both foot centers, but tolerate an edge
            // or a seam: two of four nearby samples are enough, and an adjacent
            // stationary component can carry part of the same sole.
            if(!HasBipodFootArea(*GetWorld(),Hit.ImpactPoint,MinNormal,SupportChannel,Params))return false;
        }
        if(!FeetShareSurface(Candidate.Feet[0],Candidate.Feet[1],MaximumSlopeDegrees))return false;
        const FVector ContactCenter=(Candidate.Feet[0]+Candidate.Feet[1])*.5;
        const bool Raised=FMath::Min(Candidate.Feet[0].Z,Candidate.Feet[1].Z)>FloorZ+5.;
        const double Lowering=Raised?StanceAdjustment:0.;
        const double Lift=Raised?Rising:0.;
        FVector Delta=ContactCenter-FeetCenter;
        FQuat MountTurn=FQuat::Identity;
        if(WithinBipodReach(Delta,MaximumCameraReach,Lowering,Lift))Turn=0.;
        else
        {
            if(FMath::IsNearlyZero(Turn))return false;
            const FVector Eye=LevelFrame.GetLocation();
            MountTurn=FQuat(FVector::UpVector,FMath::DegreesToRadians(Turn));
            Delta=ContactCenter-(Eye+MountTurn.RotateVector(FeetCenter-Eye));
            if(!WithinBipodReach(Delta,MaximumCameraReach,Lowering,Lift))return false;
        }
        Candidate.Anchor=ContactCenter+MountTurn.RotateVector(Hinge-FeetCenter);
        Candidate.MountYaw=FRotator::NormalizeAxis(Aim.Yaw+Turn);
        // All rifles use physical support to acquire the mount. Leg IK limits
        // and gun/camera clearance only affect presentation, never eligibility.
        const double Cost=Delta.SizeSquared();
        if(Cost<BestCost){BestCost=Cost;Out=Candidate;}
        bFound=true;return true;
    };
    for(const float Offset:Offsets)
    {
        if(TryFeet(RestFeet[0]+Forward*Offset,RestFeet[1]+Forward*Offset,SearchHeightRange) && bHintOnly)return true;
    }
    if(bFound)return true;

    // Search around the pawn, not only along the barrel: when aiming along a
    // wall, a forward ray is parallel to its face and cannot find close cover.
    const FVector PawnLocation=C->GetActorLocation();
    const float CloseReach=Capsule->GetScaledCapsuleRadius()+ForwardSearch;
    const float CloseHeightRange=FMath::Min(MaximumHeightSnap*1.5f,MaximumCameraReach);
    const double SearchBottom=FloorZ+5.;
    const double SearchTop=FeetCenter.Z+CloseHeightRange+Rising+5.;
    const double RadiusLimit=CloseReach+ForwardSearch+5.;
    if(SearchTop<=SearchBottom || !GetWorld()->OverlapBlockingTestByChannel(
        FVector(PawnLocation.X,PawnLocation.Y,(SearchBottom+SearchTop)*.5),FQuat::Identity,SupportChannel,
        FCollisionShape::MakeBox(FVector(RadiusLimit,RadiusLimit,(SearchTop-SearchBottom)*.5)),Params))return false;
    // A sill under a crenel can be below every horizontal face trace. Probe
    // down around the pawn in fixed world sectors, starting nearest the view.
    // Measure reach in the prospective mounted pose even if the player enters
    // ADS facing across the wall or away from it.
    constexpr int32 Sectors=16;
    constexpr double Step=360./Sectors;
    const int32 StartSector=FMath::RoundToInt(Aim.Yaw/Step);
    for(int32 Index=0;Index<Sectors;++Index)
    {
        const int32 Side=(Index%2==0)?-Index/2:(Index+1)/2;
        const double Yaw=(StartSector+Side)*Step;
        const double Turn=FMath::FindDeltaAngleDegrees(double(Aim.Yaw),Yaw);
        const FVector Direction=FRotator(0.,Yaw,0.).Vector();
        const FVector HalfSpan=((RestFeet[0]-RestFeet[1])*.5).RotateAngleAxis(Turn,FVector::UpVector);
        for(double Radius:{double(Capsule->GetScaledCapsuleRadius())+5.,double(CloseReach)+5.,double(CloseReach)+ForwardSearch+5.})
        {
            FVector Center=PawnLocation+Direction*Radius;Center.Z=FeetCenter.Z;
            if(TryFeet(Center+HalfSpan,Center-HalfSpan,SearchHeightRange,Turn,true))return true;
        }
    }
    const FVector Directions[]={Forward,Right,-Right,(Forward+Right).GetSafeNormal(),
        (Forward-Right).GetSafeNormal(),(-Forward+Right).GetSafeNormal(),
        (-Forward-Right).GetSafeNormal(),-Forward};
    TArray<FHitResult,TInlineAllocator<24>> NearFaces;
    for(const double SampleZ:{FloorZ+12.,FeetCenter.Z-CloseHeightRange-2.,FeetCenter.Z,FeetCenter.Z+CloseHeightRange*.5})
    {
        FVector Start=PawnLocation;Start.Z=SampleZ;
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
        const double Turn=FMath::FindDeltaAngleDegrees(double(Aim.Yaw),Inward.Rotation().Yaw);
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
                    if(TryFeet(First,Second,CloseHeightRange,Turn))return true;
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

void UWeaponBipodDeploymentComponent::ClampAim()
{
    const auto* C=Character.Get();if(!C || !C->Controller)return;
    FRotator Aim=C->Controller->GetControlRotation();
    const float Weight=FMath::SmoothStep(0.f,1.f,PlacementBlend());
    if(!FMath::IsNearlyZero(EntryYawOffset))
    {
        Aim.Yaw=InitialAim.Yaw+EntryYawOffset*(1.f-Weight);
        if(Weight>=1.f-UE_SMALL_NUMBER)EntryYawOffset=0.f;
    }
    else Aim.Yaw=InitialAim.Yaw+FMath::Clamp(FMath::FindDeltaAngleDegrees(InitialAim.Yaw,Aim.Yaw),-YawLimitDegrees,YawLimitDegrees);
    // Deployment accepts any entry pitch. Bring an outlying view into the
    // level-mounted aim window over the weapon's placement blend;
    // do not snap the view or lock the finished mount toward the ground/sky.
    const float EntryPitchDelta=FMath::FindDeltaAngleDegrees(InitialAim.Pitch,EntryAimPitch);
    const float MinPitch=FMath::Lerp(FMath::Min(-PitchLimitDegrees,EntryPitchDelta),-PitchLimitDegrees,Weight);
    const float MaxPitch=FMath::Lerp(FMath::Max(PitchLimitDegrees,EntryPitchDelta),PitchLimitDegrees,Weight);
    Aim.Pitch=InitialAim.Pitch+FMath::Clamp(FMath::FindDeltaAngleDegrees(InitialAim.Pitch,Aim.Pitch),MinPitch,MaxPitch);
    Aim.Roll=0.;C->Controller->SetControlRotation(Aim);
}

bool UWeaponBipodDeploymentComponent::TryDeployFromADS()
{
    auto* C=Character.Get();auto* Part=EquippedBipod();
    if(!Eligible() || !C || !C->bIsAiming || C->bFireHeld || !Part)return false;
    if(HasHandDeployment()&&!C->WeaponGripProfiles.Contains(TEXT("bipod")))return false;
    if(IsM24()&&C->IsRevolverFireActionPlaying())return false;
    if(bRequested)return true;
    // A quick release/re-aim is another deliberate ADS entry. Finish the old
    // release before measuring new support instead of losing that input.
    if(Blend>UE_SMALL_NUMBER)
    {
        if(HasHandDeployment()){bPendingReaim=PendingReloadWeapon.IsEmpty();return false;}
        Release(true);
    }
    RestoreCameraOffset();FSupport Candidate;
    if(!FindSupport(*Part,Candidate)){bCandidate=false;return false;}
    Bipod=Part;Support=Candidate;InitialAim=C->GetControlRotation();
    EntryYawOffset=FMath::FindDeltaAngleDegrees(Candidate.MountYaw,float(InitialAim.Yaw));
    InitialAim.Yaw=Candidate.MountYaw;
    EntryAimPitch=FRotator::NormalizeAxis(InitialAim.Pitch);
    InitialAim.Pitch=0.f;InitialAim.Roll=0.f;
    PawnAnchor=C->GetActorLocation();bRequested=true;bCandidate=false;bSeatFired=false;bPendingReaim=false;
    NextSupportProbe=GetWorld()->GetTimeSeconds()+BipodSupportInterval;
    // Consume the input accumulated before the ADS event. Otherwise a held W
    // can move the pawn once more before the new movement lock takes effect.
    C->MoveInput=FVector2D::ZeroVector;
    C->ConsumeMovementInputVector();
    C->GetCharacterMovement()->StopMovementImmediately();
    ++LocalSequence;
    ConfirmedDeployment=FWeaponBipodNetState();
    ServerDeploy(LocalSequence,C->ActiveInventoryWeapon,Support.Feet[0],Support.Feet[1],Support.Anchor,InitialAim);
    if(!bRequested)return false;
    if(!HasHandDeployment())FireDeployCue(false);
    SetComponentTickEnabled(true);return true;
}

void UWeaponBipodDeploymentComponent::Release(bool bImmediate)
{
    const bool WasRequested=bRequested;
    auto* C=Character.Get();
    if(WasRequested&&!bApplyingNet&&C)
    {
        if(C->IsLocallyControlled())ServerRelease(++LocalSequence);
        else if(C->HasAuthority())PublishRelease();
    }
    bRequested=false;bCandidate=false;bSeatFired=false;SettleClock=-1.f;
    if(auto* Part=Bipod.Get())Part->SetLegsFrozen(false); // 解除即恢复两腿自然摆动，防止冻结泄漏
    if(bImmediate)
    {
        PendingReloadWeapon.Reset();bPendingReaim=false;
        Blend=0.f;RestoreCameraOffset();
        if(auto* Part=Bipod.Get()){Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);Part->SetM24DeploymentTime(0.f);Part->SetM249DeploymentWeight(0.f);}
        Bipod.Reset();SetComponentTickEnabled(false);
    }
}

void UWeaponBipodDeploymentComponent::Advance(float DeltaSeconds)
{
    auto* C=Character.Get();if(!C)return;
    if(!C->IsLocallyControlled())
    {
        if(C->HasAuthority())AdvanceRemoteAuthority(DeltaSeconds);
        else {bRequested=NetDeployment.bActive;Blend=FMath::FInterpConstantTo(Blend,bRequested?1.f:0.f,DeltaSeconds,1.f/TransitionDuration(bRequested));}
        if(IsM24())if(auto* Part=EquippedBipod())Part->SetM24DeploymentTime(Blend*M24Bipod::Duration);
        if(auto* Part=EquippedBipod())Part->SetM249DeploymentWeight(M249BipodAnimation::LegWeight(Blend));
        return;
    }
    const bool Allowed=Eligible(bRequested);const double Now=GetWorld()->GetTimeSeconds();
    if(!PendingReloadWeapon.IsEmpty()&&C->ActiveInventoryWeapon!=PendingReloadWeapon)PendingReloadWeapon.Reset();
    if(!C->bAimHeld)bPendingReaim=false;
    const bool Probe=bRequested && Now>=NextSupportProbe;
    if(Probe)NextSupportProbe=Now+BipodSupportInterval;
    if(bRequested && (!Allowed || !C->bIsAiming || Bipod.Get()!=EquippedBipod()
        || FVector::DistSquared(C->GetActorLocation(),PawnAnchor)>4. || !SupportStillValid(Probe)))Release();
    // 锁定兜底：击退等外力给到的速度每帧掐掉，角色钉在架设点（>2cm 位移仍走解除）。
    if(bRequested){if(auto* M=C->GetCharacterMovement();!M->Velocity.IsNearlyZero())M->StopMovementImmediately();}
    const float PreviousSeconds=Blend*M24Bipod::Duration;
    // Complete the native right-hand bolt cycle before the left hand folds.
    if(!(IsM24()&&!bRequested&&C->IsRevolverFireActionPlaying()))
        Blend=FMath::FInterpConstantTo(Blend,bRequested?1.f:0.f,DeltaSeconds,1.f/TransitionDuration(bRequested));
    if(auto* Part=Bipod.Get())Part->SetM24DeploymentTime(Blend*M24Bipod::Duration);
    if(auto* Part=Bipod.Get())Part->SetM249DeploymentWeight(M249BipodAnimation::LegWeight(Blend));
    if(HasHandDeployment())
    {
        const float Seconds=Blend*M24Bipod::Duration;
        for(const float Contact:{M24Bipod::GripContact,M24Bipod::PullComplete})
            if((PreviousSeconds<Contact&&Seconds>=Contact)||(PreviousSeconds>Contact&&Seconds<=Contact))
                FireDeployCue(bRequested?Contact==M24Bipod::PullComplete:Contact==M24Bipod::GripContact);
    }
    if(bRequested)ClampAim();
    // 完全落位的瞬间：坐弹链咔哒 + 起枪身衰减抖（表现"架在固体上"的沉降）。
    if(bRequested&&!bSeatFired&&Blend>=.999f){bSeatFired=true;SettleClock=0.f;if(!HasHandDeployment())FireDeployCue(true);}
    if(SettleClock>=0.f){SettleClock+=DeltaSeconds;if(SettleClock>.9f)SettleClock=-1.f;}
    if(!bRequested && Blend<=UE_SMALL_NUMBER)
    {
        const bool bReaim=HasHandDeployment()&&Bipod.IsValid()&&bPendingReaim;
        const bool bReload=!PendingReloadWeapon.IsEmpty()&&PendingReloadWeapon==C->ActiveInventoryWeapon;
        if(Bipod.IsValid() || !AppliedCameraOffset.IsNearlyZero())Release(true);
        PendingReloadWeapon.Reset();bPendingReaim=false;
        if(bReload)C->ReloadPressed();
        else if(bReaim&&Allowed&&C->bAimHeld&&C->bIsAiming)
        {
            // A re-aim during folding queues a fresh, continuous acquisition.
            C->SetAimingState(false);
            C->ADSProgress=C->ADSStartProgress=0.f;C->ADSStartedAt=Now;
            C->SetAimingState(true);
        }
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
    auto* C=Character.Get();if(!C||!C->IsLocallyControlled())return;
    RestoreCameraOffset();auto* Part=Bipod.Get();
    if(Blend<=UE_SMALL_NUMBER && !bRequested)return;
    if(!C || !Part || Part!=EquippedBipod()){Release(true);return;}
    if(Blend<=UE_SMALL_NUMBER)return;
    if(bRequested && (!C->bIsAiming || !Eligible(true)))Release();
    const FVector Full=(Support.Anchor-Part->GetHingeWorld())*FMath::SmoothStep(0.f,1.f,PlacementBlend());
    const FVector Eye=C->FirstPersonCamera->GetComponentLocation();
    // 窗口内的视角旋转会带动枪体姿态：净空扫掠失败不是支撑失效，不能解除架枪
    // （解除只由 Advance 里的结构性检查负责）。先把校正量减半退让，仍不行这一帧
    // 干脆不平移，保持架设状态；两腿固定默认下垂，脚掌落点仅用于支撑判定。
    FVector Delta=Full;bool bPlaced=false;
    for(int32 Attempt=0;Attempt<4;++Attempt)
    {
        if(ClearPlacement(Eye,Delta,Part->GetHingeWorld()+Delta,C->GetEffectiveMuzzleForward(),bAfterPose))
        {bPlaced=true;break;}
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
    if(HasHandDeployment())
    {
        // Keep the authored unfold/fold clock, then hold the opened rest pose
        // just like the machine guns. Looking around must not drive leg IK or
        // turn a visual reach/clearance limit into support loss or lost bonuses.
        Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);
        Part->SetM24DeploymentTime(Blend*M24Bipod::Duration);
        Part->SetM249DeploymentWeight(M249BipodAnimation::LegWeight(Blend));
    }
    else
    {
        Part->SetLegsFrozen(bRequested);
        if(!bRequested)Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);
    }
    // 落位沉降抖：骨骼姿态与相机修正都定稿之后再叠加，只动枪身——两腿钉死在默认
    // 下垂，视觉上是枪体坐实在架点上，镜头与手臂不受扰。
    if(bAfterPose&&!HasHandDeployment()&&SettleClock>=0.f&&C->AKMViewmodel)
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
        return Character.IsValid() && Character->bIsAiming ? TEXT("附近有支撑面 · 重新瞄准自动架枪")
            :TEXT("附近有支撑面 · 瞄准自动架枪");
    return TEXT("脚架：靠近箱体、矮墙或窗台");
}

FString AFPSGAMECharacter::GetBipodDeploymentHint() const
{
    return BipodDeployment?BipodDeployment->GetHint():FString();
}

void UWeaponBipodDeploymentComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UWeaponBipodDeploymentComponent,NetDeployment);
}

float UWeaponBipodDeploymentComponent::HandlingBlend() const
{
    const auto* C=Character.Get();
    if(!C||!bRequested)return 0.f;
    const auto& Deployment=C->IsLocallyControlled()?ConfirmedDeployment:NetDeployment;
    if(!Deployment.bActive||(C->IsLocallyControlled()&&
        (Deployment.Sequence!=LocalSequence||Deployment.WeaponInstance!=C->ActiveInventoryWeapon)))return 0.f;
    const auto* State=GetWorld()->GetGameState();
    const double Now=State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const float Confirmed=FMath::Min(Blend,float(FMath::Clamp((Now-Deployment.StartedAt)/TransitionDuration(true),0.,1.)));
    return HasHandDeployment()?M24Bipod::Seat(Confirmed):Confirmed;
}

FString UWeaponBipodDeploymentComponent::EquippedDefinition() const
{
    const auto* C=Character.Get();if(!C)return FString();
    const auto* Model=C->GetNetShadowProfile();
    if(!Model&&C->IsLocallyControlled())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Model?Model->Equipped():nullptr;
    return Item?Item->Definition:FString();
}

bool UWeaponBipodDeploymentComponent::AuthorityEligible(bool bContinuing) const
{
    const auto* C=Character.Get();if(!C||!C->HasAuthority()||!C->Controller)return false;
    const FString Definition=EquippedDefinition();
    if(Definition!=PKMLowpolyWeaponAssets::Definition&&Definition!=LMG201WeaponAssets::Definition&&Definition!=M24WeaponAssets::Definition&&Definition!=M249WeaponAssets::Definition)return false;
    {
        const auto* Model=C->GetNetShadowProfile();
        if(!Model&&C->IsLocallyControlled())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto* Item=Model?Model->Equipped():nullptr;
        const auto* Gunsmith=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        if(!Item||!Gunsmith||Model->ActiveProductionTool())return false;
        const FString Part=Gunsmith->Installed(*Item).FindRef(TEXT("bipod"));
        if(!BipodPartInstalled(Definition,Part))return false;
    }
    const auto* Move=Cast<UFPSCharacterMovementComponent>(C->GetCharacterMovement());
    if(!Move||!Move->IsMovingOnGround()||Move->bWantsToSlide||Move->bWantsToSprint||C->GetVelocity().SizeSquared()>100.f)return false;
    if(C->IsTraversing()||C->IsDodging()||C->IsSliding()||C->IsSwitchingWeapon()||
        C->IsCastBlockingLeftHandAction()||C->IsSpellGestureBlocking())return false;
    if(const auto* Push=C->FindComponentByClass<UFPSDoorPushComponent>();Push&&Push->IsActive())return false;
    if(const auto* Health=C->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    if(const auto* PC=Cast<APlayerController>(C->Controller);!PC||(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC)))return false;
    return true;
}

bool UWeaponBipodDeploymentComponent::ResolveServerSupport(const FWeaponBipodNetState& Proposed,FSupport& Out) const
{
    const auto* C=Character.Get();if(!C||Proposed.Anchor.ContainsNaN()||Proposed.FeetA.ContainsNaN()||
        Proposed.FeetB.ContainsNaN()||Proposed.Aim.ContainsNaN())return false;
    // Remote first-person rigs do not evaluate their pose. Resolve actual server
    // collision from bounded world contacts; never trust a client component pointer.
    const FVector Eye=C->GetMeleeAimTransform().GetLocation();
    const auto* Capsule=C->GetCapsuleComponent();
    const double FloorZ=Capsule->GetComponentLocation().Z-Capsule->GetScaledCapsuleHalfHeight();
    const bool Raised=FMath::Min(Proposed.FeetA.Z,Proposed.FeetB.Z)>FloorZ+5.;
    const double Lowering=Raised?StanceAdjustment:0.;
    const double Rising=C->bIsCrouched?Lowering:0.;
    if(!WithinBipodReach(FVector(Proposed.Anchor)-Eye,100.f+MaximumCameraReach,Lowering,Rising))return false;
    // Aim is the destination of the presentation turn. Authority verifies the
    // world contacts relative to the pawn regardless of its incoming view.
    const bool LMG=EquippedDefinition()==LMG201WeaponAssets::Definition;
    const bool Sniper=EquippedDefinition()==M24WeaponAssets::Definition;
    const float Span=EquippedDefinition()==M249WeaponAssets::Definition?float((M249Bipod::Pivots[0]+M249Bipod::Tips[0]-M249Bipod::Pivots[1]-M249Bipod::Tips[1]).Size()):Sniper?float((M24Bipod::Pivots[0]+M24Bipod::Tips[0]-M24Bipod::Pivots[1]-M24Bipod::Tips[1]).Size()):LMG?float((LMG201WeaponAssets::BipodPivotsCm[0]+LMG201WeaponAssets::BipodFeetCm[0]
        -LMG201WeaponAssets::BipodPivotsCm[1]-LMG201WeaponAssets::BipodFeetCm[1]).Size()):12.469f;
    const double Width=FVector::Dist2D(Proposed.FeetA,Proposed.FeetB);
    if(Width<Span*.5||Width>Span*1.5+4.||!FeetShareSurface(Proposed.FeetA,Proposed.FeetB,MaximumSlopeDegrees))return false;
    const FVector Center=(FVector(Proposed.FeetA)+FVector(Proposed.FeetB))*.5;
    if(FVector::DistSquared(Center,Proposed.Anchor)>FMath::Square(65.f))return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NetBipodSupport),false,C);
    const FVector Feet[]={Proposed.FeetA,Proposed.FeetB};
    const float MinNormal=FMath::Cos(FMath::DegreesToRadians(MaximumSlopeDegrees));
    // Use the same bounded support, slope, area and occlusion checks for M24,
    // PKM and LMG201. Remote rigs have no evaluated pose: visual leg reach and
    // the barrel corridor must not impose an extra M24 deployment restriction.
    for(int32 I=0;I<2;++I)
    {
        if(!WithinBipodReach(Feet[I]-Eye,110.f+MaximumCameraReach,Lowering,Rising))return false;
        FHitResult Hit;
        if(!GetWorld()->LineTraceSingleByChannel(Hit,Feet[I]+FVector(0,0,3),Feet[I]-FVector(0,0,3),SupportChannel,Params)||
            !IsBipodSupport(Hit)||Hit.ImpactNormal.Z<MinNormal||FVector::DistSquared(Hit.ImpactPoint,Feet[I])>4.)return false;
        if(!CanSeeBipodContact(*GetWorld(),Eye,Hit.ImpactPoint,MaximumCameraReach+Rising,SupportChannel,Params))return false;
        if(!HasBipodFootArea(*GetWorld(),Hit.ImpactPoint,MinNormal,SupportChannel,Params))return false;
        Out.Feet[I]=Hit.ImpactPoint+FVector(0,0,.12);
        Out.Components[I]=Hit.GetComponent();Out.Transforms[I]=Hit.GetComponent()->GetComponentTransform();
    }
    Out.Anchor=Proposed.Anchor;return true;
}

FString UWeaponBipodDeploymentComponent::EquippedInstance() const
{
    const auto* C=Character.Get();if(!C)return FString();
    const auto* Model=C->GetNetShadowProfile();
    if(!Model&&C->IsLocallyControlled()&&GetWorld()->GetGameInstance())
        Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Model?Model->Equipped():nullptr;
    return Item?Item->InstanceId:FString();
}

void UWeaponBipodDeploymentComponent::ServerDeploy_Implementation(uint16 Sequence,const FString& WeaponInstance,FVector_NetQuantize100 FeetA,
    FVector_NetQuantize100 FeetB,FVector_NetQuantize100 Anchor,FRotator Aim)
{
    if(static_cast<int16>(Sequence-NetDeployment.Sequence)<=0)return;
    const double Now=GetWorld()->GetTimeSeconds();
    FWeaponBipodNetState Proposed;Proposed.Sequence=Sequence;Proposed.FeetA=FeetA;Proposed.FeetB=FeetB;
    Proposed.WeaponInstance=WeaponInstance;
    Proposed.Anchor=Anchor;Proposed.Aim=Aim;Proposed.Aim.Roll=0.;Proposed.Aim.Normalize();
    Proposed.Aim.Pitch=0.;
    FSupport Resolved;
    const bool Accepted=!WeaponInstance.IsEmpty()&&WeaponInstance==EquippedInstance()
        &&(LastDeployRequest<0.||Now-LastDeployRequest>=.1)&&AuthorityEligible()&&ResolveServerSupport(Proposed,Resolved);
    LastDeployRequest=Now;
    Proposed.bActive=Accepted;Proposed.StartedAt=Now;NetDeployment=Proposed;
    if(Accepted)
    {
        Support=Resolved;NetDeployment.FeetA=Support.Feet[0];NetDeployment.FeetB=Support.Feet[1];
        EntryAimPitch=FRotator::NormalizeAxis(Character->GetControlRotation().Pitch);
        EntryYawOffset=FMath::FindDeltaAngleDegrees(Proposed.Aim.Yaw,Character->GetControlRotation().Yaw);
        PawnAnchor=Character->GetActorLocation();InitialAim=Proposed.Aim;
        MountedDefinition=EquippedDefinition();NextSupportProbe=Now+BipodSupportInterval;
        bRequested=true;Character->GetCharacterMovement()->StopMovementImmediately();
    }
    else {TGuardValue<bool> Applying(bApplyingNet,true);Release(true);}
    GetOwner()->ForceNetUpdate();ClientDeploymentResult(NetDeployment);
}

void UWeaponBipodDeploymentComponent::PublishRelease()
{
    if(!NetDeployment.bActive)return;
    NetDeployment.bActive=false;GetOwner()->ForceNetUpdate();
    ClientDeploymentResult(NetDeployment);
}

void UWeaponBipodDeploymentComponent::ServerRelease_Implementation(uint16 Sequence)
{
    if(static_cast<int16>(Sequence-NetDeployment.Sequence)<=0)return;
    NetDeployment.Sequence=Sequence;NetDeployment.bActive=false;
    GetOwner()->ForceNetUpdate();
    if(Character.IsValid()&&!Character->IsLocallyControlled())
    {TGuardValue<bool> Applying(bApplyingNet,true);Release();}
}

void UWeaponBipodDeploymentComponent::ClientDeploymentResult_Implementation(const FWeaponBipodNetState& State)
{
    ApplyOwnerDeployment(State);
}

void UWeaponBipodDeploymentComponent::OnRep_Deployment()
{
    if(!Character.IsValid())return;
    if(!Character->IsLocallyControlled())
    {bRequested=NetDeployment.bActive;InitialAim=NetDeployment.Aim;return;}
    ApplyOwnerDeployment(NetDeployment);
}

void UWeaponBipodDeploymentComponent::ApplyOwnerDeployment(const FWeaponBipodNetState& State)
{
    const auto* C=Character.Get();
    if(!C||!C->IsLocallyControlled()||State.Sequence!=LocalSequence||!bRequested)return;
    ConfirmedDeployment=State;
    if(!State.bActive||State.WeaponInstance!=C->ActiveInventoryWeapon)
    {TGuardValue<bool> Applying(bApplyingNet,true);Release();return;}
    InitialAim=State.Aim;Support.Anchor=State.Anchor;
    // Retain the client's own component handles for local support monitoring.
    Support.Feet[0]=State.FeetA;Support.Feet[1]=State.FeetB;
}

void UWeaponBipodDeploymentComponent::AdvanceRemoteAuthority(float DeltaSeconds)
{
    const double Now=GetWorld()->GetTimeSeconds();
    if(NetDeployment.bActive)
    {
        const auto* Move=Cast<UFPSCharacterMovementComponent>(Character->GetCharacterMovement());
        const bool Probe=Now>=NextSupportProbe;
        if(Probe)NextSupportProbe=Now+BipodSupportInterval;
        if(!AuthorityEligible(true)||EquippedDefinition()!=MountedDefinition||EquippedInstance()!=NetDeployment.WeaponInstance||
            (Now-NetDeployment.StartedAt>.35&&(!Move||!Move->bWantsToAim))||
            FVector::DistSquared(Character->GetActorLocation(),PawnAnchor)>4.||!SupportStillValid(Probe))
        {PublishRelease();bRequested=false;}
        else Character->GetCharacterMovement()->StopMovementImmediately();
    }
    bRequested=NetDeployment.bActive;
    Blend=FMath::FInterpConstantTo(Blend,bRequested?1.f:0.f,DeltaSeconds,1.f/TransitionDuration(bRequested));
    if(bRequested)ClampAim();
}

#include "M24BipodValidation.inl"
