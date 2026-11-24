#include "ColdSteelDamageNumberSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void UColdSteelDamageNumberSubsystem::PushDamageNumber(AActor* Target,APlayerController* Viewer,
    const FVector& WorldPoint,float Damage,bool bCritical,bool bKilled,bool bBig,bool bTrackTarget,float MagicDamage)
{
    if(!Target||!Viewer||Damage<=0.f||Damage>100000000.f)return;
    if(Pending.Num()>=MaxPending)Pending.RemoveAt(0);
    FColdSteelDamageNumberEvent Event;
    Event.Target=Target;
    Event.Viewer=Viewer;
    Event.WorldPoint=WorldPoint;
    Event.Magic=FMath::Clamp(MagicDamage,0.f,Damage);
    Event.Physical=Damage-Event.Magic;
    Event.bCritical=bCritical;
    Event.bKilled=bKilled;
    Event.bBig=bBig;
    Event.bTrackTarget=bTrackTarget;
    Pending.Add(MoveTemp(Event));
}

FVector UColdSteelDamageNumberSubsystem::TargetTopAnchor(const AActor* Target)
{
    if(!Target)return FVector::ZeroVector;
    if(const auto* Mesh=Target->FindComponentByClass<USkeletalMeshComponent>())
    {
        // A head/cranium bone follows animation and ragdolls exactly. Do not use
        // the mesh component bounds first: tentacle/reach monsters scale those via
        // SetBoundsScale, which can push the number far above the visible body.
        const FName HeadBones[]={FName(TEXT("head")),FName(TEXT("cranium"))};
        for(const FName& Bone:HeadBones)
            if(Mesh->GetBoneIndex(Bone)!=INDEX_NONE)
                return Mesh->GetBoneLocation(Bone,EBoneSpaces::WorldSpace)+FVector(0,0,20.f);
        // No head bone: use the mesh asset bounds (unscaled by component BoundsScale),
        // transformed to world.
        if(const USkeletalMesh* Asset=Mesh->GetSkeletalMeshAsset())
        {
            const FBox Box=Asset->GetBounds().GetBox().TransformBy(Mesh->GetComponentTransform());
            if(Box.IsValid)return FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Max.Z);
        }
        const FBox MeshBox=Mesh->Bounds.GetBox();
        if(MeshBox.IsValid)return FVector(MeshBox.GetCenter().X,MeshBox.GetCenter().Y,MeshBox.Max.Z);
    }
    const FBox Bounds=Target->GetComponentsBoundingBox(true);
    if(!Bounds.IsValid)return Target->GetActorLocation();
    return FVector(Bounds.GetCenter().X,Bounds.GetCenter().Y,Bounds.Max.Z);
}

bool UColdSteelDamageNumberSubsystem::ConsumeDamageNumbers(TArray<FColdSteelDamageNumberEvent>& Out)
{
    if(Pending.IsEmpty())return false;
    Out=MoveTemp(Pending);
    Pending.Reset();
    return !Out.IsEmpty();
}

void UColdSteelDamageNumberSubsystem::Reset()
{
    Pending.Reset();
}
