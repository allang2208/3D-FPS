#include "VoxelBuildIcons.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
    // Icon render size: a 104 px card image stays sharp up to ~200% DPI.
    constexpr int32 IconSize=256;
    // One fixed 3/4 view for every entry: the camera looks along this rotation at the framed object.
    const FRotator IconView(-18.f,-35.f,0.f);
    // Largest bounding-box edge maps to this fraction of the orthographic frame, so every card shows
    // its construction at the same size.
    constexpr float IconFillFraction=.78f;
    // 单格 1×1 体素块按一半大小绘制：20 cm 方块与 1 m 地块／1×5 直线同框时不再显得一样大
    // （2026-09-17 用户要求）。只影响单格请求，材质行缩略图与「单格」卡片同样适用。
    constexpr float SingleBlockFrameScale=.5f;
    // 16 was one short: the marble row alone shows 5 shapes + 9 pieces, plus the three material
    // row thumbnails, so visible entries exceeded the cap and the eviction pass had to run while
    // every key was pinned. Cards that lost their icon stayed empty (2026-09-17 user report:
    // pavilion and the 1 m / 3 m rails). Kept above the worst case instead of one short.
    constexpr int32 MaxCachedIcons=32;
    /** How many times a key may be re-queued after a failed build before it is given up on. */
    constexpr int32 MaxBuildAttempts=3;
    /** 失败计数的键。只在失败时递增、成功后清零；成功也计数的旧写法会让被回收后重建的键
     *  在 3 轮后永久拒绝（2026-09-19 审计）。File-scope on purpose: a Live Coding patch may
     *  reset it, which only costs one extra retry. */
    static TMap<FString,int32> GIconAttempts;
    /** 已放弃的键：放弃时记录一次警告，之后静默跳过，避免抽屉每帧重排时刷日志。 */
    static TSet<FString> GIconGaveUp;
    const TCHAR* ResolvedMaterialPath=TEXT("/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved.M_WeaponPreviewResolved");
    const TCHAR* StudioSkyPath=TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment");
    const TCHAR* DefaultStoneMesh=TEXT("/Game/Building/Voxels/Rounded/SM_Voxel20_Stone.SM_Voxel20_Stone");
}

FString UVoxelBuildIcons::KeyForShape(FName MaterialId,int32 Shape)
{
    return FString::Printf(TEXT("shape:%s:%d"),*MaterialId.ToString(),Shape);
}

FString UVoxelBuildIcons::KeyForPiece(FName PieceId)
{
    return FString::Printf(TEXT("piece:%s"),*PieceId.ToString());
}

void UVoxelBuildIcons::Request(const FVoxelBuildIconRequest& Request)
{
    if(Request.Key.IsEmpty()||Request.Mesh.IsNull())return;
    if(Materials.Contains(Request.Key)||Pending.Contains(Request.Key))return;
    if(GIconGaveUp.Contains(Request.Key))return;
    Pending.Add(Request.Key);
    Queue.Add({Request});
}

UMaterialInterface* UVoxelBuildIcons::Find(const FString& Key) const
{
    if(const auto* Found=Materials.Find(Key))if(*Found){Uses.Add(Key,++Serial);return *Found;}
    return nullptr;
}

void UVoxelBuildIcons::SetVisibleKeys(const TSet<FString>& Keys)
{
    // 控件每帧都会调用；内容不变时不重写集合，避免每帧重建哈希表。
    if(VisibleKeys.Num()==Keys.Num())
    {
        bool bSame=true;
        for(const FString& Key:Keys)if(!VisibleKeys.Contains(Key)){bSame=false;break;}
        if(bSame)return;
    }
    VisibleKeys=Keys;
}

void UVoxelBuildIcons::ReleaseEntry(const FString& Key)
{
    if(auto* Target=ColorTargets.Find(Key))if(*Target)(*Target)->ReleaseResource();
    if(auto* Target=CoverageTargets.Find(Key))if(*Target)(*Target)->ReleaseResource();
    ColorTargets.Remove(Key);CoverageTargets.Remove(Key);Materials.Remove(Key);Uses.Remove(Key);
}

void UVoxelBuildIcons::Deinitialize()
{
    Queue.Reset();Pending.Reset();GIconGaveUp.Reset();GIconAttempts.Reset();VisibleKeys.Reset();
    if(ColorCapture){ColorCapture->TextureTarget=nullptr;if(Studio.IsValid())Studio->RemoveComponent(ColorCapture);ColorCapture->DestroyComponent();ColorCapture=nullptr;}
    if(CoverageCapture){CoverageCapture->TextureTarget=nullptr;if(Studio.IsValid())Studio->RemoveComponent(CoverageCapture);CoverageCapture->DestroyComponent();CoverageCapture=nullptr;}
    for(TPair<FString,TObjectPtr<UTextureRenderTarget2D>>& Entry:ColorTargets)if(Entry.Value)Entry.Value->ReleaseResource();
    for(TPair<FString,TObjectPtr<UTextureRenderTarget2D>>& Entry:CoverageTargets)if(Entry.Value)Entry.Value->ReleaseResource();
    ColorTargets.Reset();CoverageTargets.Reset();Materials.Reset();Uses.Reset();
    if(StudioFill&&Studio.IsValid())Studio->RemoveComponent(StudioFill);
    StudioFill=nullptr;StudioSky=nullptr;ResolvedMaterial=nullptr;Pool.Reset();
    Studio.Reset();
    Super::Deinitialize();
}

void UVoxelBuildIcons::EnsureStudio()
{
    if(Studio.IsValid())return;
    Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false)
        .SetTransactional(false).SetForceMipsResident(false).SetLightBrightness(6.f).SetSkyBrightness(1.f));
    StudioSky=LoadObject<UTextureCube>(nullptr,StudioSkyPath);
    if(StudioSky)Studio->SetSkyCubemap(StudioSky);
    StudioFill=NewObject<UDirectionalLightComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    StudioFill->SetIntensity(3.f);StudioFill->SetLightColor(FLinearColor(.82f,.91f,1.f));StudioFill->SetCastShadows(false);
    Studio->AddComponent(StudioFill,FTransform(FRotator(-15,150,0)));
    Studio->UpdateCaptureContents();
    ResolvedMaterial=LoadObject<UMaterialInterface>(nullptr,ResolvedMaterialPath);
    ColorCapture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);
    ColorCapture->CaptureSource=SCS_FinalToneCurveHDR;
    ColorCapture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    ColorCapture->bCaptureEveryFrame=false;ColorCapture->bCaptureOnMovement=false;
    ColorCapture->ShowFlags.SetAtmosphere(false);ColorCapture->ShowFlags.SetFog(false);ColorCapture->ShowFlags.SetVolumetricFog(false);
    ColorCapture->ShowFlags.SetMotionBlur(false);ColorCapture->ShowFlags.SetBloom(false);
    ColorCapture->ShowFlags.SetAntiAliasing(true);ColorCapture->ShowFlags.SetTemporalAA(false);
    ColorCapture->PostProcessSettings.bOverride_AutoExposureMethod=true;ColorCapture->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    ColorCapture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;
    ColorCapture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    ColorCapture->PostProcessSettings.bOverride_AutoExposureBias=true;ColorCapture->PostProcessSettings.AutoExposureBias=0.f;
    // Auto ortho planes derive the clip range from the visible geometry; framing only needs the ortho
    // width plus a camera distance that comfortably contains the piece.
    ColorCapture->ProjectionType=ECameraProjectionMode::Orthographic;
    ColorCapture->bAutoCalculateOrthoPlanes=true;
    Studio->AddComponent(ColorCapture,FTransform::Identity);
    // Final-color alpha depends on a project-wide postprocess setting, so coverage is captured
    // separately and composited by M_WeaponPreviewResolved (same as the workbench preview).
    CoverageCapture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);
    CoverageCapture->CaptureSource=SCS_SceneColorHDR;
    CoverageCapture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    CoverageCapture->bCaptureEveryFrame=false;CoverageCapture->bCaptureOnMovement=false;
    CoverageCapture->ShowFlags=ColorCapture->ShowFlags;
    CoverageCapture->ShowFlags.SetLighting(false);CoverageCapture->ShowFlags.SetDynamicShadows(false);
    CoverageCapture->bUseRayTracingIfEnabled=false;
    CoverageCapture->ProjectionType=ECameraProjectionMode::Orthographic;
    CoverageCapture->bAutoCalculateOrthoPlanes=true;
    Studio->AddComponent(CoverageCapture,FTransform::Identity);
}

UStaticMeshComponent* UVoxelBuildIcons::TakePoolComponent()
{
    // Components are pooled: one 20 cm block each for voxel constructions, one for a prefab piece.
    for(UStaticMeshComponent* Component:Pool)
        if(Component&&Component->GetStaticMesh()==nullptr)return Component;
    auto* Component=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    Studio->AddComponent(Component,FTransform::Identity);
    Component->SetMobility(EComponentMobility::Movable);
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetCastShadow(false);
    Component->SetCanEverAffectNavigation(false);
    Pool.Add(Component);
    return Component;
}

bool UVoxelBuildIcons::Build(const FVoxelBuildIconRequest& Request)
{
    EnsureStudio();
    if(!Studio.IsValid()||!ColorCapture||!CoverageCapture||!ResolvedMaterial)return false;
    UStaticMesh* Mesh=Request.Mesh.LoadSynchronous();
    if(!Mesh)Mesh=LoadObject<UStaticMesh>(nullptr,DefaultStoneMesh);
    if(!Mesh)return false;
    UMaterialInterface* Surface=Request.Surface.LoadSynchronous();
    if(!Surface)Surface=Mesh->GetMaterial(0);
    for(UStaticMeshComponent* Component:Pool)
        if(Component){Component->SetStaticMesh(nullptr);Component->SetVisibility(false);}
    TArray<UStaticMeshComponent*> Used;
    const FVector CellCentre(10.f,10.f,10.f);
    if(Request.Cells.IsEmpty())
    {
        auto* Component=TakePoolComponent();
        Component->SetStaticMesh(Mesh);
        if(Surface)Component->SetMaterial(0,Surface);
        Component->SetWorldLocationAndRotation(-Request.PivotOffsetCm,FRotator::ZeroRotator);
        Component->SetWorldScale3D(FVector(1.f));
        Component->SetVisibility(true);Component->UpdateComponentToWorld();
        Used.Add(Component);
    }
    else
    {
        for(const FIntVector& Cell:Request.Cells)
        {
            auto* Component=TakePoolComponent();
            Component->SetStaticMesh(Mesh);
            if(Surface)Component->SetMaterial(0,Surface);
            // Same 20 cm lattice as placement: a block sits centred on its own cell.
            Component->SetWorldLocationAndRotation(FVector(Cell)*20.f+CellCentre,FRotator::ZeroRotator);
            Component->SetWorldScale3D(FVector(1.f));
            Component->SetVisibility(true);Component->UpdateComponentToWorld();
            Used.Add(Component);
        }
    }
    if(Used.IsEmpty())return false;
    FBox Bounds(ForceInit);
    for(UStaticMeshComponent* Component:Used)
        if(Component->GetStaticMesh())Bounds+=Component->GetStaticMesh()->GetBoundingBox().TransformBy(Component->GetComponentTransform());
    if(!Bounds.IsValid)return false;
    const FVector Centre=Bounds.GetCenter();
    for(UStaticMeshComponent* Component:Used)
    {Component->AddWorldOffset(-Centre);Component->UpdateComponentToWorld();}
    const FVector Size=Bounds.GetSize();
    const double MaxDim=FMath::Max(Size.X,FMath::Max(Size.Y,Size.Z));
    // 单格（1×1×1 体素块）用一半的取景比例，因此在同样的卡片里只占一半大小。
    const float Fill=IconFillFraction*(Request.Cells.Num()==1?SingleBlockFrameScale:1.f);
    const float OrthoWidth=FMath::Max(24.f,float(MaxDim)/Fill);
    const float Distance=300.f+float(MaxDim)*2.f;
    const FVector Forward=IconView.Vector();
    ColorCapture->ShowOnlyComponents.Reset();CoverageCapture->ShowOnlyComponents.Reset();
    for(UStaticMeshComponent* Component:Used)
    {ColorCapture->ShowOnlyComponent(Component);CoverageCapture->ShowOnlyComponent(Component);}
    for(USceneCaptureComponent2D* Capture:{ColorCapture.Get(),CoverageCapture.Get()})
    {
        Capture->OrthoWidth=OrthoWidth;
        Capture->SetWorldLocationAndRotation(-Forward*Distance,IconView);
    }
    ReleaseEntry(Request.Key);
    auto* Color=NewObject<UTextureRenderTarget2D>(this);
    Color->RenderTargetFormat=RTF_RGBA16f;Color->ClearColor=FLinearColor(0,0,0,1);
    Color->InitAutoFormat(IconSize,IconSize);Color->UpdateResourceImmediate(true);
    auto* Coverage=NewObject<UTextureRenderTarget2D>(this);
    Coverage->RenderTargetFormat=RTF_RGBA8;Coverage->ClearColor=FLinearColor(0,0,0,1);
    Coverage->InitAutoFormat(IconSize,IconSize);Coverage->UpdateResourceImmediate(true);
    ColorCapture->TextureTarget=Color;CoverageCapture->TextureTarget=Coverage;
    ColorCapture->CaptureScene();CoverageCapture->CaptureScene();
    auto* Instance=UMaterialInstanceDynamic::Create(ResolvedMaterial,this);
    if(!Instance)return false;
    Instance->SetTextureParameterValue(TEXT("PreviewTexture"),Color);
    Instance->SetTextureParameterValue(TEXT("PreviewCoverage"),Coverage);
    ColorTargets.Add(Request.Key,Color);CoverageTargets.Add(Request.Key,Coverage);
    Materials.Add(Request.Key,Instance);Uses.Add(Request.Key,++Serial);
    return true;
}

void UVoxelBuildIcons::Tick(float DeltaTime)
{
    if(Queue.IsEmpty())return;
    // One capture pair per frame: the icons are small but a burst would still hitch the drawer.
    const FJob Job=Queue[0];
    Queue.RemoveAt(0);
    const bool bOk=Build(Job.Request);
    Pending.Remove(Job.Request.Key);
    if(!bOk)
    {
        // 失败计数只在失败时累加；到上限后放弃并只记一次，之后 Request 静默跳过这个键。
        int32& Tries=GIconAttempts.FindOrAdd(Job.Request.Key);
        ++Tries;
        if(Tries>=MaxBuildAttempts)
        {
            GIconGaveUp.Add(Job.Request.Key);
            UE_LOG(LogTemp,Warning,TEXT("VoxelBuildIcon: giving up key=%s after %d attempts"),*Job.Request.Key,Tries);
        }
        else
        {
            UE_LOG(LogTemp,Warning,TEXT("VoxelBuildIcon: failed key=%s attempt=%d mesh=%s"),
                *Job.Request.Key,Tries,*Job.Request.Mesh.ToString());
        }
        return;
    }
    // 成功清零，缩略图被 LRU 回收后仍能重建（此前成功也计数，重建 3 轮后永久拒绝）。
    GIconAttempts.Remove(Job.Request.Key);
    // Success is logged too: the drawer silently showing nothing is the symptom, and without a
    // line per built key there is no way to tell "never built" from "built then recycled".
    UE_LOG(LogTemp,Display,TEXT("VoxelBuildIcon: built key=%s cached=%d"),
        *Job.Request.Key,Materials.Num());
    while(Materials.Num()>MaxCachedIcons)
    {
        FString Oldest;uint64 Use=MAX_uint64;
        // 抽屉正在显示的缩略图不回收：全部都在显示时宁可超过上限，也不让卡片变成空图。
        for(const TPair<FString,uint64>& Entry:Uses)
            if(!VisibleKeys.Contains(Entry.Key)&&Entry.Value<Use){Use=Entry.Value;Oldest=Entry.Key;}
        if(Oldest.IsEmpty())break;
        UE_LOG(LogTemp,Display,TEXT("VoxelBuildIcon: recycled key=%s (cache %d, nothing evictable was newer)"),
            *Oldest,Materials.Num());
        ReleaseEntry(Oldest);
    }
}
