#include "ColdSteelHubMapBakeCommandlet.h"

#if WITH_EDITOR
#include "ColdSteelMapReadback.h"
#include "ColdSteelHubMapRegistration.h"
#include "AssetCompilingManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "ContentStreaming.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "Misc/PackageName.h"
#include "RHIGPUReadback.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "UObject/SavePackage.h"

namespace ColdSteelMapReadback
{
    // Only the offline bake waits on the GPU. Read the actual capture, preserving top-to-bottom row order.
    bool ReadPhoto(UTextureRenderTarget2D* Target,TArray<FColor>& Pixels)
    {
        FTextureRenderTargetResource* Resource=Target->GameThread_GetRenderTargetResource();
        const int32 Width=Target->SizeX, Height=Target->SizeY;
        ENQUEUE_RENDER_COMMAND(ReadMapPhoto)([Resource,Width,Height,&Pixels](FRHICommandListImmediate& Cmd)
        {
            FRHITexture* Source=Resource->GetRenderTargetTexture().GetReference();
            if (!Source || Source->GetDesc().Format!=PF_B8G8R8A8) return;
            FRHIGPUTextureReadback Staging(TEXT("ColdSteelHubPhoto"));
            Cmd.Transition(FRHITransitionInfo(Source,ERHIAccess::Unknown,ERHIAccess::CopySrc));
            Staging.EnqueueCopy(Cmd,Source);
            Cmd.Transition(FRHITransitionInfo(Source,ERHIAccess::CopySrc,ERHIAccess::SRVMask));
            Cmd.SubmitAndBlockUntilGPUIdle();
            int32 Pitch=0,Rows=0;
            auto* Buffer=static_cast<const FColor*>(Staging.Lock(Pitch,&Rows));
            if (!Buffer) return;
            if (Pitch>=Width && Rows>=Height)
            {
                Pixels.SetNumUninitialized(Width*Height);
                for (int32 Row=0;Row<Height;++Row)
                    FMemory::Memcpy(Pixels.GetData()+Row*Width,Buffer+Row*Pitch,Width*sizeof(FColor));
            }
            Staging.Unlock();
        });
        FlushRenderingCommands();
        return !Pixels.IsEmpty();
    }
}

namespace ColdSteelHubBake
{
    constexpr int32 Resolution=2048;
    bool SavePhoto(const TArray<FColor>& Pixels,FVector2D Center,double Width)
    {
        const FSoftObjectPath Path(UColdSteelHubMapRegistration::TexturePath);
        const FString PackageName=Path.GetLongPackageName(),Name=Path.GetAssetName();
        UPackage* Package=CreatePackage(*PackageName);
        Package->FullyLoad();
        UTexture2D* Texture=FindObject<UTexture2D>(Package,*Name);
        if (!Texture)
        {
            Texture=NewObject<UTexture2D>(Package,*Name,RF_Public|RF_Standalone);
            FAssetRegistryModule::AssetCreated(Texture);
        }
        Texture->PreEditChange(nullptr);
        Texture->Source.Init(Resolution,Resolution,1,1,TSF_BGRA8,reinterpret_cast<const uint8*>(Pixels.GetData()));
        Texture->SRGB=true;
        Texture->NeverStream=true;
        Texture->LODGroup=TEXTUREGROUP_UI;
        Texture->CompressionSettings=TC_Default;
        Texture->CompressionNoAlpha=true;
        Texture->MipGenSettings=TMGS_SimpleAverage;
        Texture->AddressX=TA_Clamp;
        Texture->AddressY=TA_Clamp;
        auto* Registration=Cast<UColdSteelHubMapRegistration>(Texture->GetAssetUserDataOfClass(UColdSteelHubMapRegistration::StaticClass()));
        if (!Registration)
        {
            Registration=NewObject<UColdSteelHubMapRegistration>(Texture);
            Texture->AddAssetUserData(Registration);
        }
        Registration->CenterCm=Center;
        Registration->WidthCm=Width;
        Texture->PostEditChange();
        FAssetCompilingManager::Get().FinishAllCompilation();
        const FString File=FPackageName::LongPackageNameToFilename(PackageName,FPackageName::GetAssetPackageExtension());
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);
        FSavePackageArgs Save;
        Save.TopLevelFlags=RF_Public|RF_Standalone;
        return UPackage::SavePackage(Package,Texture,*File,Save);
    }
}
#endif

int32 UColdSteelHubMapBakeCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    using namespace ColdSteelHubBake;
    if (!FApp::CanEverRender() || GUsingNullRHI) return 1;
    const FString Level=TEXT("/Game/GameMaps/DayNight_Lighting");
    UWorld* World=UEditorLoadingAndSavingUtils::LoadMap(FPackageName::LongPackageNameToFilename(Level,FPackageName::GetMapPackageExtension()));
    if (!World || !World->Scene || World->GetPackage()->GetName()!=Level) return 2;
    FAssetCompilingManager::Get().FinishAllCompilation();
    FBox Platform(ForceInit);
    for (TActorIterator<AActor> It(World);It;++It)
    {
        TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
        for (const auto* Mesh:Meshes)
            if (Mesh->GetStaticMesh() && Mesh->GetStaticMesh()->GetFName()==TEXT("SM_GodSpaceStructure"))
                Platform+=Mesh->GetBounds().GetBox();
    }
    if (!Platform.IsValid) { UE_LOG(LogTemp,Error,TEXT("Hub map: saved platform geometry was not found")); return 3; }
    const FVector Center=Platform.GetCenter();
    const double Width=FMath::CeilToDouble(FMath::Max(Platform.GetSize().X,Platform.GetSize().Y)*1.08);
    const FVector Eye(Center.X,Center.Y,Platform.Max.Z+Width);
    TStrongObjectPtr<UTextureRenderTarget2D> Target(NewObject<UTextureRenderTarget2D>());
    Target->ClearColor=FLinearColor::Black;
    Target->InitCustomFormat(Resolution,Resolution,PF_B8G8R8A8,false);
    Target->UpdateResourceImmediate(true);
    TStrongObjectPtr<USceneCaptureComponent2D> Camera(NewObject<USceneCaptureComponent2D>());
    Camera->TextureTarget=Target.Get();
    Camera->ProjectionType=ECameraProjectionMode::Orthographic;
    Camera->OrthoWidth=Width;
    Camera->bAutoCalculateOrthoPlanes=false;
    Camera->bUpdateOrthoPlanes=false;
    Camera->bUseCustomProjectionMatrix=true;
    Camera->CustomProjectionMatrix=FReversedZOrthoMatrix(Width*.5,Width*.5,1./(Eye.Z-Platform.Min.Z+1000.),0.);
    Camera->bCaptureEveryFrame=false;
    Camera->bCaptureOnMovement=false;
    Camera->bAlwaysPersistRenderingState=true;
    Camera->CaptureSource=SCS_FinalColorLDR;
    Camera->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives;
    Camera->ShowFlags.SetFog(false);
    Camera->ShowFlags.SetAtmosphere(false);
    Camera->ShowFlags.SetCloud(false);
    Camera->ShowFlags.SetBloom(false);
    Camera->ShowFlags.SetMotionBlur(false);
    Camera->ShowFlags.SetEyeAdaptation(false);
    Camera->ShowFlags.SetSelectionOutline(false);
    auto& PP=Camera->PostProcessSettings;
    PP.bOverride_AutoExposureMinBrightness=PP.bOverride_AutoExposureMaxBrightness=true;
    PP.AutoExposureMinBrightness=PP.AutoExposureMaxBrightness=1.f;
    PP.bOverride_ColorSaturation=true;
    PP.ColorSaturation=FVector4(.55,.55,.55,1.);
    Camera->SetWorldLocationAndRotation(Eye,FRotator(-90.,0.,0.));
    Camera->RegisterComponentWithWorld(World);
    // Establish repeatable daylight in the in-memory capture world without changing the saved lighting rig.
    for (TActorIterator<AActor> It(World);It;++It)
    {
        TInlineComponentArray<UDirectionalLightComponent*> Lights(*It);
        for (auto* Light:Lights) Light->SetVisibility(false);
        TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
        for (auto* Mesh:Meshes)
            if (Mesh->GetBounds().GetBox().Intersect(Platform.ExpandBy(1200.))) Mesh->PrestreamTextures(30.f,false);
    }
    TStrongObjectPtr<UDirectionalLightComponent> Sun(NewObject<UDirectionalLightComponent>());
    Sun->SetMobility(EComponentMobility::Movable);
    Sun->SetWorldRotation(FRotator(-57.,36.,0.));
    Sun->SetIntensity(4.f);
    Sun->RegisterComponentWithWorld(World);
    IStreamingManager::Get().AddViewInformation(Center+FVector(0,0,700),Resolution,Resolution,1.f,true,0.f,nullptr,World);
    IStreamingManager::Get().UpdateResourceStreaming(0.f,true);
    IStreamingManager::Get().BlockTillAllRequestsFinished();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    World->SendAllEndOfFrameUpdates();
    FlushRenderingCommands();
    for (int32 Frame=0;Frame<12;++Frame)
    {
        ++GFrameCounter;
        ENQUEUE_RENDER_COMMAND(HubPhotoFrame)([](FRHICommandListImmediate&){++GFrameNumberRenderThread;});
        Camera->CaptureScene();
        ENQUEUE_RENDER_COMMAND(EndHubPhotoFrame)([](FRHICommandListImmediate& Cmd){Cmd.EndFrame();});
        FlushRenderingCommands();
    }
    TArray<FColor> Pixels;
    const bool bRead=ColdSteelMapReadback::ReadPhoto(Target.Get(),Pixels);
    Camera->UnregisterComponent();
    Sun->UnregisterComponent();
    if (!bRead) { UE_LOG(LogTemp,Error,TEXT("Hub map: GPU readback failed")); return 4; }
    uint8 MinLight=255,MaxLight=0;
    for (FColor& Color:Pixels)
    {
        Color.A=255;
        const uint8 Light=FMath::Max3(Color.R,Color.G,Color.B);
        MinLight=FMath::Min(MinLight,Light);
        MaxLight=FMath::Max(MaxLight,Light);
    }
    if (MaxLight-MinLight<8) { UE_LOG(LogTemp,Error,TEXT("Hub map: empty scene capture")); return 5; }
    const FVector2D AbsoluteCenter=FVector2D(Center)+FVector2D(World->OriginLocation.X,World->OriginLocation.Y);
    if (!SavePhoto(Pixels,AbsoluteCenter,Width)) return 6;
    UE_LOG(LogTemp,Display,TEXT("Hub map: saved %s, %dx%d, center XY %s, width %.2f cm (+X north)"),
        UColdSteelHubMapRegistration::TexturePath,Resolution,Resolution,*AbsoluteCenter.ToString(),Width);
    return 0;
#else
    return 1;
#endif
}
