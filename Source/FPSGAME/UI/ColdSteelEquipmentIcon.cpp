#include "ColdSteelWeaponIcons.h"
#include "ColdSteelEquipmentIconSource.h"
#include "FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/StaticMesh.h"
#include "Rendering/StaticMeshVertexBuffer.h"
#include "Materials/MaterialInterface.h"
#include "Engine/World.h"

// 刚性装备（登山包等挂 spine_03 的静态件）的图标就是穿在身上的那个网格：
// player_body.json 的 world_static_mesh 是显示源的唯一事实，图标棚复用同一条目，
// 避免装备外观和背包贴图各画一份以后漂移。
bool UColdSteelWeaponIcons::PrepareEquipment(const FColdSteelItem& Item)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_PrepareEquipment);
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.EquipmentAssembly"));
    const FString& Definition=Item.Definition;
    const FSoftObjectPath MeshPath=ColdSteelEquipmentIconMesh(Item);
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
    const FBoxSphereBounds Local=Asset->GetBounds();
    // Default backpack front is -Y. Other equipment supplies its display-only
    // orientation; the spellbook needs roll to put its -Y long axis upright.
    const FQuat Orient=FRotator(ColdSteelInventory::Number(Item,TEXT("ue_icon_pitch"),0),
        ColdSteelInventory::Number(Item,TEXT("ue_icon_yaw"),-90),
        ColdSteelInventory::Number(Item,TEXT("ue_icon_roll"),0)).Quaternion();
    const FTransform Pose(Orient,-(Orient.RotateVector(Local.Origin)),FVector::OneVector);
    MaterialMesh->SetWorldTransform(Pose);
    // 圆角装备摸不到旋转后包围盒的角：AABB 取景会让 91% 填充的合同落成约七成。
    // 相机正对 +X，画面水平/竖直即世界 Y/Z——直接投顶点算实际剪影范围。
    FBox Silhouette(ForceInit);
    if(const auto* RenderData=Asset->GetRenderData();RenderData&&!RenderData->LODResources.IsEmpty())
    {
        const auto& Positions=RenderData->LODResources[0].VertexBuffers.PositionVertexBuffer;
        const int32 Count=Positions.GetNumVertices();
        for(int32 Index=0;Index<Count;++Index)
            Silhouette+=Pose.TransformPosition(FVector(Positions.VertexPosition(Index)));
    }
    const FBox Bounds=Silhouette.IsValid?Silhouette:Local.GetBox().TransformBy(MaterialMesh->GetComponentTransform());
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(MaterialMesh);
    // 画布按占格推导：登山包 3x3，所以是 320x320 方幅。
    const FIntPoint Grid=ColdSteelInventory::BaseFootprint(Item);
    const int32 Width=FMath::Max(1,FMath::RoundToInt(320.f*float(Grid.X)/FMath::Max(1,Grid.Y)));
    if(Target->SizeX!=Width||Target->SizeY!=320)Target->ResizeTarget(Width,320);
    const float Aspect=float(Width)/320.f;
    // 同一取景规则：主轴填满 91%，轮廓中心在画幅中心。
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
    UE_LOG(LogTemp,Display,TEXT("EquipmentIcon: prepare def=%s mesh=%s slots=%d size=%s"),*Definition,*Asset->GetName(),MaterialMesh->GetNumMaterials(),*Size.ToString());
    return true;
}
