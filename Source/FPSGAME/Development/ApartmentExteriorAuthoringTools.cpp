#include "ApartmentExteriorAuthoringTools.h"

#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SceneCaptureComponentCube.h"
#include "ContentStreaming.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/TextureRenderTargetCube.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/CoreDelegates.h"
#include "Misc/PackageName.h"
#include "RenderingThread.h"
#include "RHI.h"
#include "RHICommandList.h"
#include "ShaderCompiler.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#endif

#if WITH_EDITOR
bool UApartmentExteriorAuthoringTools::RenderCommandletCamera(USceneCaptureComponent2D* Camera, int32 WarmupFrames)
{
    UWorld* World = IsValid(Camera) ? Camera->GetWorld() : nullptr;
    if (!IsRunningCommandlet() || !IsAllowCommandletRendering() || GUsingNullRHI || !World ||
        World->WorldType != EWorldType::Editor || !World->Scene || !Camera->IsRegistered() ||
        !Camera->TextureTarget || Camera->TextureTarget->SizeX <= 0 || WarmupFrames < 1)
        return false;

    FAssetCompilingManager::Get().FinishAllCompilation();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    const FVector Eye = Camera->GetComponentLocation();
    const float Width = Camera->TextureTarget->SizeX;
    const float HalfFov = .5f * FMath::Clamp(Camera->FOVAngle, 1.f, 179.f);
    const float FovWidth = Width / FMath::Tan(FMath::DegreesToRadians(HalfFov));
    TGuardValue<bool> PersistView(Camera->bAlwaysPersistRenderingState, true);
    auto& Streaming = IStreamingManager::Get();
    for (int32 Frame = 0; Frame < WarmupFrames; ++Frame)
    {
        Streaming.AddViewInformation(Eye, Width, FovWidth, 1.f, true, 0.f, nullptr, World);
        Streaming.UpdateResourceStreaming(0.f, true);
        if (Frame + 1 == WarmupFrames) Streaming.BlockTillAllRequestsFinished();
        // Match the engine's offscreen screenshot frame. Nanite queues GPU page
        // feedback only when the render thread sees a new GFrameCounterRenderThread.
        const uint64 CaptureFrame = ++GFrameCounter;
        ENQUEUE_RENDER_COMMAND(BeginAuthoringCameraFrame)([CaptureFrame](FRHICommandListImmediate&)
        {
            GFrameCounterRenderThread = CaptureFrame;
            ++GFrameNumberRenderThread;
            FCoreDelegates::OnBeginFrameRT.Broadcast();
        });
        Camera->CaptureScene();
        ENQUEUE_RENDER_COMMAND(EndAuthoringCameraFrame)([](FRHICommandListImmediate& RHICmdList)
        {
            FCoreDelegates::OnEndFrameRT.Broadcast();
            RHICmdList.EndFrame();
        });
        FlushRenderingCommands();
    }
    return true;
}
#endif

UTextureCube* UApartmentExteriorAuthoringTools::BakeCityReflection(UWorld* World,
    const TArray<AActor*>& StaticActors, const FString& AssetPath, FVector Origin, int32 Resolution)
{
#if WITH_EDITOR
    if (!World || World->WorldType != EWorldType::Editor || !World->Scene || GUsingNullRHI
        || StaticActors.IsEmpty() || !FPackageName::IsValidLongPackageName(AssetPath)
        || Resolution < 64 || Resolution > 2048 || !FMath::IsPowerOfTwo(Resolution)) return nullptr;

    // Compile the actual imported materials before writing the production texture.
    UE_LOG(LogTemp, Display, TEXT("ApartmentExterior: preparing city reflection resources"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();

    TStrongObjectPtr<UTextureRenderTargetCube> Target(NewObject<UTextureRenderTargetCube>(GetTransientPackage()));
    Target->ClearColor=FLinearColor::Black;
    Target->bHDR=true;
    Target->InitAutoFormat(Resolution);
    Target->UpdateResourceImmediate(true);
    TStrongObjectPtr<USceneCaptureComponentCube> Capture(NewObject<USceneCaptureComponentCube>(GetTransientPackage()));
    Capture->TextureTarget=Target.Get();
    Capture->CaptureSource=SCS_SceneColorHDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false;
    Capture->bCaptureOnMovement=false;
    Capture->bAlwaysPersistRenderingState=true;
    Capture->ShowFlags.SetAtmosphere(false);
    Capture->ShowFlags.SetFog(false);
    Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetMotionBlur(false);
    Capture->ShowFlags.SetBloom(false);
    Capture->ShowFlags.SetEyeAdaptation(false);
    Capture->ShowFlags.SetLighting(true);
    Capture->ShowFlags.SetMaterials(true);
    Capture->SetWorldLocation(Origin);
    Capture->RegisterComponentWithWorld(World);
    for (AActor* Actor:StaticActors)
        if (IsValid(Actor) && Actor->GetWorld()==World) Capture->ShowOnlyActorComponents(Actor);

    IStreamingManager::Get().AddViewInformation(Origin,Resolution,Resolution,1.f,true,0.f,nullptr,World);
    IStreamingManager::Get().UpdateResourceStreaming(0.f,true);
    IStreamingManager::Get().BlockTillAllRequestsFinished();
    World->SendAllEndOfFrameUpdates();
    FlushRenderingCommands();
    // Renderer history/streaming warm-up only; gameplay and actor ticks never run.
    for (int32 Frame=0;Frame<8;++Frame)
    {
        ++GFrameCounter;
        Capture->CaptureScene();
        FlushRenderingCommands();
    }

    UPackage* Package=CreatePackage(*AssetPath);
    const FString Name=FPackageName::GetLongPackageAssetName(AssetPath);
    UTextureCube* Texture=FindObject<UTextureCube>(Package,*Name);
    if (Texture)
    {
        FText Error;
        if (!Target->UpdateTexture(Texture,CTF_Default,nullptr,[](UTexture*){},&Error))
        {
            UE_LOG(LogTemp,Error,TEXT("ApartmentExterior: cube update failed: %s"),*Error.ToString());
            Capture->UnregisterComponent();return nullptr;
        }
    }
    else
    {
        Texture=Target->ConstructTextureCube(Package,Name,RF_Public|RF_Standalone,CTF_Default);
        if (Texture) FAssetRegistryModule::AssetCreated(Texture);
    }
    Capture->UnregisterComponent();
    if (!Texture) return nullptr;
    Texture->CompressionSettings=TC_HDR_Compressed;
    Texture->SRGB=false;
    Texture->MipGenSettings=TMGS_SimpleAverage;
    Texture->LODGroup=TEXTUREGROUP_Skybox;
    Texture->MaxTextureSize=Resolution;
    Texture->PostEditChange();
    Texture->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("ApartmentExterior: production reflection authored %s (%d cube faces)"),*AssetPath,6);
    return Texture; // The caller saves this asset, then binds its derived water material.
#else
    return nullptr;
#endif
}
