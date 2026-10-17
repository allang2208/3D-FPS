#include "M870FurnitureAssets.h"
#include "Super90StockAssets.h"
#include "Super90ForegripAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

FString M870FurnitureAssets::ForegripFamily(const FString& Variant){return Super90ForegripAssets::Family(Variant);}
bool M870FurnitureAssets::SupportsStock(const FString& Variant){return Super90StockAssets::Supports(Variant);}
FString M870FurnitureAssets::MeshPath(const FString& Part)
{
    if(Part==TEXT("factory_stock"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_factory_stock");
    if(Part==TEXT("factory_reargrip"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_factory_reargrip");
    if(Part==TEXT("skeleton"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_skeleton");
    if(Part==TEXT("core_stock"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_core_stock");
    if(Part==TEXT("qr_performance"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_qr_performance");
    if(Part==TEXT("tactical_telescopic"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_tactical_telescopic");
    if(Part==TEXT("legendary_adjustable_tactical_stock"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_legendary_adjustable_tactical_stock");
    if(Part==TEXT("vertical"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_vertical");
    if(Part==TEXT("tactical_vertical"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_tactical_vertical");
    if(Part==TEXT("canted"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_canted");
    if(Part==TEXT("prism"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_prism");
    if(Part==TEXT("angled"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_angled");
    return FString();
}
FString M870FurnitureAssets::ProfilePath(FName Family)
{
    if(Family==TEXT("vertical"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_vertical");
    if(Family==TEXT("canted"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_canted");
    if(Family==TEXT("prism"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_prism");
    if(Family==TEXT("angled"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_angled");
    return FString();
}
FString M870FurnitureAssets::InstalledPart(const UStaticMeshComponent* Component)
{
    const UStaticMesh* Mesh=Component?Component->GetStaticMesh().Get():nullptr;
    if(!Mesh||!Mesh->GetPathName().StartsWith(TEXT("/Game/Weapons/M870/CommonFurniture20261016/")))return FString();
    return Mesh->GetName().RightChop(8);
}
namespace
{
UStaticMeshComponent* Part(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,UStaticMesh* Mesh,FName Bone)
{
    if(!Mesh||!Host||!Host->GetSkeletalMeshAsset())
    {
        if(Existing)Existing->DestroyComponent();
        return nullptr;
    }
    if(!Existing)
    {
        Existing=NewObject<UStaticMeshComponent>(Owner);Owner->AddInstanceComponent(Existing);
        Existing->SetupAttachment(Host,Bone);Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);Existing->bReceivesDecals=false;Existing->RegisterComponent();
    }
    Existing->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,Bone);
    Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
    if(Existing->GetStaticMesh()!=Mesh)Existing->EmptyOverrideMaterials();
    Existing->SetStaticMesh(Mesh);
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();FTransform Bind=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(Bone);I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bind=Bind*Ref.GetRefBonePose()[I];
    Existing->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bind));Existing->SetVisibility(true);
    return Existing;
}
}
void M870FurnitureAssets::ConfigureRear(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent*& Stock,UStaticMeshComponent*& Grip,
    const FString& StockVariant,bool Enabled)
{
    auto* Asset=Host?Host->GetSkeletalMeshAsset():nullptr;if(!Asset)return;
    const bool HasFactory=Asset->GetMaterials().ContainsByPredicate([](const FSkeletalMaterial& M)
        {return M.MaterialSlotName==TEXT("M870_FactoryFurniture");});
    const bool Replace=Enabled&&HasFactory&&SupportsStock(StockVariant);
    UStaticMesh* StockMesh=Replace?LoadObject<UStaticMesh>(nullptr,*MeshPath(StockVariant)):nullptr;
    UStaticMesh* GripMesh=Replace?LoadObject<UStaticMesh>(nullptr,*MeshPath(TEXT("factory_reargrip"))):nullptr;
    const bool Installed=StockMesh&&GripMesh;
    Stock=Part(Owner,Host,Stock,Installed?StockMesh:nullptr,TEXT("WPN_root"));
    Grip=Part(Owner,Host,Grip,Installed?GripMesh:nullptr,TEXT("WPN_root"));
    if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Asset->GetMaterials().IsValidIndex(M)&&Asset->GetMaterials()[M].MaterialSlotName==TEXT("M870_FactoryFurniture"))
                    Host->ShowMaterialSection(M,S,!Installed,L);
            }
}
UStaticMeshComponent* M870FurnitureAssets::ConfigureForegrip(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Family,bool Enabled)
{
    return Part(Owner,Host,Existing,Enabled?LoadObject<UStaticMesh>(nullptr,*MeshPath(Family)):nullptr,TEXT("WPN_bolt"));
}
