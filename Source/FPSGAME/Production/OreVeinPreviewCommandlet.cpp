#include "OreVeinPreviewCommandlet.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineUtils.h"
#include "ImageUtils.h"
#include "Materials/MaterialInstance.h"
#include "Misc/FileHelper.h"
#include "Modules/ModuleManager.h"
#include "PreviewScene.h"
#include "RHIGPUReadback.h"
#include "RenderingThread.h"

struct FOrePreviewScene
{
    TUniquePtr<FPreviewScene> Studio;
    TObjectPtr<UTextureRenderTarget2D> Target = nullptr;
    TObjectPtr<USceneCaptureComponent2D> Capture = nullptr;
    TArray<TObjectPtr<UStaticMeshComponent>> Rocks;

    bool Build()
    {
        Studio = MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues()
            .SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false)
            .SetForceMipsResident(true).SetLightBrightness(10.f).SetSkyBrightness(3.f));
        Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr, TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment")));
        Studio->DirectionalLight->SetWorldRotation(FRotator(-35, -35, 0));
        Studio->UpdateCaptureContents();

        static const TCHAR* Meshes[] = {
            TEXT("/Game/UnrealNormandy/StaticMeshes/SM_LS_Rock_00A.SM_LS_Rock_00A"),
            TEXT("/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Iron.SM_LS_Rock_00A_Iron"),
            TEXT("/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Copper.SM_LS_Rock_00A_Copper"),
            TEXT("/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Silver.SM_LS_Rock_00A_Silver"),
            TEXT("/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Gold.SM_LS_Rock_00A_Gold"),
        };
        constexpr float RockScale = 0.45f;
        constexpr float Spacing = 650.f;
        // Ownerless components exactly like ColdSteelMaterialIcon::PrepareMaterial:
        // add to the studio FIRST (its SetRelativeTransform wipes any earlier pose),
        // then SetWorldTransform afterwards.
        for (int32 Index = 0; Index < 5; ++Index)
        {
            auto* Mesh = LoadObject<UStaticMesh>(nullptr, Meshes[Index]);
            if (!Mesh) { UE_LOG(LogTemp, Error, TEXT("OREPREV mesh missing %s"), Meshes[Index]); return false; }
            auto* Comp = NewObject<UStaticMeshComponent>(GetTransientPackage(), NAME_None, RF_Transient);
            Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Comp->SetForcedLodModel(1);
            Studio->AddComponent(Comp, FTransform::Identity);
            Comp->SetStaticMesh(Mesh);
            const FQuat Orient = FQuat(FVector::YAxisVector, FMath::DegreesToRadians(22.f))
                * FQuat(FVector::ZAxisVector, FMath::DegreesToRadians(30.f));
            const FBoxSphereBounds Local = Mesh->GetBounds();
            const FVector Origin((Index - 2) * Spacing, 0, 0);
            Comp->SetWorldTransform(FTransform(Orient, Origin, FVector(RockScale)));
            Comp->AddToRoot();
            Rocks.Add(Comp);
        }

        Target = NewObject<UTextureRenderTarget2D>(GetTransientPackage());
        Target->RenderTargetFormat = RTF_RGBA16f;
        Target->ClearColor = FLinearColor(0, 0, 0, 1);
        Target->AddToRoot();
        Target->InitAutoFormat(1536, 512);
        Target->UpdateResourceImmediate(true);
        FlushRenderingCommands(); FlushRenderingCommands();
        UE_LOG(LogTemp, Display, TEXT("OREPREV build: target resource=%s"),
            Target->GameThread_GetRenderTargetResource() ? TEXT("yes") : TEXT("null"));

        Capture = NewObject<USceneCaptureComponent2D>(GetTransientPackage(), NAME_None, RF_Transient);
        Capture->AddToRoot();
        Capture->TextureTarget = Target;
        Capture->CaptureSource = SCS_FinalColorLDR;
        Capture->ProjectionType = ECameraProjectionMode::Orthographic;
                // Whole-scene mode: the preview world contains only the rocks, and the
        // show-only list only ever surfaced one of the five components.
        Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives;
        Capture->bCaptureEveryFrame = false;
        Capture->bCaptureOnMovement = false;
        Capture->ShowFlags.SetAtmosphere(false);
        Capture->ShowFlags.SetFog(false);
        Capture->ShowFlags.SetMotionBlur(false);
        Capture->ShowFlags.SetBloom(false);
        Capture->ShowFlags.SetDynamicShadows(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod = true;
        Capture->PostProcessSettings.AutoExposureMethod = AEM_Manual;
        // Camera 200 units off the nearest face, looking straight down +X, and the
        // same reversed-Z ortho the icon pipeline uses (near plane lands at 200).
        Capture->OrthoWidth = 2200.f;
        Capture->SetWorldLocationAndRotation(FVector(-2 * Spacing - 310.f * RockScale - 200.f, 0, 0), FRotator::ZeroRotator);
        Capture->bAutoCalculateOrthoPlanes = false;
        Capture->bUseCustomProjectionMatrix = true;
        constexpr float Aspect = 1536.f / 512.f;
        Capture->CustomProjectionMatrix = FReversedZOrthoMatrix(
            Capture->OrthoWidth * .5f, Capture->OrthoWidth * .5f / Aspect, 1.f / 2000.f, -.1f);
        Studio->AddComponent(Capture, FTransform::Identity);
        Capture->SetWorldLocationAndRotation(FVector(-2 * Spacing - 310.f * RockScale - 200.f, 0, 0), FRotator::ZeroRotator);
        Studio->GetWorld()->SendAllEndOfFrameUpdates();

        return true;
    }

    void PumpFrames(int32 Frames)
    {
        for (int32 Frame = 0; Frame < Frames; ++Frame)
        {
            ++GFrameCounter;
            FAssetCompilingManager::Get().ProcessAsyncTasks();
            ENQUEUE_RENDER_COMMAND(BeginFrame)([](FRHICommandListImmediate&) { ++GFrameNumberRenderThread; });
            ENQUEUE_RENDER_COMMAND(EndFrame)([](FRHICommandListImmediate& Cmd) { Cmd.EndFrame(); });
            FlushRenderingCommands();
            FPlatformProcess::Sleep(.005f);
        }
    }

    bool SavePng(const TCHAR* Name)
    {
        // Same route as the project's icon pipeline: enqueue an RHI staging copy on
        // the render thread and lock it back. GameThread ReadPixels fails under a
        // commandlet here (proven by two failed attempts).
        FlushRenderingCommands();
        FRenderTarget* Resource = Target->GameThread_GetRenderTargetResource();
        FRHITexture* Source = Resource ? Resource->GetRenderTargetTexture().GetReference() : nullptr;
        UE_LOG(LogTemp, Display, TEXT("OREPREV diag resource=%s src=%s size=%dx%d fmt=%d"),
            Resource ? TEXT("yes") : TEXT("null"), Source ? TEXT("yes") : TEXT("null"),
            Target->SizeX, Target->SizeY, int(Target->RenderTargetFormat));
        if (!Source)
        {
            // The capture itself allocates the target texture; ask for one more
            // explicit capture and drain the queue before giving up.
            if (Capture) Capture->CaptureScene();
            FlushRenderingCommands();
            FPlatformProcess::Sleep(.1f);
            FlushRenderingCommands();
            Source = Resource ? Resource->GetRenderTargetTexture().GetReference() : nullptr;
        }
        if (!Source)
        {
            UE_LOG(LogTemp, Error, TEXT("OREPREV no render target texture %s"), Name);
            return false;
        }
        // Lock/poll must run ON the render thread (RHICommandList assert): poll by
        // repeatedly enqueueing a render command until the staging copy is ready.
        struct FOreReadbackPacket
        {
            TUniquePtr<FRHIGPUTextureReadback> Staging;
            TAtomic<bool> Done{false};
            bool Ok = false;
            TArray<FColor> Pixels;
        };
        auto Packet = MakeShared<FOreReadbackPacket, ESPMode::ThreadSafe>();
        Packet->Staging = MakeUnique<FRHIGPUTextureReadback>(TEXT("OreVeinPreview"));
        FRHIGPUTextureReadback* Raw = Packet->Staging.Get();
        ENQUEUE_RENDER_COMMAND(OrePrevCopy)([Packet, Source](FRHICommandListImmediate& Cmd)
        {
            Cmd.Transition(FRHITransitionInfo(Source, ERHIAccess::Unknown, ERHIAccess::CopySrc));
            Packet->Staging->EnqueueCopy(Cmd, Source);
            Cmd.Transition(FRHITransitionInfo(Source, ERHIAccess::CopySrc, ERHIAccess::SRVMask));
        });
        const int32 SizeX = Target->SizeX, SizeY = Target->SizeY;
        const double Deadline = FPlatformTime::Seconds() + 15.0;
        while (FPlatformTime::Seconds() < Deadline)
        {
            ENQUEUE_RENDER_COMMAND(OrePrevPoll)([Packet, Raw, SizeX, SizeY](FRHICommandListImmediate& Cmd)
            {
                if (Packet->Done.Load() || !Raw->IsReady()) return;
                int32 RowPitch = 0, BufferHeight = 0;
                const auto* Half = static_cast<const FFloat16Color*>(Raw->Lock(RowPitch, &BufferHeight));
                if (!Half || RowPitch < SizeX || BufferHeight < SizeY)
                {
                    if (Half) Raw->Unlock();
                    Packet->Ok = false;
                }
                else
                {
                    Packet->Pixels.SetNumUninitialized(SizeX * SizeY);
                    const int32 Pitch = RowPitch;   // engine contract: OutRowPitchInPixels (element units)
                    for (int32 Y = 0; Y < SizeY; ++Y)
                        for (int32 X = 0; X < SizeX; ++X)
                            Packet->Pixels[Y * SizeX + X] = Half[Y * Pitch + X].GetFloats().ToFColorSRGB();
                    Raw->Unlock();
                    Packet->Ok = true;
                }
                Packet->Staging.Reset();
                Packet->Done.Store(true);
            });
            FlushRenderingCommands();
            if (Packet->Done.Load()) break;
            FPlatformProcess::Sleep(.02f);
        }
        if (!Packet->Done.Load() || !Packet->Ok)
        {
            UE_LOG(LogTemp, Error, TEXT("OREPREV staging readback failed %s"), Name);
            return false;
        }
        const TArray<FColor>& Pixels = Packet->Pixels;
        {
            int64 Sum = 0; int32 MaxV = 0, NonZero = 0;
            for (int32 i = 0; i < Pixels.Num(); i += 7)
            {
                const FColor& C = Pixels[i];
                const int32 V = int(C.R) + int(C.G) + int(C.B);
                Sum += V;
                const int32 ChannelMax = FMath::Max3(int32(C.R), int32(C.G), int32(C.B));
                MaxV = FMath::Max(MaxV, ChannelMax);
                if (V > 0) ++NonZero;
            }
            const int64 Samples = FMath::Max<int64>(1, Pixels.Num() / 7);
            UE_LOG(LogTemp, Display, TEXT("OREPREV stats %s nonzero=%d/%d max=%d avg=%.2f"),
                Name, NonZero, Samples, MaxV, double(Sum) / Samples / 3.0);
        }
        TArray64<uint8> Png;
        FImageUtils::PNGCompressImageArray(Target->SizeX, Target->SizeY,
            TArrayView64<const FColor>(Pixels.GetData(), int64(Pixels.Num())), Png);
        const FString Path = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("OreVeinRocks"), Name);
        return FFileHelper::SaveArrayToFile(Png, *Path);
    }
};

int32 UOreVeinPreviewCommandlet::Main(const FString& Params)
{
    FOrePreviewScene Scene;
    if (!Scene.Build()) return 1;
    FAssetCompilingManager::Get().FinishAllCompilation();
    Scene.PumpFrames(240);            // let fresh vein shaders compile through the workers
    // One rock per frame: multiple components in the show-only/scene path only ever
    // surfaced a single rock, so capture each individually, centered.
    static const TCHAR* Names[] = { TEXT("plain.png"), TEXT("iron.png"), TEXT("copper.png"), TEXT("silver.png"), TEXT("gold.png") };
    bool AllOk = true;
    for (int32 Index = 0; Index < Scene.Rocks.Num(); ++Index)
    {
        const float X = (Index - 2) * 650.f;
        Scene.Capture->OrthoWidth = 900.f;
        Scene.Capture->CustomProjectionMatrix = FReversedZOrthoMatrix(
            450.f, 450.f / (1536.f / 512.f), 1.f / 2000.f, -.1f);
        Scene.Capture->SetWorldLocationAndRotation(FVector(X - 340.f, 0, 0), FRotator::ZeroRotator);
        Scene.PumpFrames(4);
        Scene.Capture->CaptureScene();
        Scene.PumpFrames(4);
        Scene.Capture->CaptureScene();
        Scene.PumpFrames(4);
        AllOk &= Scene.SavePng(Names[Index]);
    }
    UE_LOG(LogTemp, Display, TEXT("OREPREV %s"), AllOk ? TEXT("PASS") : TEXT("FAIL"));
    return AllOk ? 0 : 2;
}
