#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "QBZ191Mounts.inl"

namespace QBZ191Attachments
{
inline FString MeshPath(const FString& Key)
{
    return TEXT("/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_")+Key;
}
inline UStaticMeshComponent* ConfigureFitted(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,const FString& Key,bool Enabled,const TCHAR* Bone=TEXT("WPN_root"))
{
    if(Part)Part->SetVisibility(false);
    if(!Enabled)return Part;
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));if(!Mesh)return Part;
    if(!Part){Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,Bone);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();}
    Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));Part->SetVisibility(true);return Part;
}
inline FString AnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    const FString Kind=FCString::Strcmp(Clip,TEXT("equip"))==0?TEXT("equip_charge"):Clip;
    const TCHAR* Revision=(Kind.Contains(TEXT("reload")) || Kind==TEXT("equip_charge"))?TEXT("Attachments20260913"):TEXT("Refined20260913");
    return FString::Printf(TEXT("/Game/Weapons/QBZ191/%s/Animations/%s/A_QBZ191_%s_%s"),Revision,Family,Family,*Kind);
}
inline FTransform OpticMount(const FString& Variant)
{
    // Source rail crown, in the private QBZ bone's metre frame. Shared optical
    // meshes are centimetres, with X forward and their saddle at Z=0.
    const float Along=Variant==TEXT("lpvo_1_6x")?.09f:Variant==TEXT("prism_scope_2x")?.06f:.08f;
    return FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(.000688f,Along,.096473f),FVector(.01f));
}
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,const TCHAR* Family,bool Enabled)
{
    if(Part)Part->SetVisibility(false);
    if(!Enabled)return Part;
    const FString Key(Family);
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));if(!Mesh)return Part;
    if(!Part){Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,TEXT("WPN_root"));Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();}
    Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(QBZ191Mounts::Underbarrel(Key));Part->SetVisibility(true);return Part;
}
}
