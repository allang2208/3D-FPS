#pragma once
#include "AKMSovietCalibration.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
namespace AKMAttachment
{
inline FString GripAnimationPath(const TCHAR* Key,const TCHAR* Clip)
{
    const TCHAR* Family=FCString::Strcmp(Key,TEXT("vertical"))==0?TEXT("GripVRENatural"):
        (FCString::Strcmp(Key,TEXT("canted"))==0||FCString::Strcmp(Key,TEXT("prism"))==0)?TEXT("GripVREExtensions"):TEXT("GripErgonomic");
    return FString::Printf(TEXT("/Game/Weapons/AKMIntegration/SovietFab/%s/%s/A_AKM_%s_%s"),Family,Key,Key,Clip);
}
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,const TCHAR* Key,bool Enabled,FName Bone=TEXT("WPN_root"))
{
    if(!Enabled){if(Part)Part->SetVisibility(false);return Part;}
    const bool NewGrip=FCString::Strcmp(Key,TEXT("canted"))==0||FCString::Strcmp(Key,TEXT("vertical"))==0||FCString::Strcmp(Key,TEXT("angled"))==0;
    const bool ReceiverFinish=FCString::Strcmp(Key,TEXT("vertical"))==0||FCString::Strcmp(Key,TEXT("canted"))==0||
        FCString::Strcmp(Key,TEXT("prism"))==0||FCString::Strcmp(Key,TEXT("drum"))==0||
        FCString::Strcmp(Key,TEXT("suppressor"))==0||FCString::Strcmp(Key,TEXT("brake"))==0||FCString::Strcmp(Key,TEXT("titanium_brake"))==0;
    const TCHAR* Directory=ReceiverFinish?TEXT("/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_"):NewGrip?TEXT("/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_"):FCString::Strcmp(Key,TEXT("optic"))==0?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_AKM_"):TEXT("/Game/Weapons/AKMIntegration/SovietFab/Attachments/SM_AKM_");
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*(FString(Directory)+Key+(FCString::Strcmp(Key,TEXT("canted"))==0?TEXT("_CompactMount"):TEXT(""))));
    if(!Mesh){UE_LOG(LogTemp,Error,TEXT("AKM_ATTACHMENT missing %s"),Key);return Part;}
    if(!Part){Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,Bone);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();}
    Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));Part->SetVisibility(true);return Part;
}
inline const FVector HoloPointCM(.08,4.846218,16.475324);
}
