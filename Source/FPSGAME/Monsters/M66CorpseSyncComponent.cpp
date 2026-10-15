#include "M66CorpseSyncComponent.h"
#include "M66IncineratorMonster.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCorpsePoseAnimInstance.h"
#include "MonsterRagdollPhysics.h"
#include "M66AudioComponent.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

bool FM66CorpsePacket::NetSerialize(FArchive& Ar,UPackageMap*,bool& Success)
{
    Ar<<Revision<<ServerTime;Ar.SerializeBits(&Frozen,1);MeshWorld.Serialize(Ar);
    uint16 Count=uint16(LocalPose.Num());Ar<<Count;
    if(Count>256){Success=false;Ar.SetError();return false;}
    if(Ar.IsLoading())LocalPose.SetNum(Count);
    for(auto& Transform:LocalPose)
    {
        FVector3f Position(Transform.GetTranslation()),Scale(Transform.GetScale3D());
        FRotator Rotation=Transform.Rotator();Ar<<Position<<Scale;Rotation.SerializeCompressedShort(Ar);
        if(Ar.IsLoading())Transform=FTransform(Rotation,FVector(Position),FVector(Scale));
    }
    Success=!Ar.IsError();return true;
}
UM66CorpseSyncComponent::UM66CorpseSyncComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;PrimaryComponentTick.TickGroup=TG_PostPhysics;
}
void UM66CorpseSyncComponent::BeginPlay()
{
    Super::BeginPlay();Monster=Cast<AM66IncineratorMonster>(GetOwner());
    if(Monster){AddTickPrerequisiteComponent(Monster->GetMesh());AddTickPrerequisiteComponent(Monster->CorpseRagdoll);}
    if(Packet.Revision)Wake();
}
void UM66CorpseSyncComponent::Wake(){SetComponentTickEnabled(true);}
void UM66CorpseSyncComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UM66CorpseSyncComponent,Packet);}
void UM66CorpseSyncComponent::OnRep_Packet()
{
    PreviousPose=Pose.LocalTransforms;
    if(Monster)PreviousWorld=Monster->GetMesh()->GetComponentTransform();
    BlendAge=bRemoteSetup?0.f:.1f;Wake();
}
void UM66CorpseSyncComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Dt,Type,Function);if(!Monster)return;
    auto* Mesh=Monster->GetMesh();
    if(GetOwner()->HasAuthority())
    {
        auto* Corpse=Monster->CorpseRagdoll.Get();
        const bool Frozen=Corpse->IsFrozen();
        if(!Corpse->SimulatedBodyCount()&&!Frozen)return;
        PhysicsAge+=Dt;
        if(!bImpactPlayed&&PhysicsAge>.2f)
        {
            FHitResult Hit;bool Contact=Frozen;
            if(const auto* Body=Mesh->GetBodyInstance(TEXT("Bone_006")))
            {
                const FBox Bounds=Body->GetBodyBounds();const FVector Bottom(Bounds.GetCenter().X,Bounds.GetCenter().Y,Bounds.Min.Z);
                Contact|=GetWorld()->LineTraceSingleByObjectType(Hit,Bottom+FVector(0,0,8),Bottom-FVector(0,0,8),
                    FCollisionObjectQueryParams(FCollisionObjectQueryParams::AllStaticObjects),FCollisionQueryParams(SCENE_QUERY_STAT(M66BodyFall),false,Monster));
            }
            if(Contact){bImpactPlayed=true;Monster->BodyAudio->Emit(TEXT("Land"),Hit.bBlockingHit?Hit.ImpactPoint:Mesh->GetSocketLocation(TEXT("Bone_001")));}
        }
        PublishAge+=Dt;if(Packet.Revision&&PublishAge<.1f&&!Frozen)return;PublishAge=0.f;
        FPoseSnapshot Snapshot;
        if(Frozen)Mesh->SnapshotPose(Snapshot);else MonsterRagdollPhysics::CapturePose(Mesh,Snapshot);
        if(!Snapshot.bIsValid)return;
        Packet.LocalPose=MoveTemp(Snapshot.LocalTransforms);Packet.MeshWorld=Mesh->GetComponentTransform();Packet.Frozen=Frozen;
        const auto* Clock=GetWorld()->GetGameState();Packet.ServerTime=Clock?Clock->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        ++Packet.Revision;Monster->ForceNetUpdate();
        if(Frozen)SetComponentTickEnabled(false);
        return;
    }
    if(!Packet.Revision||!Mesh->GetSkeletalMeshAsset())return;
    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    if(Packet.LocalPose.Num()!=Ref.GetNum())return;
    if(!bRemoteSetup)
    {
        Monster->AcceptServerCorpse();
        Mesh->SetComponentTickEnabled(true);Mesh->SetForcedLOD(1);
        Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
        Mesh->SetSimulatePhysics(false);Mesh->SetAllBodiesSimulatePhysics(false);Mesh->SetAllBodiesPhysicsBlendWeight(0.f);
        Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
        Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        Mesh->bPauseAnims=false;Mesh->SetAnimInstanceClass(UMonsterCorpsePoseAnimInstance::StaticClass());
        Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Pose.BoneNames.Reset();for(int32 I=0;I<Ref.GetNum();++I)Pose.BoneNames.Add(Ref.GetBoneName(I));
        Pose.SkeletalMeshName=Mesh->GetSkeletalMeshAsset()->GetFName();Pose.bIsValid=true;bRemoteSetup=true;
    }
    BlendAge=FMath::Min(.1f,BlendAge+Dt);const float Alpha=BlendAge/.1f;
    Pose.LocalTransforms=Packet.LocalPose;
    FTransform WorldPose=Packet.MeshWorld;
    if(Alpha<1.f&&PreviousPose.Num()==Pose.LocalTransforms.Num())
    {
        WorldPose.Blend(PreviousWorld,Packet.MeshWorld,Alpha);
        for(int32 I=0;I<Pose.LocalTransforms.Num();++I)Pose.LocalTransforms[I].Blend(PreviousPose[I],Packet.LocalPose[I],Alpha);
    }
    Mesh->SetWorldTransform(WorldPose,false,nullptr,ETeleportType::TeleportPhysics);
    if(auto* Anim=Cast<UMonsterCorpsePoseAnimInstance>(Mesh->GetAnimInstance()))Anim->HoldPose(Pose);
    Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
    if(Packet.Frozen&&Alpha>=1.f){MonsterRagdollPhysics::RetireCorpseTicks(Mesh);SetComponentTickEnabled(false);}
}
