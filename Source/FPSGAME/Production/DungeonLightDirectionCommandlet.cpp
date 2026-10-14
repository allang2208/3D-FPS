#include "DungeonLightDirectionCommandlet.h"

#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SpotLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/RectLight.h"
#include "Engine/SpotLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Materials/MaterialInterface.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "PreviewScene.h"
#include "RHIGPUReadback.h"
#include "RenderingThread.h"

namespace DungeonDirectionPreview
{
using JObject = TSharedPtr<FJsonObject>;
FVector JsonVector(const JObject& Object, const TCHAR* Key)
{
    const auto& Values = Object->GetArrayField(Key);
    return FVector(Values[0]->AsNumber(), Values[1]->AsNumber(), Values[2]->AsNumber());
}
double Number(const JObject& Object, const TCHAR* Key, double Default)
{
    Object->TryGetNumberField(Key, Default);
    return Default;
}
FQuat Rotation(const JObject& Light)
{
    return FRotator(Number(Light, TEXT("pitch"), -90), Number(Light, TEXT("yaw"), 0), Number(Light, TEXT("roll"), 0)).Quaternion();
}
JObject ReadCatalog()
{
    FString Text;
    JObject Catalog;
    FFileHelper::LoadFileToString(Text, *FPaths::Combine(FPaths::ProjectDir(), TEXT("SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json")));
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Catalog);
    return Catalog;
}
void WriteVector(const JObject& Object, const TCHAR* Key, const FVector& Vector)
{
    Object->SetArrayField(Key, {MakeShared<FJsonValueNumber>(Vector.X), MakeShared<FJsonValueNumber>(Vector.Y), MakeShared<FJsonValueNumber>(Vector.Z)});
}
bool ProbeInitializedWorld(UWorld* World, const JObject& Catalog)
{
    if (!World->IsGameWorld() || !World->bIsWorldInitialized || !World->AreActorsInitialized()) return false;
    TArray<TSharedPtr<FJsonValue>> Rows;
    int32 OldWrong = 0, FixedWrong = 0;
    for (const auto& ModuleValue : Catalog->GetArrayField(TEXT("modules")))
    {
        const auto Module = ModuleValue->AsObject();
        int32 Index = 0;
        for (const auto& Value : Module->GetArrayField(TEXT("lights")))
        {
            const auto Light = Value->AsObject();
            const FString Kind = Light->GetStringField(TEXT("type"));
            for (int32 Yaw : {0, 90, 180, 270})
            {
                const FQuat Desired = FRotator(0, Yaw, 0).Quaternion() * Rotation(Light);
                FActorSpawnParameters Params;
                Params.ObjectFlags |= RF_Transient;
                Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                ALight* Actor = World->SpawnActor<ALight>(Kind == TEXT("spot") ? ASpotLight::StaticClass() : Kind == TEXT("rect") ? ARectLight::StaticClass() : APointLight::StaticClass(), FVector(0, 0, -100000), Desired.Rotator(), Params);
                auto* Component = CastChecked<ULocalLightComponent>(Actor->GetLightComponent());
                Component->SetIntensity(0.f);
                Component->SetVisibility(false);
                if (!Actor->IsActorInitialized()) return false;
                const FVector Before = Component->GetForwardVector();
                // Reproduce the previous production fix's rejected order.
                const bool OldMoved = Actor->SetActorLocationAndRotation(Actor->GetActorLocation(), Desired, false, nullptr, ETeleportType::TeleportPhysics);
                const FVector Rejected = Component->GetForwardVector();
                Component->SetMobility(EComponentMobility::Movable);
                const bool FixedMoved = Actor->SetActorLocationAndRotation(Actor->GetActorLocation(), Desired, false, nullptr, ETeleportType::TeleportPhysics);
                const FVector Fixed = Component->GetForwardVector(), Expected = Desired.GetAxisX();
                const bool WasWrong = !Rejected.Equals(Expected, .001);
                OldWrong += WasWrong ? 1 : 0;
                FixedWrong += (!FixedMoved || !Fixed.Equals(Expected, .001)) ? 1 : 0;
                auto Row = MakeShared<FJsonObject>();
                Row->SetStringField(TEXT("module"), Module->GetStringField(TEXT("id")));
                Row->SetNumberField(TEXT("index"), Index); Row->SetNumberField(TEXT("room_yaw"), Yaw);
                Row->SetStringField(TEXT("type"), Kind);
                Row->SetBoolField(TEXT("actor_initialized"), Actor->IsActorInitialized());
                Row->SetBoolField(TEXT("old_set_transform_accepted"), OldMoved);
                Row->SetBoolField(TEXT("fixed_set_transform_accepted"), FixedMoved);
                WriteVector(Row, TEXT("spawned"), Before); WriteVector(Row, TEXT("previous_fix_actual"), Rejected);
                WriteVector(Row, TEXT("corrected_actual"), Fixed); WriteVector(Row, TEXT("expected"), Expected);
                Rows.Add(MakeShared<FJsonValueObject>(Row));
                Actor->Destroy();
            }
            ++Index;
        }
    }
    auto Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("initialized_game_world"), true);
    Result->SetNumberField(TEXT("cases"), Rows.Num()); Result->SetNumberField(TEXT("previous_fix_wrong_cases"), OldWrong);
    Result->SetNumberField(TEXT("corrected_wrong_cases"), FixedWrong); Result->SetArrayField(TEXT("rows"), Rows);
    FString Text; FJsonSerializer::Serialize(Result, TJsonWriterFactory<>::Create(&Text));
    const FString Path = FPaths::Combine(FPaths::ProjectDir(), TEXT("SourceAssets/DungeonHallCeilingLight20261009/Receipts/initialized-game-directions.json"));
    const bool Saved = FFileHelper::SaveStringToFile(Text, *Path);
    UE_LOG(LogTemp, Display, TEXT("INITIALIZED_LIGHT_DIRECTIONS cases=%d old_wrong=%d corrected_wrong=%d"), Rows.Num(), OldWrong, FixedWrong);
    return Saved && Rows.Num() > 0 && OldWrong > 0 && FixedWrong == 0;
}

bool BuildReception(UWorld* World, const JObject& Catalog, TArray<TPair<ALight*, FQuat>>& Lights)
{
    JObject Hall;
    for (const auto& Value : Catalog->GetArrayField(TEXT("modules")))
        if (Value->AsObject()->GetStringField(TEXT("id")) == TEXT("FacilityReceptionHall")) Hall = Value->AsObject();
    if (!Hall) return false;
    FActorSpawnParameters Params;
    Params.ObjectFlags |= RF_Transient;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    for (const auto& Value : Hall->GetArrayField(TEXT("parts")))
    {
        const auto Part = Value->AsObject();
        const FString Path = Part->GetStringField(TEXT("mesh"));
        auto* Shape = LoadObject<UStaticMesh>(nullptr, *Path);
        if (!Shape) { UE_LOG(LogTemp, Error, TEXT("HALL_PREVIEW missing mesh %s"), *Path); return false; }
        auto* Actor = World->SpawnActor<AStaticMeshActor>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
        auto* Component = Actor->GetStaticMeshComponent();
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetStaticMesh(Shape);
        bool Shadow = true; Part->TryGetBoolField(TEXT("cast_shadow"), Shadow);
        Component->SetCastShadow(Shadow);
        Actor->SetActorTransform(FTransform(FRotator(0, Number(Part, TEXT("yaw"), 0), 0), JsonVector(Part, TEXT("position")), JsonVector(Part, TEXT("scale"))));
        const TArray<TSharedPtr<FJsonValue>>* Materials = nullptr;
        if (Part->TryGetArrayField(TEXT("materials"), Materials))
            for (int32 Slot = 0; Slot < Materials->Num(); ++Slot)
                Component->SetMaterial(Slot, LoadObject<UMaterialInterface>(nullptr, *(*Materials)[Slot]->AsString()));
    }
    for (const auto& Value : Hall->GetArrayField(TEXT("lights")))
    {
        const auto L = Value->AsObject();
        const bool Spot = L->GetStringField(TEXT("type")) == TEXT("spot");
        const FQuat Desired = Rotation(L);
        auto* Actor = World->SpawnActor<ALight>(Spot ? ASpotLight::StaticClass() : ARectLight::StaticClass(), JsonVector(L, TEXT("position")), Desired.Rotator(), Params);
        auto* C = CastChecked<ULocalLightComponent>(Actor->GetLightComponent());
        // Recreate the previous live game's ordering for the BEFORE image.
        const bool Accepted = Actor->SetActorLocationAndRotation(Actor->GetActorLocation(), Desired, false, nullptr, ETeleportType::TeleportPhysics);
        UE_LOG(LogTemp, Display, TEXT("HALL_PREVIEW before id=%s initialized=%d move_accepted=%d actual=%s"), *L->GetStringField(TEXT("id")), Actor->IsActorInitialized(), Accepted, *C->GetForwardVector().ToString());
        C->SetMobility(EComponentMobility::Movable);
        C->SetIntensityUnits(ELightUnits::Lumens);
        float Intensity = L->GetNumberField(TEXT("intensity"));
        if (auto* S = Cast<USpotLightComponent>(C))
        {
            const float Outer = Number(L, TEXT("outer_cone_degrees"), 65);
            S->SetOuterConeAngle(Outer); S->SetInnerConeAngle(Outer - 15);
            S->SetSourceRadius(Number(L, TEXT("source_radius"), 1)); S->SetSourceLength(0);
            Intensity *= .5f * (1.f - FMath::Cos(FMath::DegreesToRadians(Outer)));
        }
        if (auto* R = Cast<URectLightComponent>(C))
        {
            R->SetSourceWidth(Number(L, TEXT("source_width_cm"), 64));
            R->SetSourceHeight(Number(L, TEXT("source_height_cm"), 64));
        }
        C->SetIntensity(Intensity); C->SetAttenuationRadius(Number(L, TEXT("optimized_radius_cm"), L->GetNumberField(TEXT("radius"))));
        const FVector Color = JsonVector(L, TEXT("color")); C->SetLightColor(FLinearColor(Color.X, Color.Y, Color.Z));
        bool Shadows = true; L->TryGetBoolField(TEXT("cast_shadows"), Shadows); C->SetCastShadows(Shadows);
        C->SetIndirectLightingIntensity(0.f);
        Lights.Emplace(Actor, Desired);
    }
    return true;
}

void Pump(FPreviewScene& Studio, int32 Count)
{
    for (int32 Frame = 0; Frame < Count; ++Frame)
    {
        ++GFrameCounter;
        FAssetCompilingManager::Get().ProcessAsyncTasks();
        Studio.GetWorld()->SendAllEndOfFrameUpdates();
        ENQUEUE_RENDER_COMMAND(DirectionBeginFrame)([](FRHICommandListImmediate&) { ++GFrameNumberRenderThread; });
        ENQUEUE_RENDER_COMMAND(DirectionEndFrame)([](FRHICommandListImmediate& Cmd) { Cmd.EndFrame(); });
        FlushRenderingCommands();
        FPlatformProcess::Sleep(.005f);
    }
}

// The project's proven commandlet staging route; ordinary Python RT export
// returned identical black images, which are not valid lighting evidence.
bool SavePng(UTextureRenderTarget2D* Target, const FString& Path)
{
    FlushRenderingCommands();
    auto* Resource = Target->GameThread_GetRenderTargetResource();
    FRHITexture* Texture = Resource ? Resource->GetRenderTargetTexture().GetReference() : nullptr;
    if (!Texture) return false;
    struct FReadback
    {
        TUniquePtr<FRHIGPUTextureReadback> Staging;
        TAtomic<bool> Done{false};
        TArray<FColor> Pixels;
    };
    auto Packet = MakeShared<FReadback, ESPMode::ThreadSafe>();
    Packet->Staging = MakeUnique<FRHIGPUTextureReadback>(TEXT("DungeonLightDirection"));
    ENQUEUE_RENDER_COMMAND(DirectionCopy)([Packet, Texture](FRHICommandListImmediate& Cmd)
    {
        Cmd.Transition(FRHITransitionInfo(Texture, ERHIAccess::Unknown, ERHIAccess::CopySrc));
        Packet->Staging->EnqueueCopy(Cmd, Texture);
        Cmd.Transition(FRHITransitionInfo(Texture, ERHIAccess::CopySrc, ERHIAccess::SRVMask));
    });
    const int32 Width = Target->SizeX, Height = Target->SizeY;
    const double Deadline = FPlatformTime::Seconds() + 15.;
    while (FPlatformTime::Seconds() < Deadline && !Packet->Done.Load())
    {
        ENQUEUE_RENDER_COMMAND(DirectionPoll)([Packet, Width, Height](FRHICommandListImmediate&)
        {
            if (Packet->Done.Load() || !Packet->Staging->IsReady()) return;
            int32 Pitch = 0, Rows = 0;
            const auto* Half = static_cast<const FFloat16Color*>(Packet->Staging->Lock(Pitch, &Rows));
            if (Half && Pitch >= Width && Rows >= Height)
            {
                Packet->Pixels.SetNumUninitialized(Width * Height);
                for (int32 Y = 0; Y < Height; ++Y)
                    for (int32 X = 0; X < Width; ++X)
                        Packet->Pixels[Y * Width + X] = Half[Y * Pitch + X].GetFloats().ToFColorSRGB();
            }
            if (Half) Packet->Staging->Unlock();
            Packet->Staging.Reset();
            Packet->Done.Store(true);
        });
        FlushRenderingCommands();
        FPlatformProcess::Sleep(.02f);
    }
    if (!Packet->Done.Load() || Packet->Pixels.IsEmpty()) return false;
    int32 Nonzero = 0;
    for (const FColor& Pixel : Packet->Pixels)
        Nonzero += (Pixel.R > 5 || Pixel.G > 5 || Pixel.B > 5) ? 1 : 0;
    UE_LOG(LogTemp, Display, TEXT("DIRECTION_PREVIEW pixels %s lit=%d/%d"), *Path, Nonzero, Packet->Pixels.Num());
    if (Nonzero < 100) return false;
    TArray64<uint8> Png;
    FImageUtils::PNGCompressImageArray(Width, Height,
        TArrayView64<const FColor>(Packet->Pixels.GetData(), Packet->Pixels.Num()), Png);
    return FFileHelper::SaveArrayToFile(Png, *Path);
}
}
#endif

int32 UDungeonLightDirectionCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    using namespace DungeonDirectionPreview;
    FPreviewScene Studio(FPreviewScene::ConstructionValues().SetEditor(false)
        .SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(true)
        .SetLightBrightness(0.f).SetSkyBrightness(0.f));
    UWorld* World = Studio.GetWorld();
    const bool Hall = FParse::Param(*Params, TEXT("ReceptionHall"));
    if (FParse::Param(*Params, TEXT("ProbeGameDirections")))
    {
        const auto Catalog = ReadCatalog();
        return Catalog && ProbeInitializedWorld(World, Catalog) ? 0 : 1;
    }
    TArray<TPair<ALight*, FQuat>> HallLights;
    if (Hall)
    {
        const auto Catalog = ReadCatalog();
        if (!Catalog || !BuildReception(World, Catalog, HallLights)) return 1;
    }
    ASpotLight* Light = nullptr;
    USpotLightComponent* Component = nullptr;
    const FVector Position(0, 0, 600);
    const FRotator Authored(-90, 0, 0);
    if (!Hall)
    {
    auto* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
    auto* Lamp = LoadObject<UStaticMesh>(nullptr,
        TEXT("/Game/Dungeons/IndustrialV1/Meshes/SM_CeilingLamp_Cool.SM_CeilingLamp_Cool"));
    if (!Cube || !Lamp) return 1;
    FActorSpawnParameters Spawn;
    Spawn.ObjectFlags |= RF_Transient;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto Mesh = [&](UStaticMesh* Shape, const FVector& Position, const FVector& Scale)
    {
        auto* Actor = World->SpawnActor<AStaticMeshActor>(Position, FRotator::ZeroRotator, Spawn);
        auto* Component = Actor->GetStaticMeshComponent();
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetStaticMesh(Shape);
        Actor->SetActorScale3D(Scale);
    };
    Mesh(Cube, FVector(0, 0, -5), FVector(24, 20, .1));
    Mesh(Cube, FVector(0, 0, 805), FVector(24, 20, .1));
    Mesh(Cube, FVector(0, 1005, 400), FVector(24, .1, 8));
    Mesh(Cube, FVector(-1205, 0, 400), FVector(.1, 20, 8));
    Mesh(Lamp, FVector(0, 0, 609), FVector::OneVector);
    Mesh(Cube, FVector(0, 0, 710), FVector(.035, .035, 1.8));

    // Exact old generator call. ASpotLight's native root adds another -90 pitch.
    Light = World->SpawnActor<ASpotLight>(Position, Authored, Spawn);
    Component = CastChecked<USpotLightComponent>(Light->GetLightComponent());
    Component->SetMobility(EComponentMobility::Movable);
    Component->SetIntensityUnits(ELightUnits::Lumens);
    Component->SetIntensity(2200.f);
    Component->SetAttenuationRadius(2000.f);
    Component->SetInnerConeAngle(50.f);
    Component->SetOuterConeAngle(65.f);
    Component->SetCastShadows(true);
    Component->SetSourceRadius(1.f);
    Component->SetSourceLength(0.f);
    Component->SetIndirectLightingIntensity(0.f);
    }

    auto* Target = NewObject<UTextureRenderTarget2D>(GetTransientPackage());
    Target->AddToRoot();
    Target->RenderTargetFormat = RTF_RGBA16f;
    Target->ClearColor = FLinearColor::Black;
    Target->InitAutoFormat(1024, 640);
    Target->UpdateResourceImmediate(true);
    auto* Capture = NewObject<USceneCaptureComponent2D>(GetTransientPackage());
    Capture->AddToRoot();
    Capture->TextureTarget = Target;
    Capture->CaptureSource = SCS_FinalColorLDR;
    Capture->bCaptureEveryFrame = false;
    Capture->bCaptureOnMovement = false;
    Capture->ProjectionType = ECameraProjectionMode::Perspective;
    Capture->FOVAngle = 72.f;
    Capture->ShowFlags.SetAtmosphere(false);
    Capture->ShowFlags.SetFog(false);
    Capture->ShowFlags.SetBloom(false);
    Capture->ShowFlags.SetMotionBlur(false);
    auto& PP = Capture->PostProcessSettings;
    PP.bOverride_AutoExposureMethod = true;
    PP.AutoExposureMethod = AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
    PP.AutoExposureApplyPhysicalCameraExposure = false;
    PP.bOverride_AutoExposureBias = true;
    PP.AutoExposureBias = 0.f;
    PP.bOverride_DynamicGlobalIlluminationMethod = true;
    PP.DynamicGlobalIlluminationMethod = EDynamicGlobalIlluminationMethod::None;
    PP.bOverride_ReflectionMethod = true;
    PP.ReflectionMethod = EReflectionMethod::None;
    Studio.AddComponent(Capture, FTransform::Identity);
    const FVector Eye = Hall ? FVector(-500, -1100, 550) : FVector(850, -1750, 380);
    const FVector Aim = Hall ? FVector(-1250, 600, 850) : FVector(-100, 0, 410);
    Capture->SetWorldLocationAndRotation(Eye, (Aim - Eye).Rotation());
    FAssetCompilingManager::Get().FinishAllCompilation();
    Pump(Studio, 30);
    const FString Output = FPaths::Combine(FPaths::ProjectDir(), Hall ?
        TEXT("SourceAssets/DungeonHallCeilingLight20261009/Receipts/HallRender") :
        TEXT("SourceAssets/DungeonLightDirection20261009/Receipts/NativeRender"));
    IFileManager::Get().MakeDirectory(*Output, true);
    bool Ok = true;
    for (int32 Version = 0; Version < 2; ++Version)
    {
        if (Hall)
        {
            if (Version == 1)
                for (const auto& Item : HallLights)
                {
                    // Production fix: mobility was established before this move.
                    const bool Accepted = Item.Key->SetActorLocationAndRotation(Item.Key->GetActorLocation(), Item.Value, false, nullptr, ETeleportType::TeleportPhysics);
                    Ok &= Accepted && Item.Key->GetActorForwardVector().Equals(Item.Value.GetAxisX(), .001);
                }
        }
        else
        {
        if (Version == 1)
            Light->SetActorLocationAndRotation(Position, Authored, false, nullptr, ETeleportType::TeleportPhysics);
        UE_LOG(LogTemp, Display, TEXT("DIRECTION_PREVIEW %s actual light direction %s"),
            Version == 0 ? TEXT("before") : TEXT("after"), *Component->GetForwardVector().ToString());
        }
        for (int32 Frame = 0; Frame < 8; ++Frame)
        {
            Pump(Studio, 1);
            Capture->CaptureScene();
            FlushRenderingCommands();
        }
        Ok &= SavePng(Target, FPaths::Combine(Output, Version == 0 ? TEXT("before.png") : TEXT("after.png")));
    }
    Studio.RemoveComponent(Capture);
    Capture->RemoveFromRoot();
    Target->RemoveFromRoot();
    UE_LOG(LogTemp, Display, TEXT("DIRECTION_PREVIEW %s (isolated room; no production map saved)"), Ok ? TEXT("PASS") : TEXT("FAIL"));
    return Ok ? 0 : 2;
#else
    return 1;
#endif
}
