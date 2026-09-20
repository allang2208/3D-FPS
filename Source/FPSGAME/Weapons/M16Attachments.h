#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

// Authoring: SourceAssets/M16UniversalAttachments20260920. Root-space bodies
// carry their measured installation; magazine assets retain mesh bind space.
namespace M16Attachments
{
inline FString MeshPath(const FString& Key)
{
    return FString::Printf(TEXT("/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_%s.SM_M16_%s"),*Key,*Key);
}
inline FString AnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/%s/A_M16_%s_%s.A_M16_%s_%s"),Family,Family,Clip,Family,Clip);
}
inline FTransform RootMount()
{
    return FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
}
inline FTransform OpticMount()
{
    // M16 carry-handle saddle. +X optic axis maps to root +Y; no sight-line tilt.
    return FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(-.000038f,.105f,.1815f),FVector(.01f));
}
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,
    UStaticMeshComponent* Part,const TCHAR* Key,bool bEnabled)
{
    if(Part)Part->SetVisibility(false);
    if(!bEnabled||!Rifle)return Part;
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
    if(!Mesh)return Part;
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);
        Part->SetupAttachment(Rifle,TEXT("WPN_root"));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    if(Part->GetStaticMesh()!=Mesh)Part->EmptyOverrideMaterials();
    Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(RootMount());Part->SetVisibility(true);
    return Part;
}
}
