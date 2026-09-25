#include "ColdSteelWeaponIcons.h"
#include "FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "../Production/ProductionHarvestAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/World.h"

// 生产材料（矿石、金属锭、石块）没有枪的装配骨架也没有配件，图标就是拾取物本身。
// 所以这条通道直接挂 AColdSteelPickup::InstallProductionMaterial 用的同一份网格与
// 同一份分种材质实例，并按同一尺寸归一化：背包里看到的和地上掉的是同一个东西。
bool UColdSteelWeaponIcons::PrepareMaterial(const FColdSteelItem& Item)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_PrepareMaterial);
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.MaterialAssembly"));
    const FString& Definition=Item.Definition;
    const FSoftObjectPath MeshPath=ProductionHarvestAssets::PickupMesh(Definition,0);
    auto* Asset=MeshPath.IsValid()?LoadObject<UStaticMesh>(nullptr,*MeshPath.ToString()):nullptr;
    if(!Asset)return false;
    if(!MaterialMesh)
    {
        MaterialMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        MaterialMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        MaterialMesh->SetForcedLodModel(1);
        Studio->AddComponent(MaterialMesh,FTransform::Identity);
    }
    MaterialMesh->EmptyOverrideMaterials();
    MaterialMesh->SetStaticMesh(Asset);
    // 与世界掉落一致：最长边归一到 24 cm，并把网格中心移到原点。
    const FBoxSphereBounds Local=Asset->GetBounds();
    const float Scale=24.f/FMath::Max(1.f,2.f*float(Local.BoxExtent.GetMax()));
    // 道具用固定 3/4 展示角，不像武器那样取正侧视：配件轮廓对武器才是可读信息，
    // 而金属锭的长轴原本正对相机（拍出来是一张平板），平躺的石块侧视只剩一条边。
    // 先绕 Z 偏航把长轴转到画面横向，再绕 Y 俯仰露出顶面；取景按旋转后的包围盒算。
    const FQuat Orient=FQuat(FVector::YAxisVector,FMath::DegreesToRadians(22.f))
        *FQuat(FVector::ZAxisVector,FMath::DegreesToRadians(30.f));
    const FTransform Pose(Orient,-(Orient.RotateVector(Local.Origin*Scale)),FVector(Scale));
    MaterialMesh->SetWorldTransform(Pose);
    if(const auto MaterialPath=ProductionHarvestAssets::PickupMaterial(Definition);MaterialPath.IsValid())
    {
        // 分矿种色调／分金属颜色实例。取不到就退回网格自带材质，不因此判失败。
        if(auto* Override=LoadObject<UMaterialInterface>(nullptr,*MaterialPath.ToString()))
        {
            MaterialMesh->SetMaterial(0,Override);
            UE_LOG(LogTemp,Display,TEXT("MaterialIcon: override def=%s applied=%s class=%s"),*Definition,
                *GetNameSafe(MaterialMesh->GetMaterial(0)),*Override->GetClass()->GetName());
        }
        else UE_LOG(LogTemp,Warning,TEXT("MaterialIcon: 材质实例不可用 def=%s path=%s"),*Definition,*MaterialPath.ToString());
    }
    const FBox Bounds=Local.GetBox().TransformBy(MaterialMesh->GetComponentTransform());
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(MaterialMesh);
    // 画布与其余通道同规则：按作者占格推导。材料都是 1x1，所以是 320x320 方幅。
    const FIntPoint Grid=ColdSteelInventory::BaseFootprint(Item);
    const int32 Width=FMath::Max(256,FMath::RoundToInt(320.f*float(Grid.X)/FMath::Max(1,Grid.Y)));
    if(Target->SizeX!=Width||Target->SizeY!=320)Target->ResizeTarget(Width,320);
    const float Aspect=float(Width)/320.f;
    // 取景沿用近战口径：主轴填满 91%，轮廓中心落在画幅中心。
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/.91f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();
    CaptureMeshes.Add(MaterialMesh);
    for(int32 Slot=0;Slot<MaterialMesh->GetNumMaterials();++Slot)
        if(auto* Material=MaterialMesh->GetMaterial(Slot))CaptureMaterials.AddUnique(Material);
    for(UMaterialInterface* Material:CaptureMaterials)
    {
        TArray<UTexture*> UsedTextures;Material->GetUsedTextures(UsedTextures);
        for(auto* Texture:UsedTextures)if(Texture)CaptureTextures.AddUnique(Texture);
    }
    RequestCaptureTextureMips();Studio->GetWorld()->SendAllEndOfFrameUpdates();
    UE_LOG(LogTemp,Display,TEXT("MaterialIcon: prepare def=%s mesh=%s slots=%d scale=%.3f size=%s"),*Definition,*Asset->GetName(),MaterialMesh->GetNumMaterials(),Scale,*Size.ToString());
    return true;
}
