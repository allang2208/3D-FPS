#pragma once
#include "PKMLowpolyWeaponAssets.h"

namespace PKMAttachments
{
inline FString MeshPath(const FString& Key)
{
    if(Key==TEXT("optic_rail"))
        return TEXT("/Game/Weapons/PKMLowpoly20260922/OpticMount23/SM_PKM_optic_rail");
    return TEXT("/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_")+Key;
}
inline FString AnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/%s/A_PKM_%s_%s"),Family,Family,Clip);
}
inline FTransform OpticMount(const FString& Variant)
{
    // Cover-local metres. The authored rail follows the opening cover, while
    // OpticMount23 lowers the contact plane 9.1 mm. It still clears the
    // measured factory rear sight; all optic bodies retain their own scale.
    const double GunY=Variant==TEXT("lpvo_1_6x")?.050:Variant==TEXT("prism_scope_2x")?.060:.070;
    return FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(0.,-(GunY+.021),.0444),FVector(.01));
}
inline const FVector MuzzleMount(-.0000381814,.7870370393,.0778526890);
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,
    const TCHAR* Key,bool Enabled,FName Bone=TEXT("WPN_root"))
{
    if(!Enabled){if(Part)Part->SetVisibility(false);return Part;}
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
    if(!Mesh){if(Part)Part->SetVisibility(false);UE_LOG(LogTemp,Error,TEXT("PKM_ATTACHMENT: missing %s"),Key);return Part;}
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,Bone);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    else if(Part->GetAttachParent()!=Rifle||Part->GetAttachSocketName()!=Bone)
        Part->AttachToComponent(Rifle,FAttachmentTransformRules::KeepRelativeTransform,Bone);
    if(Part->GetStaticMesh()!=Mesh)Part->EmptyOverrideMaterials();
    Part->SetStaticMesh(Mesh);
    Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01)));
    Part->SetVisibility(true);return Part;
}
inline UStaticMeshComponent* FindRail(AActor* Owner)
{
    TInlineComponentArray<UStaticMeshComponent*> Parts(Owner);
    for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("PKMOpticRail")))return Part;
    return nullptr;
}
inline void ConfigureRail(AActor* Owner,USkeletalMeshComponent* Rifle,bool Enabled)
{
    auto* Part=FindRail(Owner);
    Part=Configure(Owner,Rifle,Part,TEXT("optic_rail"),Enabled&&PKMLowpolyWeaponAssets::Matches(Rifle),TEXT("PKM_Cover"));
    if(Part)Part->ComponentTags.AddUnique(TEXT("PKMOpticRail"));
}
inline void RemoveRail(AActor* Owner)
{
    if(auto* Part=FindRail(Owner))Part->DestroyComponent();
}
}
