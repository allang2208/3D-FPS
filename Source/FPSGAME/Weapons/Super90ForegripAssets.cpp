#include "Super90ForegripAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

UStaticMeshComponent* Super90ForegripAssets::Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const TCHAR* GripFamily,bool bEnabled)
{
    if(!bEnabled||!Host||!Host->GetSkeletalMeshAsset())
    {
        if(Existing)Existing->DestroyComponent();
        return nullptr;
    }
    const FString Path=MeshPath(GripFamily);
    auto* PartMesh=LoadObject<UStaticMesh>(nullptr,*Path);
    if(!PartMesh)
    {
        if(Existing)Existing->DestroyComponent();
        UE_LOG(LogTemp,Error,TEXT("Super90 missing foregrip %s"),*Path);
        return nullptr;
    }
    if(!Existing)
    {
        Existing=NewObject<UStaticMeshComponent>(Owner);
        Owner->AddInstanceComponent(Existing);
        Existing->SetupAttachment(Host,TEXT("WPN_root"));
        Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);Existing->bReceivesDecals=false;
        Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
        Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
        Existing->RegisterComponent();
    }
    Existing->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    Existing->EmptyOverrideMaterials();Existing->SetStaticMesh(PartMesh);
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root=Root*Ref.GetRefBonePose()[I];
    // The native rig's root has a different up axis and inherited FBX scale.
    // Use the measured component-space seat, as in the Super90 optic mount.
    const FTransform Seat(FRotationMatrix::MakeFromXZ(FVector(0,-1,0),FVector::UpVector).ToQuat(),FVector(0,-16.f,-80.15f));
    Existing->SetRelativeTransform(Seat.GetRelativeTransform(Root));
    Existing->SetVisibility(true);
    return Existing;
}
