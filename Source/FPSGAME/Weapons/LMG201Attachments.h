#pragma once
#include "LMG201WeaponAssets.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

namespace LMG201Attachments
{
inline constexpr const TCHAR* WetMaterialsPath=TEXT("/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials");
inline FString MeshPath(const FString& Key)
{
    return TEXT("/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_")+Key;
}
inline FString AnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    if(FCString::Strcmp(Clip,TEXT("reload"))==0||FCString::Strcmp(Clip,TEXT("reload_empty"))==0)
        return FString::Printf(TEXT("/Game/Weapons/LMG201/Magazine24/Animations/%s/A_LMG201_%s_%s"),Family,Family,Clip);
    return FString::Printf(TEXT("/Game/Weapons/LMG201/Accessories22/Animations/%s/A_LMG201_%s_%s"),Family,Family,Clip);
}
inline void LoadGripFamily(const TCHAR* Family,TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>>& Clips)
{
    // Original magazine clips and the new cloth-pouch reload have independent
    // contact paths, each returning to this grip family's own idle.
    for(const TCHAR* Name:{TEXT("idle"),TEXT("aim"),TEXT("fire"),TEXT("aim_fire"),TEXT("equip"),
        TEXT("inspect"),TEXT("reload"),TEXT("reload_empty")})
    {
        auto* Base=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::AnimationPath(Name));
        auto* Grip=LoadObject<UAnimSequence>(nullptr,*AnimationPath(Family,Name));
        if(Base&&Grip)Clips.Add(Base,Grip);
        else UE_LOG(LogTemp,Error,TEXT("LMG201: missing %s grip clip %s"),Family,Name);
    }
    for(const TCHAR* Name:{TEXT("reload"),TEXT("reload_empty")})
    {
        auto* Base=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::ClothAnimationPath(TEXT("base"),Name));
        auto* Grip=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::ClothAnimationPath(Family,Name));
        if(Base&&Grip)Clips.Add(Base,Grip);
        auto* DrumBase=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::DrumAnimationPath(TEXT("base"),Name));
        auto* DrumGrip=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::DrumAnimationPath(Family,Name));
        if(DrumBase&&DrumGrip)Clips.Add(DrumBase,DrumGrip);
    }
}
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,
    UStaticMeshComponent* Part,const TCHAR* Key,bool Enabled)
{
    if(!Enabled){if(Part)Part->SetVisibility(false);return Part;}
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
    if(!Mesh){if(Part)Part->SetVisibility(false);UE_LOG(LogTemp,Error,TEXT("LMG201: missing attachment %s"),Key);return Part;}
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,TEXT("WPN_root"));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    else if(Part->GetAttachParent()!=Rifle||Part->GetAttachSocketName()!=TEXT("WPN_root"))
        Part->AttachToComponent(Rifle,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    if(Part->GetStaticMesh()!=Mesh)Part->EmptyOverrideMaterials();
    Part->SetStaticMesh(Mesh);
    Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01)));
    Part->SetVisibility(true);return Part;
}
}
