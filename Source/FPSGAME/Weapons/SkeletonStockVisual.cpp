#include "../FPSGAMECharacter.h"
#include "A762Attachments.h"
#include "SVDAttachments.h"
#include "PKMAttachments.h"
#include "M16Attachments.h"
#include "AKMSovietCalibration.h"
#include "QBZ191Attachments.h"
#include "ASH12WeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
bool IsFactoryStock(FString Name)
{
    Name.ReplaceInline(TEXT(" "),TEXT("_"));
    return Name.Contains(TEXT("Classic_Stock"))||Name.Contains(TEXT("FactoryStock"))||Name==TEXT("M_M16_Stock");
}

FTransform ASHCheekRestMount(const USkeletalMesh* Asset)
{
    const auto& Ref=Asset->GetRefSkeleton();
    auto Bone=[&](const TCHAR* Name)
    {
        FTransform T=FTransform::Identity;
        for(int32 Index=Ref.FindBoneIndex(Name);Index!=INDEX_NONE;Index=Ref.GetParentIndex(Index))
            T=T*Ref.GetRefBonePose()[Index];
        return T;
    };
    const FTransform Root=Bone(TEXT("WPN_root")), Rear=Bone(TEXT("WPN_RearSight"));
    const FVector Forward=(Bone(TEXT("WPN_FrontSight")).GetLocation()-Rear.GetLocation()).GetSafeNormal();
    const FQuat Rotation=FRotationMatrix::MakeFromXZ(Forward,Rear.GetRotation().GetAxisZ()).ToQuat();
    // Author pivot in ASH's actual rail frame; Blender lateral Y reflects in FBX.
    const FTransform Mount(Rotation,Rear.GetLocation()+Rotation.RotateVector(FVector(-22.4f,-.02f,-6.5f)));
    return Mount.GetRelativeTransform(Root);
}
}

void AFPSGAMECharacter::SetGunsmithStock(const FString& Variant)
{
    if (IsPistolWeapon()) return;
    auto* Rifle=AKMViewmodel.Get();auto* Asset=Rifle?Rifle->GetSkeletalMeshAsset():nullptr;
    if(!Asset)return;
    const bool AKM=AKMSoviet::Matches(Rifle);
    const bool A762=A762WeaponAssets::Matches(Rifle);
    const bool SVD=SVDWeaponAssets::Matches(Rifle);
    const bool PKM=PKMLowpolyWeaponAssets::Matches(Rifle);
    const bool QR=Variant==TEXT("qr_performance");
    const bool Core=Variant==TEXT("core_stock");
    const bool Tactical=Variant==TEXT("tactical_telescopic");
    const bool CheekRest=bUseASH12&&Variant==TEXT("ash12_cheek_rest");
    const bool Enabled=(CheekRest||(!bUseASH12&&(Variant==TEXT("skeleton")||QR||Core||Tactical)&&(bUsingM4Infima||AKM||bUseQBZ191||A762||PKM||SVD)))&&bInventoryWeaponReady;
    const bool ReplaceFactory=Enabled&&!CheekRest;
    bool HasSection=false;
    for(const auto& Material:Asset->GetMaterials())HasSection|=IsFactoryStock(Material.MaterialSlotName.ToString());
    if(ReplaceFactory&&!HasSection){UE_LOG(LogTemp,Error,TEXT("SKELETON_STOCK: factory stock section missing on %s"),*Asset->GetPathName());return;}
    if(Enabled)
    {
        const TCHAR* StockPath=AKM?TEXT("/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock.SM_SkeletonStock"):TEXT("/Game/Weapons/ReferenceStock5080/SM_SkeletonStock.SM_SkeletonStock");
        if(QR)
            StockPath=AKM?TEXT("/Game/Weapons/QRPerformanceStock/Meshy20260913/AKM/SM_PerformanceStock.SM_PerformanceStock"):TEXT("/Game/Weapons/QRPerformanceStock/Meshy20260913/M4/SM_PerformanceStock.SM_PerformanceStock");
        else if(Core)
            StockPath=AKM?TEXT("/Game/Weapons/CoreStock20260914/Meshy0914005605/AKM/SM_CoreStock.SM_CoreStock"):TEXT("/Game/Weapons/CoreStock20260914/Meshy0914005605/M4/SM_CoreStock.SM_CoreStock");
        else if(Tactical)
            StockPath=AKM?TEXT("/Game/Weapons/TacticalTelescopicStock20260914/AKM/SM_TacticalTelescopicStock.SM_TacticalTelescopicStock"):TEXT("/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock.SM_TacticalTelescopicStock");
        auto* StockMesh=LoadObject<UStaticMesh>(nullptr,SVD?*SVDAttachments::MeshPath(Variant):PKM?*PKMAttachments::MeshPath(Variant):A762?*A762Attachments::MeshPath(Variant):bUseM16?*M16Attachments::MeshPath(Variant):CheekRest?ASH12WeaponAssets::CheekRestMeshPath:(bUseQBZ191?*QBZ191Attachments::MeshPath(Variant):StockPath));
        if(!StockMesh){UE_LOG(LogTemp,Error,TEXT("SKELETON_STOCK: mesh missing"));return;}
        if(!StockAttachment)
        {
        StockAttachment=NewObject<UStaticMeshComponent>(this,TEXT("SkeletonStock"));
        StockAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        StockAttachment->SetCastShadow(false);StockAttachment->bReceivesDecals=false;
        StockAttachment->SetupAttachment(Rifle,TEXT("WPN_root"));StockAttachment->RegisterComponent();
        }
        // Replace the mesh when changing options on an existing workbench/icon rig.
        if(StockAttachment->GetStaticMesh()!=StockMesh)StockAttachment->EmptyOverrideMaterials();
        StockAttachment->SetStaticMesh(StockMesh);
        // Author frame: +X toward buttpad. FBX reflects Blender Y; root inherits 100x scale.
        // Each receiver was measured in root space; the shared stock keeps physical size.
        StockMount=(bUseM16||bUseQBZ191||A762||PKM||SVD)?FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)):
            FTransform(FQuat(FVector::UpVector,-PI*.5f),AKM?FVector(.0008f,-.083f,.035f):FVector(0,-.0385f,.0725f),FVector(.01f));
        if(CheekRest)StockMount=ASHCheekRestMount(Asset);
        StockAttachment->SetRelativeTransform(StockMount);
    }
    bSkeletonStock=Enabled;if(StockAttachment)StockAttachment->SetVisibility(Enabled);
    if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Asset->GetMaterials().IsValidIndex(M)&&IsFactoryStock(Asset->GetMaterials()[M].MaterialSlotName.ToString()))Rifle->ShowMaterialSection(M,S,!ReplaceFactory,L);
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
