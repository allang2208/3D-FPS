#if WITH_EDITOR
#include "../Monsters/FatZombiePusPool.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "AssetCompilingManager.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Materials/Material.h"
#include "RenderingThread.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"

// Explicit diagnostic command: reconstruct the user's paused residue in an
// editor world, read its mesh data, then remove it without ticking gameplay.
static FAutoConsoleCommandWithWorld InspectFatZombiePus(
    TEXT("fps.InspectFatZombiePus"), TEXT("Read the reported pus mesh in the editor world."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
    {
        if (!World || World->IsGameWorld() || World->GetPackage()->GetName() != TEXT("/Game/GameMaps/DayNight_Lighting")) return;
        FAssetCompilingManager::Get().FinishAllCompilation();
        // A non-rendering commandlet does not create the editor's physics scene.
        if (!World->GetPhysicsScene()) World->CreatePhysicsScene();
        for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
            if (It->GetActorLabel() == TEXT("Floor")) It->GetStaticMeshComponent()->RecreatePhysicsState();
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            TInlineComponentArray<UPrimitiveComponent*> Primitives(*It);
            for (auto* Primitive : Primitives)
            {
                const FBox Box = Primitive->Bounds.GetBox();
                if (Box.Min.X <= -354 && Box.Max.X >= -354 && Box.Min.Y <= 638 && Box.Max.Y >= 638 && Box.Min.Z <= 25 && Box.Max.Z >= -.1)
                    UE_LOG(LogTemp,Display,TEXT("FAT_PUS_GROUND_CANDIDATE %s %s min=%s max=%s collision=%d visible=%d"),
                        *It->GetActorLabel(),*Primitive->GetPathName(),*Box.Min.ToString(),*Box.Max.ToString(),int32(Primitive->GetCollisionEnabled()),Primitive->IsVisible());
            }
        }
        for (TObjectIterator<UPrimitiveComponent> It; It; ++It)
            if (It->GetWorld()==World && !It->GetOwner() && It->IsRegistered())
                UE_LOG(LogTemp,Display,TEXT("FAT_PUS_OWNERLESS_SURFACE %s bounds=%s extent=%s collision=%d visible=%d"),
                    *It->GetPathName(),*It->Bounds.Origin.ToString(),*It->Bounds.BoxExtent.ToString(),int32(It->GetCollisionEnabled()),It->IsVisible());
        FHitResult GroundHit;
        World->LineTraceSingleByChannel(GroundHit, FVector(-353.966559,638.393534,42.15), FVector(-353.966559,638.393534,-82.85), ECC_Visibility);
        UE_LOG(LogTemp,Display,TEXT("FAT_PUS_RECONSTRUCTION world=%s hit=%s point=%s pawn_response=%d"),
            *World->GetPathName(),*GetPathNameSafe(GroundHit.GetActor()),*GroundHit.ImpactPoint.ToString(),
            GroundHit.GetComponent()?int32(GroundHit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)):-1);
        FActorSpawnParameters Params;
        Params.ObjectFlags = RF_Transient;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pool = World->SpawnActor<AFatZombiePusPool>(FVector(-353.966559,638.393534,2.150003), FRotator(0,-87.827148,0), Params);
        if (!Pool) return;
        FFatZombiePusSettings Settings;
        Settings.ShapeSeed = 1584119041;
        Pool->InitializeFrom(nullptr, Settings);
        Pool->DispatchBeginPlay();
        const auto* Mesh = Pool->Surface->GetMesh();
        const auto* Colors = Mesh->Attributes()->PrimaryColors();
        float MinAlpha = 1, MaxAlpha = 0, SumAlpha = 0;
        int32 ColorCount = 0, MappedTriangles = 0;
        if (Colors)
        {
            for (int32 Id : Colors->ElementIndicesItr())
            {
                const float A = Colors->GetElement(Id).W;
                MinAlpha = FMath::Min(MinAlpha,A); MaxAlpha = FMath::Max(MaxAlpha,A); SumAlpha += A; ++ColorCount;
            }
            for (int32 Id : Mesh->TriangleIndicesItr()) if (Colors->IsSetTriangle(Id)) ++MappedTriangles;
        }
        float Visibility = -1;
        auto* Material = Pool->Surface->GetMaterial(0);
        if (Material) Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Visibility")),Visibility);
        const auto Bounds = Pool->Surface->Bounds;
        UE_LOG(LogTemp,Display,TEXT("FAT_PUS_MESH_DATA triangles=%d vertices=%d mapped=%d colors=%d alpha=%.3f/%.3f/%.3f material=%s slots=%d visibility=%.3f bounds=%s extent=%s"),
            Mesh->TriangleCount(),Mesh->VertexCount(),MappedTriangles,ColorCount,MinAlpha,MaxAlpha,ColorCount?SumAlpha/ColorCount:0,
            *GetPathNameSafe(Material),Pool->Surface->GetNumMaterials(),Visibility,*Bounds.Origin.ToString(),*Bounds.BoxExtent.ToString());
        if (FParse::Param(FCommandLine::Get(), TEXT("FatPusDrawDiagnosis")))
        {
            AStaticMeshActor* FloorActor = nullptr;
            FTransform OriginalFloorTransform;
            bool bOriginalDisableNanite = false;
            for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
                if (It->GetActorLabel() == TEXT("Floor"))
                {
                    FloorActor = *It;
                    OriginalFloorTransform = It->GetActorTransform();
                    bOriginalDisableNanite = It->GetStaticMeshComponent()->IsForceDisableNanite();
                }
            auto* Camera = World->SpawnActor<ASceneCapture2D>(Params);
            auto* Capture = Camera->GetCaptureComponent2D();
            auto* Target = NewObject<UTextureRenderTarget2D>(Camera);
            Target->RenderTargetFormat = RTF_RGBA8;
            Target->InitAutoFormat(768,768);
            Capture->TextureTarget = Target;
            Capture->CaptureSource = SCS_BaseColor;
            Capture->bCaptureEveryFrame = false;
            Capture->bCaptureOnMovement = false;
            Capture->FOVAngle = 60;
            Camera->SetActorLocation(Bounds.Origin + FVector(-240,-140,390));
            Camera->SetActorRotation((Bounds.Origin-Camera->GetActorLocation()).Rotation());
            auto Save = [&](const TCHAR* Name)
            {
                World->SendAllEndOfFrameUpdates();
                FlushRenderingCommands();
                UE_LOG(LogTemp,Display,TEXT("FAT_PUS_DRAW %s registered=%d render_state=%d proxy=%p"),Name,
                    Pool->Surface->IsRegistered(),Pool->Surface->IsRenderStateCreated(),Pool->Surface->GetSceneProxy());
                Capture->CaptureScene();
                FlushRenderingCommands();
                TArray<FColor> Pixels;
                Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);
                TArray64<uint8> PNG;
                FImageUtils::PNGCompressImageArray(768,768,Pixels,PNG);
                FFileHelper::SaveArrayToFile(PNG,*(FPaths::ProjectSavedDir()/TEXT("FatZombiePusVisibility")/(FString(Name)+TEXT(".png"))));
            };
            if (FParse::Param(FCommandLine::Get(), TEXT("FatPusFixedGround")))
            {
                Save(TEXT("fixed-ground"));
                Camera->Destroy();
                Pool->Destroy();
                return;
            }
            Save(TEXT("reported-material"));
            Pool->Surface->SetMaterial(0,UMaterial::GetDefaultMaterial(MD_Surface));
            Save(TEXT("default-material"));
            Pool->Surface->SetMaterial(0,Material);
            Pool->AddActorWorldOffset(FVector(0,0,20));
            Save(TEXT("raised-material"));
            Pool->AddActorWorldOffset(FVector(0,0,-18));
            Save(TEXT("raised-2cm"));
            Pool->AddActorWorldOffset(FVector(0,0,-2));
            for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
                if (It->GetActorLabel() == TEXT("Floor"))
                {
                    const auto& Positions = It->GetStaticMeshComponent()->GetStaticMesh()->GetRenderData()->LODResources[0].VertexBuffers.PositionVertexBuffer;
                    FBox VertexBounds(ForceInit);
                    for (uint32 V=0;V<Positions.GetNumVertices();++V)
                        VertexBounds += It->GetActorTransform().TransformPosition(FVector(Positions.VertexPosition(V)));
                    UE_LOG(LogTemp,Display,TEXT("FAT_PUS_FLOOR_VERTICES min=%s max=%s"),*VertexBounds.Min.ToString(),*VertexBounds.Max.ToString());
                    UE_LOG(LogTemp,Display,TEXT("FAT_PUS_FLOOR_NANITE valid=%d disallowed=%d"),
                        It->GetStaticMeshComponent()->HasValidNaniteData(),It->GetStaticMeshComponent()->IsDisallowNanite());
                    It->GetStaticMeshComponent()->SetForceDisableNanite(true);
                }
            Save(TEXT("floor-raster"));
            Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
            Capture->ShowOnlyComponent(Pool->Surface);
            for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
                if (It->GetActorLabel() == TEXT("Floor")) Capture->ShowOnlyComponent(It->GetStaticMeshComponent());
            Save(TEXT("only-floor-and-pus"));
            for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
                if (It->GetActorLabel() == TEXT("Floor")) It->SetActorScale3D(FVector(100,100,.4));
            Save(TEXT("floor-scale-100"));
            Capture->CaptureSource = SCS_SceneDepth;
            Target->RenderTargetFormat = RTF_RGBA16f;
            Target->InitAutoFormat(768,768);
            Capture->CaptureScene();
            FlushRenderingCommands();
            TArray<FFloat16Color> DepthPixels;
            Target->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(DepthPixels);
            const float Depth = DepthPixels[384*768+384].R.GetFloat();
            UE_LOG(LogTemp,Display,TEXT("FAT_PUS_FLOOR_DEPTH depth=%.4f camera=%s forward=%s world_z=%.4f"),
                Depth,*Camera->GetActorLocation().ToString(),*Camera->GetActorForwardVector().ToString(),
                Camera->GetActorLocation().Z+Camera->GetActorForwardVector().Z*Depth);
            Camera->SetActorLocation(FVector(Bounds.Origin.X,Bounds.Origin.Y,200));
            Camera->SetActorRotation(FRotator(-90,0,0));
            Capture->CaptureScene();
            FlushRenderingCommands();
            Target->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(DepthPixels);
            UE_LOG(LogTemp,Display,TEXT("FAT_PUS_FLOOR_DEPTH_TOP depth=%.4f world_z=%.4f"),
                DepthPixels[384*768+384].R.GetFloat(),200-DepthPixels[384*768+384].R.GetFloat());
            if (FloorActor)
            {
                FloorActor->SetActorTransform(OriginalFloorTransform);
                FloorActor->GetStaticMeshComponent()->SetForceDisableNanite(bOriginalDisableNanite);
            }
            Camera->Destroy();
        }
        Pool->Destroy();
    }));
#endif
