#pragma once
#include "AKMSovietCalibration.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
namespace AKMAttachment
{
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,const TCHAR* Key,bool Enabled,FName Bone=TEXT("WPN_root"))
{
    if(!Enabled){if(Part)Part->SetVisibility(false);return Part;}
    const TCHAR* Directory=FCString::Strcmp(Key,TEXT("optic"))==0?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_AKM_"):TEXT("/Game/Weapons/AKMIntegration/SovietFab/Attachments/SM_AKM_");
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*(FString(Directory)+Key));
    if(!Mesh){UE_LOG(LogTemp,Error,TEXT("AKM_ATTACHMENT missing %s"),Key);return Part;}
    if(!Part){Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,Bone);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();}
    Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));Part->SetVisibility(true);return Part;
}
inline const FVector HoloPointCM(.08,4.846218,16.475324);
}
