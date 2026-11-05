#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "M24Attachments.h"

namespace SniperSkeletonStock
{
inline constexpr const TCHAR* Id=TEXT("sniper_skeleton_stock");
inline constexpr const TCHAR* M24CarbonId=TEXT("m24_carbon_spine_stock");
inline constexpr const TCHAR* M24CarbonMeshPrefix=TEXT("/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_");
inline FString Family(const FString& Definition)
{
    if(Definition==TEXT("ue_m24"))return TEXT("M24");
    if(Definition==TEXT("ue_svd"))return TEXT("SVD");
    if(Definition==TEXT("ue_svch"))return TEXT("SVCH");
    return FString();
}
inline bool Supports(const FString& Definition){return !Family(Definition).IsEmpty();}
inline constexpr const TCHAR* M24Root=TEXT("/Game/Weapons/M24/ReceiverGripRebuild20261031");
inline bool IsReplacement(const FString& Definition,const FString& Variant)
{return (Variant==Id&&Supports(Definition))||(Definition==TEXT("ue_m24")&&Variant==M24CarbonId);}
inline FString MeshPath(const FString& Definition,bool Advanced=false,const FString& Variant=Id)
{
    if(Definition==TEXT("ue_m24"))
    {
        const FString Prefix=Variant==M24CarbonId?FString(M24CarbonMeshPrefix):FString(M24Root)+TEXT("/Meshes/SM_M24_ReceiverStock_");
        return Prefix+(Advanced?TEXT("Advanced"):TEXT("Native"));
    }
    return TEXT("/Game/Weapons/SkeletonSniperStock20261031/Meshes/SM_SniperSkeleton_")+Family(Definition);
}
inline bool UsesM24DirectStock(const UStaticMeshComponent* Part)
{
    if(!Part||!Part->IsVisible()||!Part->GetStaticMesh())return false;
    const FString Path=Part->GetStaticMesh()->GetPathName();
    return Path.StartsWith(FString(M24Root)+TEXT("/Meshes/SM_M24_ReceiverStock_"))||Path.StartsWith(M24CarbonMeshPrefix);
}
inline FString M24GripMeshPath(const FString& Variant)
{
    const TCHAR* Suffix=Variant==TEXT("balanced_reargrip")?TEXT("balanced"):Variant==TEXT("phantom_reargrip")?TEXT("phantom"):Variant==TEXT("stable_antislip_reargrip")?TEXT("stable"):TEXT("Default");
    return FString(M24Root)+TEXT("/Meshes/SM_M24_PistolGrip_")+Suffix;
}
inline FString M24FrontMeshPath(){return FString(M24Root)+TEXT("/Meshes/SM_M24_AdvancedFront_ForIndependentGrip");}
inline FString M24ProfilePath(FName Family){return FString(M24Root)+TEXT("/Profiles/DA_M24_")+Family.ToString();}
// Native M24 component units. Preserve the accepted framing while the hand
// moves onto a corrected pistol-grip contact (mesh scale is applied by framing).
inline const FVector M24PresentationHand(.037195854,.080805898,.026502814);
inline FName M24GripFamily(FName MeshName,bool Extended)
{
    if(MeshName==TEXT("SM_M24_PistolGrip_balanced"))return Extended?TEXT("skeleton_mag10_balanced"):TEXT("skeleton_base_balanced");
    if(MeshName==TEXT("SM_M24_PistolGrip_phantom"))return Extended?TEXT("skeleton_mag10_phantom"):TEXT("skeleton_base_phantom");
    if(MeshName==TEXT("SM_M24_PistolGrip_stable"))return Extended?TEXT("skeleton_mag10_stable"):TEXT("skeleton_base_stable");
    return Extended?TEXT("skeleton_mag10"):TEXT("skeleton_base");
}
inline FName M24GripFamily(const UStaticMeshComponent* Part,bool Extended)
{return M24GripFamily(Part&&Part->GetStaticMesh()?Part->GetStaticMesh()->GetFName():NAME_None,Extended);}
inline FName M24GripFamilyForVariant(const FString& Variant,bool Extended)
{return M24GripFamily(FName(*FPaths::GetBaseFilename(M24GripMeshPath(Variant))),Extended);}
inline FString M24GripVariant(const UStaticMeshComponent* Part)
{
    if(!Part||!Part->IsVisible())return FString();
    const FString Mesh=Part->GetStaticMesh()?Part->GetStaticMesh()->GetPathName():FString();
    auto* Surface=Part->GetMaterial(0);
    if(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Surface))Surface=Dynamic->Parent;
    const FString Material=Surface?Surface->GetPathName():FString();
    for(const TCHAR* Key:{TEXT("phantom_reargrip"),TEXT("stable_antislip_reargrip"),TEXT("balanced_reargrip")})
        if(Mesh.Contains(Key)||Mesh.StartsWith(M24GripMeshPath(Key)+TEXT("."))||Material.Contains(Key))return Key;
    return FString();
}
inline bool IsFactorySlot(FName Slot)
{return Slot==TEXT("M24_FactoryStock")||Slot==TEXT("M24_FactoryChassis")||Slot==TEXT("M24_FactoryRearSeat")||Slot==TEXT("SVD_FactoryStock")||Slot==TEXT("KVInhibitor_stock");}
inline void FactorySections(USkeletalMeshComponent* Host,bool Visible)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return;
    const auto* Asset=Host->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();if(!Render)return;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
    {
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
        if(Asset->GetMaterials().IsValidIndex(M)&&IsFactorySlot(Asset->GetMaterials()[M].MaterialSlotName))
        {
            const int32 Front=Host->GetMaterialIndex(TEXT("M24_FactoryFront"));
            const bool Show=Visible&&(Asset->GetMaterials()[M].MaterialSlotName!=TEXT("M24_FactoryRearSeat")||Front==INDEX_NONE||Host->IsMaterialSectionShown(Front,L));
            Host->ShowMaterialSection(M,S,Show,L);
        }
    }
}
inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Part,const FString& Definition,bool Advanced=false,const FString& Variant=Id)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return Part;
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Definition,Advanced,Variant));if(!Mesh)return Part;
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);
        Part->SetupAttachment(Host,TEXT("WPN_root"));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    else Part->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    if(Part->GetStaticMesh()!=Mesh)Part->EmptyOverrideMaterials();
    Part->SetStaticMesh(Mesh);
    Part->SetRelativeTransform(Definition==TEXT("ue_m24")?M24Attachments::Mount(Host):FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    Part->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);Part->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
    Part->SetVisibility(Host->IsVisible());Part->SetHiddenInGame(Host->bHiddenInGame);
    FactorySections(Host,false);return Part;
}
inline UStaticMeshComponent* ConfigureM24Grip(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Part,const FString& Variant)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return Part;
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*M24GripMeshPath(Variant));
    if(!Mesh)return Part;
    if(!Part)
    {
        Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Host,TEXT("WPN_root"));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();
    }
    else Part->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    Part->EmptyOverrideMaterials();Part->SetStaticMesh(Mesh);
    Part->SetRelativeTransform(M24Attachments::Mount(Host));
    Part->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);Part->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
    Part->SetVisibility(Host->IsVisible());Part->SetHiddenInGame(Host->bHiddenInGame);return Part;
}
}
