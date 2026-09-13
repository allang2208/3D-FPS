#include "../FPSGAMECharacter.h"
#include "AKMSovietCalibration.h"
#include "QBZ191Attachments.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
bool IsFactoryStock(FString Name)
{
    Name.ReplaceInline(TEXT(" "),TEXT("_"));
    return Name.Contains(TEXT("Classic_Stock"))||Name.Contains(TEXT("FactoryStock"));
}
}

void AFPSGAMECharacter::SetGunsmithStock(const FString& Variant)
{
    auto* Rifle=AKMViewmodel.Get();auto* Asset=Rifle?Rifle->GetSkeletalMeshAsset():nullptr;
    if(!Asset)return;
    const bool AKM=AKMSoviet::Matches(Rifle);
    const bool QR=Variant==TEXT("qr_performance");
    const bool Enabled=(Variant==TEXT("skeleton")||QR)&&(bUsingM4Infima||AKM)&&bInventoryWeaponReady;
    bool HasSection=false;
    for(const auto& Material:Asset->GetMaterials())HasSection|=IsFactoryStock(Material.MaterialSlotName.ToString());
    if(Enabled&&!HasSection){UE_LOG(LogTemp,Error,TEXT("SKELETON_STOCK: factory stock section missing on %s"),*Asset->GetPathName());return;}
    if(Enabled)
    {
        const TCHAR* StockPath=QR
            ?(AKM?TEXT("/Game/Weapons/QRPerformanceStock/AKM/SM_QRPerformanceStock.SM_QRPerformanceStock"):TEXT("/Game/Weapons/QRPerformanceStock/M4/SM_QRPerformanceStock.SM_QRPerformanceStock"))
            :(AKM?TEXT("/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock.SM_SkeletonStock"):TEXT("/Game/Weapons/ReferenceStock5080/SM_SkeletonStock.SM_SkeletonStock"));
        auto* StockMesh=LoadObject<UStaticMesh>(nullptr,bUseQBZ191?*QBZ191Attachments::MeshPath(Variant):StockPath);
        if(!StockMesh){UE_LOG(LogTemp,Error,TEXT("SKELETON_STOCK: mesh missing"));return;}
        if(!StockAttachment)
        {
        StockAttachment=NewObject<UStaticMeshComponent>(this,TEXT("SkeletonStock"));
        StockAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        StockAttachment->SetCastShadow(false);StockAttachment->bReceivesDecals=false;
        StockAttachment->SetupAttachment(Rifle,TEXT("WPN_root"));StockAttachment->RegisterComponent();
        }
        // Replace the mesh when changing options on an existing workbench/icon rig.
        StockAttachment->SetStaticMesh(StockMesh);
        // Author frame: +X toward buttpad. FBX reflects Blender Y; root inherits 100x scale.
        // Each receiver was measured in root space; the shared stock keeps physical size.
        StockMount=bUseQBZ191?FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)):
            FTransform(FQuat(FVector::UpVector,-PI*.5f),AKM?FVector(.0008f,-.083f,.035f):FVector(0,-.0385f,.0725f),FVector(.01f));
        StockAttachment->SetRelativeTransform(StockMount);
    }
    bSkeletonStock=Enabled;if(StockAttachment)StockAttachment->SetVisibility(Enabled);
    if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Asset->GetMaterials().IsValidIndex(M)&&IsFactoryStock(Asset->GetMaterials()[M].MaterialSlotName.ToString()))Rifle->ShowMaterialSection(M,S,!Enabled,L);
            }
}
bool AFPSGAMECharacter::HasSkeletonStock() const {return bSkeletonStock&&StockAttachment&&StockAttachment->IsVisible();}
bool AFPSGAMECharacter::ValidateStockAttachment() const
{
    auto* Rifle=AKMViewmodel.Get();const auto* Asset=Rifle?Rifle->GetSkeletalMeshAsset():nullptr;if(!Asset)return false;
    bool Found=false;
    for(int32 M=0;M<Asset->GetMaterials().Num();++M)if(IsFactoryStock(Asset->GetMaterials()[M].MaterialSlotName.ToString()))
    {Found=true;if(Rifle->IsMaterialSectionShown(M,0)==bSkeletonStock)return false;}
    if(!Found)return false;
    if(!bSkeletonStock)return !StockAttachment||!StockAttachment->IsVisible();
    if(!HasSkeletonStock()||StockAttachment->GetAttachSocketName()!=TEXT("WPN_root"))return false;
    const FTransform Expected=StockMount*Rifle->GetSocketTransform(TEXT("WPN_root"));
    return StockAttachment->GetComponentLocation().Equals(Expected.GetLocation(),.025f)
        &&StockAttachment->GetComponentQuat().AngularDistance(Expected.GetRotation())<.002f
        &&StockAttachment->GetComponentScale().Equals(FVector::OneVector,.005f);
}
