#include "XuanChiSurfaceDiagnosisCommandlet.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/RectLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureCube.h"
#include "Engine/Texture.h"
#include "ContentStreaming.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "RenderingThread.h"
#include "PreviewScene.h"
#include "../UI/ColdSteelMeleePreview.h"
#include "../UI/GunsmithPreviewLighting.h"

int32 UXuanChiSurfaceDiagnosisCommandlet::Main(const FString& Params)
{
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/XuanChiZhenYue20261004/BladeV3/TextureRepair/LitDiagnosis");
    FParse::Value(*Params,TEXT("Out="),Out);
    IFileManager::Get().MakeDirectory(*Out,true);
    FPreviewScene Studio(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false)
        .SetTransactional(false).SetForceMipsResident(true).SetLightBrightness(6.f).SetSkyBrightness(1.f));
    auto* World=Studio.GetWorld();
    Studio.SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Meshes/SM_XuanChi_Complete_V3"));
    if(!Mesh)return 1;
    // Render the saved source geometry, not the simplified Nanite export fallback.
    // This in-memory diagnostic change is never saved back to the asset.
#if WITH_EDITOR
    Mesh->NaniteSettings.bEnabled=false;Mesh->Build(false);
#endif
    auto* Part=NewObject<UStaticMeshComponent>();Part->SetStaticMesh(Mesh);Part->SetForceDisableNanite(true);Part->SetCastShadow(false);
    Studio.AddComponent(Part,FTransform::Identity);Part->SetWorldTransform(ColdSteelMeleePreview::Pose(*Mesh,ColdSteelMeleePreview::Rotation(*Mesh)));
    Studio.DirectionalLight->SetWorldRotation(FRotator(-40,-55,0));
    auto* Fill=NewObject<UDirectionalLightComponent>();Fill->SetIntensity(3.f);Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));Fill->SetCastShadows(false);
    Studio.AddComponent(Fill,FTransform(FRotator(-15,150,0)));
    Studio.UpdateCaptureContents();
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->RenderTargetFormat=RTF_RGBA16f;RT->ClearColor=FLinearColor(0,0,0,1);RT->InitAutoFormat(1600,600);RT->UpdateResourceImmediate(true);
    auto* Capture=NewObject<USceneCaptureComponent2D>();Studio.AddComponent(Capture,FTransform::Identity);
    Capture->TextureTarget=RT;Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
    Capture->ProjectionType=ECameraProjectionMode::Orthographic;Capture->OrthoWidth=225;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(112.5f,112.5f/(1600.f/600.f),1.f/2000.f,-.1f);
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->ShowOnlyComponent(Part);
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetBloom(false);Capture->ShowFlags.SetMotionBlur(false);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=0;
    GunsmithPreviewLighting::Create(Studio,*Capture);
    GunsmithPreviewLighting::Update(*Capture,Part->Bounds.GetBox(),false);
    FAssetCompilingManager::Get().FinishAllCompilation();World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
    UTexture::ForceUpdateTextureStreaming();IStreamingManager::Get().StreamAllResources(0.f);
    bool Ok=true;
    for(int32 Mode=0;Mode<4;++Mode)
    {
        Capture->CaptureSource=SCS_FinalToneCurveHDR;
        Capture->PostProcessSettings.AutoExposureBias=0.f;
        const float FluxScales[]={1.f,.01f,.025f,.05f};
        GunsmithPreviewLighting::Update(*Capture,Part->Bounds.GetBox(),false);
        for(USceneComponent* Child:Capture->GetAttachChildren())if(auto* Light=Cast<URectLightComponent>(Child))Light->SetIntensity(Light->Intensity*FluxScales[Mode]);
        for(int32 Frame=0;Frame<8;++Frame){Capture->CaptureScene();FlushRenderingCommands();}
        TArray<FLinearColor> Linear;Ok&=RT->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(Linear,FReadSurfaceDataFlags(RCM_MinMax));
        TArray<FColor> Pixels;Pixels.Reserve(Linear.Num());for(const auto& Color:Linear)Pixels.Add(Color.ToFColorSRGB());
        TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(1600,600,Pixels,PNG);
        const TCHAR* Names[]={TEXT("original.png"),TEXT("softbox_001.png"),TEXT("softbox_0025.png"),TEXT("softbox_005.png")};
        const TCHAR* Name=Names[Mode];
        Ok&=FFileHelper::SaveArrayToFile(PNG,*(Out/Name));
        UE_LOG(LogTemp,Display,TEXT("XUANCHI_SURFACE_DIAGNOSIS %s pixels=%d"),Name,Pixels.Num());
    }
    return Ok?0:1;
}
