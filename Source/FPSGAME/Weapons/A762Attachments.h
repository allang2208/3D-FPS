#pragma once
#include "A762WeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

// Fitted assets retain the accepted AKM contact frame on the shared Manny rig.
namespace A762Attachments
{
inline FString MeshPath(const FString& Key)
{
    return TEXT("/Game/Weapons/A762/Accessories05/Meshes/SM_A762_")+Key;
}
inline FString AnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/A762/Accessories05/Animations/%s/A_A762_%s_%s"),Family,Family,Clip);
}
inline FTransform OpticMount(const FString& Variant)
{
    // Seat the existing clamp on the measured rail crown; eye relief is separate
    // from optical center and remains calibrated by OpticLocalAimPoint().
    const double Along=Variant==TEXT("lpvo_1_6x")?.105:Variant==TEXT("prism_scope_2x")?.078:
        Variant==TEXT("panoramic_red_dot")?.065:.060;
    return FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(.00056,Along,.0995),FVector(.01));
}
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,
    const TCHAR* Key,bool Enabled,FName Bone=TEXT("WPN_root"))
{
    if(!Enabled){if(Part)Part->SetVisibility(false);return Part;}
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
    if(!Mesh){if(Part)Part->SetVisibility(false);UE_LOG(LogTemp,Error,TEXT("A762_ATTACHMENT: missing %s"),Key);return Part;}
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,Bone);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    if(Part->GetStaticMesh()!=Mesh)Part->EmptyOverrideMaterials();
    Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01)));
    Part->SetVisibility(true);return Part;
}
}
