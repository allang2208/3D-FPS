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
    FoldingSightHeads.Reset();FoldingSightMounts.Reset();FoldingSightAxes.Reset();FoldingSightAngles.Reset();
    const auto* WeaponMesh=AKMViewmodel->GetSkeletalMeshAsset();
    if(!WeaponMesh||(!bUseQBZ191&&!WeaponMesh->GetName().Contains(TEXT("FoldingSights"))))return;
    const auto& Ref=WeaponMesh->GetRefSkeleton();FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root=Root*Ref.GetRefBonePose()[I];
    for(int32 I=0;I<2;++I)
    {
        const FString Name=bUseQBZ191?(I==0?TEXT("SM_QBZ191_RearSight"):TEXT("SM_QBZ191_FrontSight")):(I==0?TEXT("SM_M4_RearSight"):TEXT("SM_M4_FrontSight"));
        const FString Directory=bUseQBZ191?TEXT("/Game/Weapons/QBZ191/Attachments20260913/"):TEXT("/Game/Weapons/M4FoldingSights/");
        auto* Part=LoadObject<UStaticMesh>(nullptr,*(Directory+Name+TEXT(".")+Name));
        if(!Part){UE_LOG(LogTemp,Error,TEXT("WEAPON_FOLDING: missing %s"),*Name);continue;}
        auto* Head=NewObject<UStaticMeshComponent>(this);
        Head->SetStaticMesh(Part);Head->SetCollisionEnabled(ECollisionEnabled::NoCollision);Head->SetCastShadow(false);Head->bReceivesDecals=false;
        Head->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));Head->RegisterComponent();
        // QBZ head vertices are centimetres relative to their own hinge in the
        // WPN_root frame. That private bone uses metres, as do its optic mounts.
        const FTransform Mount=bUseQBZ191
            ?FTransform(FQuat::Identity,FVector(.000688f,I==0?-.009231f:.343514f,.1000f),FVector(.01f))
            :FTransform(FQuat::Identity,M4Sights::Hinges[I]).GetRelativeTransform(Root);
        Head->SetRelativeTransform(Mount);FoldingSightHeads.Add(Head);FoldingSightMounts.Add(Mount);
        FoldingSightAxes.Add(bUseQBZ191?FVector::ForwardVector:M4Sights::Axis);
        // Fold outward, away from the shared optic saddle: rear to stock,
        // front to muzzle. Blender's Y reflection reverses the author angles.
        FoldingSightAngles.Add(bUseQBZ191?(I==0?90.f:-90.f):M4Sights::Angles[I]);
    }
    UpdateFoldingSights(0.f);
}
void AFPSGAMECharacter::UpdateFoldingSights(float /*DeltaSeconds*/)
{
    if(FoldingSightHeads.Num()!=2)return;
    // Folding is an attachment state, including when rebuilding a switched weapon.
    SightFoldAlpha=bHolographicOptic?1.f:0.f;
    for(int32 I=0;I<2;++I)
    {
        FTransform Pose=FoldingSightMounts[I];
        Pose.SetRotation(Pose.GetRotation()*FQuat(FoldingSightAxes[I],FMath::DegreesToRadians(FoldingSightAngles[I]*SightFoldAlpha)));
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
        Expected.SetRotation(Expected.GetRotation()*FQuat(FoldingSightAxes[I],FMath::DegreesToRadians(bFolded?FoldingSightAngles[I]:0.f)));
        Expected=Expected*Root;
        if(!Head->GetComponentLocation().Equals(Expected.GetLocation(),.02f)||Head->GetComponentQuat().AngularDistance(Expected.GetRotation())>.002f)return false;
    }
    return true;
}
