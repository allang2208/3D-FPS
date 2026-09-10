#include "../FPSGAMECharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

namespace M4Sights
{
    // Generated from the actual source mesh in folding-sights.json. Component-space cm.
    const FVector Hinges[]={{4.81653735,-17.89975911,1.09246466},{4.81410958,-49.31282997,1.17446287}};
    const FVector Axis=FVector(-.99619466,0,-.08715604).GetSafeNormal();
    const float Angles[]={-90.f,90.f};
}
void AFPSGAMECharacter::InitializeFoldingSights()
{
    for(auto Head:FoldingSightHeads)Head->DestroyComponent();
    FoldingSightHeads.Reset();FoldingSightMounts.Reset();
    const auto* WeaponMesh=AKMViewmodel->GetSkeletalMeshAsset();
    if(!WeaponMesh||!WeaponMesh->GetName().Contains(TEXT("FoldingSights")))return;
    const auto& Ref=WeaponMesh->GetRefSkeleton();FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root=Root*Ref.GetRefBonePose()[I];
    for(int32 I=0;I<2;++I)
    {
        const FString Name=I==0?TEXT("SM_M4_RearSight"):TEXT("SM_M4_FrontSight");
        auto* Part=LoadObject<UStaticMesh>(nullptr,*(TEXT("/Game/Weapons/M4FoldingSights/")+Name+TEXT(".")+Name));
        if(!Part){UE_LOG(LogTemp,Error,TEXT("M4_FOLDING: missing %s"),*Name);continue;}
        auto* Head=NewObject<UStaticMeshComponent>(this);
        Head->SetStaticMesh(Part);Head->SetCollisionEnabled(ECollisionEnabled::NoCollision);Head->SetCastShadow(false);Head->bReceivesDecals=false;
        Head->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));Head->RegisterComponent();
        const FTransform Mount=FTransform(FQuat::Identity,M4Sights::Hinges[I]).GetRelativeTransform(Root);
        Head->SetRelativeTransform(Mount);FoldingSightHeads.Add(Head);FoldingSightMounts.Add(Mount);
    }
    SightFoldAlpha=bHolographicOptic?1.f:0.f;UpdateFoldingSights(0.f);
}
void AFPSGAMECharacter::UpdateFoldingSights(float DeltaSeconds)
{
    if(FoldingSightHeads.Num()!=2)return;
    SightFoldAlpha=FMath::FInterpConstantTo(SightFoldAlpha,bHolographicOptic?1.f:0.f,DeltaSeconds,1.f/.18f);
    const float Smooth=SightFoldAlpha*SightFoldAlpha*(3.f-2.f*SightFoldAlpha);
    for(int32 I=0;I<2;++I)
    {
        FTransform Pose=FoldingSightMounts[I];
        Pose.SetRotation(Pose.GetRotation()*FQuat(M4Sights::Axis,FMath::DegreesToRadians(M4Sights::Angles[I]*Smooth)));
        FoldingSightHeads[I]->SetRelativeTransform(Pose);
    }
}
bool AFPSGAMECharacter::ValidateFoldingSights(bool bFolded) const
{
    if(FoldingSightHeads.Num()!=2||!FMath::IsNearlyEqual(SightFoldAlpha,bFolded?1.f:0.f,.001f))return false;
    for(int32 I=0;I<2;++I)
    {
        const auto* Head=FoldingSightHeads[I].Get();if(!Head||!Head->IsVisible())return false;
        const FTransform Root=AKMViewmodel->GetSocketTransform(TEXT("WPN_root"));
        FTransform Expected=FoldingSightMounts[I];
        Expected.SetRotation(Expected.GetRotation()*FQuat(M4Sights::Axis,FMath::DegreesToRadians(bFolded?M4Sights::Angles[I]:0.f)));
        Expected=Expected*Root;
        if(!Head->GetComponentLocation().Equals(Expected.GetLocation(),.02f)||Head->GetComponentQuat().AngularDistance(Expected.GetRotation())>.002f)return false;
    }
    return true;
}
