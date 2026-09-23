#pragma once
#include "SVDWeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace SVDAttachments
{
inline constexpr const TCHAR* Root=TEXT("/Game/Weapons/SVDDragunov20260922/Accessories20260923");
inline constexpr const TCHAR* WetMaterialsPath=TEXT("/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials");
inline FString MeshPath(const FString& Key)
{
    const bool Stock=Key==TEXT("skeleton")||Key==TEXT("core_stock")||Key==TEXT("qr_performance")||Key==TEXT("tactical_telescopic");
    const TCHAR* Folder=Stock?TEXT("/Game/Weapons/SVDDragunov20260922/StockAdapter20260923"):Root;
    return FString(Folder)+TEXT("/Meshes/SM_SVD_")+Key;
}
inline FString AnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    return FString::Printf(TEXT("%s/Animations/A_SVD_%s_%s"),Root,Family,Clip);
}
inline FTransform OpticMount(const FString& Variant)
{
    const double Along=Variant==TEXT("lpvo_1_6x")?.020:Variant==TEXT("prism_scope_2x")?.030:.035;
    return FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(.0000364,Along,.086),FVector(.01f));
}
inline const FVector MuzzleMount(.0000364133,.80120006,.0389192775);
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Part,const TCHAR* Key,bool Enabled)
{
    if(!Enabled){if(Part)Part->SetVisibility(false);return Part;}
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
    if(!Asset){if(Part)Part->SetVisibility(false);UE_LOG(LogTemp,Error,TEXT("SVD_ATTACHMENT missing %s"),Key);return Part;}
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Rifle,TEXT("WPN_root"));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    if(Part->GetStaticMesh()!=Asset)Part->EmptyOverrideMaterials();
    Part->SetStaticMesh(Asset);Part->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    Part->SetVisibility(true);return Part;
}
inline void FactorySections(USkeletalMeshComponent* Rifle,const TCHAR* Identity,bool Visible)
{
    if(!SVDWeaponAssets::Matches(Rifle))return;
    const auto* Asset=Rifle->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();if(!Render)return;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
    {
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
        if(Asset->GetMaterials().IsValidIndex(M)&&Asset->GetMaterials()[M].MaterialSlotName.ToString().Contains(Identity))
            Rifle->ShowMaterialSection(M,S,Visible,L);
    }
}
}
