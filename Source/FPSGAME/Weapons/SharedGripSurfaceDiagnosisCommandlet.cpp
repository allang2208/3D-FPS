#include "SharedGripSurfaceDiagnosisCommandlet.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "ContentStreaming.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "PreviewScene.h"
#include "RenderingThread.h"
#include "../UI/GunsmithPreviewLighting.h"

int32 USharedGripSurfaceDiagnosisCommandlet::Main(const FString& Params)
{
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/SharedSwordGrips20260927/MaterialRepair20261031/NativeBefore");
    FParse::Value(*Params,TEXT("Out="),Out);
    IFileManager::Get().MakeDirectory(*Out,true);
    FPreviewScene Studio(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false)
        .SetTransactional(false).SetForceMipsResident(true).SetLightBrightness(6.f).SetSkyBrightness(1.5f));
    UWorld* World=Studio.GetWorld();
    Studio.SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
    TArray<UStaticMeshComponent*> Parts;
    FBox Bounds(ForceInit);
    for(const TCHAR* Id:{TEXT("iron_spine_power_grip"),TEXT("lockweave_guard_grip")})
    {
        const FString Path=FString(TEXT("/Game/Weapons/SharedSwordGrips20260927/Rune/SM_RuneGrip_"))+Id;
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);
        if(!Mesh)return 1;
#if WITH_EDITOR
        Mesh->NaniteSettings.bEnabled=false;
        Mesh->Build(false);
#endif
        auto* Part=NewObject<UStaticMeshComponent>();
        Part->SetStaticMesh(Mesh);Part->SetForceDisableNanite(true);Part->SetCastShadow(false);
        Studio.AddComponent(Part,FTransform(FVector(150,Parts.IsEmpty()?-4.:4.,-Mesh->GetBounds().Origin.Z)));
        Bounds+=Part->Bounds.GetBox();Parts.Add(Part);
        for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
            UE_LOG(LogTemp,Display,TEXT("GRIP_DIAG_MATERIAL %s %d %s"),Id,Slot,*GetPathNameSafe(Part->GetMaterial(Slot)));
    }
    Studio.DirectionalLight->SetWorldRotation(FRotator(-40,-55,0));
    auto* Fill=NewObject<UDirectionalLightComponent>();Fill->SetIntensity(3.f);Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));Fill->SetCastShadows(false);
    Studio.AddComponent(Fill,FTransform(FRotator(-15,150,0)));
    Studio.UpdateCaptureContents();
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->RenderTargetFormat=RTF_RGBA16f;
    RT->ClearColor=FLinearColor(0,0,0,1);RT->InitAutoFormat(768,768);RT->UpdateResourceImmediate(true);
    auto* Capture=NewObject<USceneCaptureComponent2D>();Studio.AddComponent(Capture,FTransform::Identity);
    Capture->TextureTarget=RT;Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
    Capture->ProjectionType=ECameraProjectionMode::Orthographic;Capture->OrthoWidth=24.f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(12.f,12.f,1.f/2000.f,-.1f);
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    for(auto* Part:Parts)Capture->ShowOnlyComponent(Part);
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetBloom(false);Capture->ShowFlags.SetMotionBlur(false);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=.35f;
    GunsmithPreviewLighting::Create(Studio,*Capture);
    GunsmithPreviewLighting::Update(*Capture,Bounds,false);
    FAssetCompilingManager::Get().FinishAllCompilation();World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
    UTexture::ForceUpdateTextureStreaming();IStreamingManager::Get().StreamAllResources(0.f);
    bool Ok=true;
    const TCHAR* Names[]={TEXT("workbench.png"),TEXT("no_softboxes.png"),TEXT("softboxes_0025.png"),TEXT("base_color.png")};
    const float Flux[]={1.f,0.f,.025f,1.f};
    for(int32 Mode=0;Mode<4;++Mode)
    {
        Capture->CaptureSource=Mode==3?SCS_BaseColor:SCS_FinalToneCurveHDR;
        GunsmithPreviewLighting::Update(*Capture,Bounds,false,Flux[Mode]);
        for(int32 Frame=0;Frame<8;++Frame){Capture->CaptureScene();FlushRenderingCommands();}
        TArray<FLinearColor> Linear;
        Ok&=RT->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(Linear,FReadSurfaceDataFlags(RCM_MinMax));
        TArray<FColor> Pixels;Pixels.Reserve(Linear.Num());
        for(const auto& Color:Linear){FColor Pixel=Color.ToFColorSRGB();Pixel.A=255;Pixels.Add(Pixel);}
        TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(768,768,Pixels,PNG);
        Ok&=FFileHelper::SaveArrayToFile(PNG,*(Out/Names[Mode]));
        UE_LOG(LogTemp,Display,TEXT("GRIP_SURFACE_DIAGNOSIS %s pixels=%d"),Names[Mode],Pixels.Num());
    }
    return Ok?0:1;
}
