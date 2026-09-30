#include "HumanoidKnockdownComponent.h"
#include "NurseZombie.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"

const TArray<FMonsterObstaclePose>& UHumanoidKnockdownComponent::ClipObstaclePoses(UAnimSequence* Clip)
{
    const TWeakObjectPtr<UAnimSequence> Key(Clip);
    if (const auto* Cached=ClipObstacleCache.Find(Key)) return *Cached;
    // At most fall, supine recovery and prone recovery; component lifetime only.
    if (ClipObstacleCache.Num()>=3) ClipObstacleCache.Reset();
    auto& Frames=ClipObstacleCache.Add(Key);
    if (!Clip) return Frames;
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Clip->GetPlayLength()/.08f),1,64);
    Frames.Reserve(Steps+1);
    for (int32 Frame=0;Frame<=Steps;++Frame)
    {
        auto& Pose=Frames.AddDefaulted_GetRef();
        Pose.Reserve(ObstacleProbes.Num());
        TMap<FName,FTransform> Bones;
        for (const auto& Probe:ObstacleProbes)
        {
            FTransform* Bone=Bones.Find(Probe.Bone);
            if (!Bone) Bone=&Bones.Add(Probe.Bone,ClipBone(Clip,Probe.Bone,Clip->GetPlayLength()*Frame/Steps)*StandingMeshRelative);
            Pose.Add(MonsterObstacleCollision::TransformProbe(Probe,*Bone));
        }
    }
    return Frames;
}

bool UHumanoidKnockdownComponent::PrepareAnimatedCapsule()
{
    if (bAnimatedCapsule) return true;
    auto* N=Humanoid(); auto* Capsule=N->GetCapsuleComponent();
    AnimatedRadius=StandingRadius;
    for (const auto& Pose:ClipObstaclePoses(FallClip))
        for (const auto& Sphere:Pose)
            AnimatedRadius=FMath::Max(AnimatedRadius,float(Sphere.Center.Size2D())+Sphere.Radius+2.f);
    if (ObstacleProbes.IsEmpty()) AnimatedRadius=FMath::Max(AnimatedRadius,StandingHalfHeight*2.f);
    const float Height=FMath::Max(StandingHalfHeight,AnimatedRadius);
    const float Scale=Capsule->GetShapeScale();
    const FVector Center=N->GetActorLocation()+FVector(0,0,(Height-StandingHalfHeight)*Scale);
    FCollisionResponseContainer Responses=Capsule->GetCollisionResponseToChannels();
    Responses.SetResponse(ECC_Pawn,ECR_Ignore);
    return !GetWorld()->OverlapBlockingTestByChannel(Center+FVector(0,0,1),N->GetActorQuat(),Capsule->GetCollisionObjectType(),
        FCollisionShape::MakeCapsule(AnimatedRadius*Scale-.5f,Height*Scale-.5f),
        FCollisionQueryParams(SCENE_QUERY_STAT(HumanoidFallSpace),false,N),FCollisionResponseParams(Responses));
}

void UHumanoidKnockdownComponent::ApplyAnimatedCapsule()
{
    if (bAnimatedCapsule) return;
    auto* N=Humanoid(); auto* Capsule=N->GetCapsuleComponent(); auto* Mesh=BodyMesh();
    auto* Move=N->GetCharacterMovement();
    AddedHalfHeight=FMath::Max(StandingHalfHeight,AnimatedRadius)-StandingHalfHeight;
    Move->SetUpdateNavAgentWithOwnersCollisions(false);
    Move->AirControl=0; Move->bOrientRotationToMovement=false;
    Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Capsule->SetCapsuleSize(AnimatedRadius,StandingHalfHeight+AddedHalfHeight,false);
    Capsule->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    N->SetActorLocation(N->GetActorLocation()+FVector(0,0,AddedHalfHeight*Capsule->GetShapeScale()),false,nullptr,ETeleportType::TeleportPhysics);
    Mesh->AttachToComponent(Capsule,FAttachmentTransformRules::KeepWorldTransform);
    bAnimatedCapsule=true;
}

void UHumanoidKnockdownComponent::RestoreAnimatedCapsule()
{
    if (!bAnimatedCapsule) return;
    auto* N=Humanoid(); auto* Capsule=N->GetCapsuleComponent(); auto* Mesh=BodyMesh();
    const bool Attached=Mesh->GetAttachParent()==Capsule;
    if (Attached) Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Capsule->SetCapsuleSize(StandingRadius,StandingHalfHeight,false);
    Capsule->SetCollisionResponseToChannel(ECC_Pawn,StandingPawnResponse);
    N->SetActorLocation(N->GetActorLocation()-FVector(0,0,AddedHalfHeight*Capsule->GetShapeScale()),false,nullptr,ETeleportType::TeleportPhysics);
    if (Attached) Mesh->AttachToComponent(Capsule,FAttachmentTransformRules::KeepWorldTransform);
    auto* Move=N->GetCharacterMovement();
    Move->SetUpdateNavAgentWithOwnersCollisions(bStandingNavUpdate);
    Move->AirControl=StandingAirControl; Move->bOrientRotationToMovement=bStandingOrientToMovement;
    bAnimatedCapsule=false; AddedHalfHeight=0;
}

bool UHumanoidKnockdownComponent::RecoveryPathFits(UAnimSequence* Clip,const FTransform& ActorTransform,float FloorZ)
{
    FMonsterObstaclePose Previous,Next;
    MonsterObstacleCollision::WorldPose(BodyMesh(),ObstacleProbes,Previous);
    const auto& Frames=ClipObstaclePoses(Clip);
    // Most recoveries are in open floor space. One conservative broad-phase box
    // skips all per-body sweeps there; only wall/column contacts need the detail.
    FBox Envelope(ForceInit);
    auto Include=[&](const FMonsterObstacleSphere& Sphere)
    {
        FVector Center=Sphere.Center;
        Center.Z=FMath::Max(Center.Z,double(FloorZ+Sphere.Radius+2.f));
        Envelope+=Center-FVector(Sphere.Radius); Envelope+=Center+FVector(Sphere.Radius);
    };
    for (const auto& Sphere:Previous) Include(Sphere);
    for (const auto& LocalPose:Frames)
        for (const auto& Sphere:LocalPose)
            Include({ActorTransform.TransformPosition(Sphere.Center),static_cast<float>(Sphere.Radius*ActorTransform.GetScale3D().GetAbsMax())});
    FCollisionResponseContainer Responses(ECR_Ignore);
    Responses.SetResponse(ECC_WorldStatic,ECR_Block); Responses.SetResponse(ECC_WorldDynamic,ECR_Block);
    if (Envelope.IsValid && !GetWorld()->OverlapBlockingTestByChannel(Envelope.GetCenter(),FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeBox(Envelope.GetExtent()),FCollisionQueryParams(SCENE_QUERY_STAT(HumanoidRecoveryEnvelope),false,Humanoid()),
        FCollisionResponseParams(Responses))) return true;
    for (const auto& LocalPose:Frames)
    {
        Next.Reset(LocalPose.Num());
        for (const auto& Sphere:LocalPose)
            Next.Add({ActorTransform.TransformPosition(Sphere.Center),static_cast<float>(Sphere.Radius*ActorTransform.GetScale3D().GetAbsMax())});
        if (!MonsterObstacleCollision::PoseFits(Humanoid(),Next,FloorZ) ||
            !MonsterObstacleCollision::PathFits(Humanoid(),Previous,Next,FloorZ)) return false;
        Swap(Previous,Next);
    }
    return true;
}

bool UHumanoidKnockdownComponent::FindRecoverySpace(UAnimSequence* Clip,FHitResult& Floor,FRotator& Facing,FVector& Candidate)
{
    const double Now=GetWorld()->GetTimeSeconds();
    if (Now<NextRecoveryProbe) return false;
    NextRecoveryProbe=Now+.35;
    auto* N=Humanoid(); auto* Mesh=BodyMesh(); auto* Capsule=N->GetCapsuleComponent();
    const FVector Pelvis=Mesh->GetSocketLocation(PelvisBone);
    const FVector Axis=(Mesh->GetSocketLocation(HeadBone)-Pelvis).GetSafeNormal2D();
    const FVector ClipPelvis=ClipBone(Clip,PelvisBone,0.f).GetLocation();
    const FVector ClipAxis=StandingMeshRelative.TransformVectorNoScale(ClipBone(Clip,HeadBone,0.f).GetLocation()-ClipPelvis).GetSafeNormal2D();
    const float BaseYaw=Axis.IsNearlyZero()?N->GetActorRotation().Yaw:Axis.Rotation().Yaw-ClipAxis.Rotation().Yaw;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(HumanoidGetUpClearance),false,N);
    FCollisionResponseContainer Responses=Capsule->GetCollisionResponseToChannels();
    Responses.SetResponse(ECC_Pawn,ECR_Ignore);
    // Try only two facings per bounded probe, rather than all directions every tick.
    static constexpr float Yaws[]={0,45,-45,90,-90,135,-135,180};
    for (int32 Attempt=0;Attempt<2;++Attempt)
    {
        const float Yaw=Yaws[RecoveryFacingIndex++%UE_ARRAY_COUNT(Yaws)];
        Facing=FRotator(0,BaseYaw+Yaw,0);
        Candidate=Pelvis-Facing.RotateVector(StandingMeshRelative.TransformPosition(ClipPelvis)*N->GetActorScale3D());
        FHitResult Support;
        const FVector At(Candidate.X,Candidate.Y,Floor.ImpactPoint.Z);
        if (!GetWorld()->LineTraceSingleByChannel(Support,At+FVector(0,0,30),At-FVector(0,0,35),ECC_Pawn,Query,FCollisionResponseParams(Responses)) ||
            Support.ImpactNormal.Z<N->GetCharacterMovement()->GetWalkableFloorZ()) continue;
        Candidate.Z=Support.ImpactPoint.Z+Capsule->GetScaledCapsuleHalfHeight()+2.f;
        if (GetWorld()->OverlapBlockingTestByChannel(Candidate,FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),Query,FCollisionResponseParams(Responses))) continue;
        if (auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
        {
            const auto& Agent=N->GetCharacterMovement()->GetNavAgentPropertiesRef();
            const auto* Data=Nav->GetNavDataForProps(Agent);
            FNavLocation Location;
            if (Data && (!Nav->ProjectPointToNavigation(FVector(Candidate.X,Candidate.Y,Support.ImpactPoint.Z),Location,FVector(15,15,40),Data) ||
                FVector::DistSquared2D(Location.Location,Candidate)>FMath::Square(15.f))) continue;
        }
        if (!RecoveryPathFits(Clip,FTransform(Facing,Candidate,N->GetActorScale3D()),Support.ImpactPoint.Z)) continue;
        Floor=Support;
        RecoveryFacingIndex=0;
        return true;
    }
    return false;
}
