#include "VillageShadowCapture.h"
#include "../Building/BronzeTorch.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
const FName VillageShadowTag(TEXT("FPS.F6.VillageShadow"));
constexpr int32 MaxSampledCasters = 512;

TArray<TSharedPtr<FJsonValue>> VectorValues(FVector V)
{
    return {MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z)};
}

template <typename T>
TArray<TSharedPtr<FJsonValue>> ShadowNumbers(const TArray<T>& Values)
{
    TArray<TSharedPtr<FJsonValue>> Result;
    Result.Reserve(Values.Num());
    for (T Value : Values) Result.Add(MakeShared<FJsonValueNumber>(Value));
    return Result;
}
}

bool FVillageShadowCapture::FindFixtures(UWorld* World)
{
    if (!World || !World->IsGameWorld()) return false;
    auto* PC = World->GetFirstPlayerController();
    if (!PC || !PC->IsLocalController() || !PC->PlayerCameraManager) return false;
    Eye = PC->PlayerCameraManager->GetCameraLocation();
    WorldName = World->GetPathName();
    for (TActorIterator<ABronzeTorch> It(World); It; ++It)
    {
        if (!It->IsExteriorClockFixture() || !It->IsLit()) continue;
        auto* Light = It->FindComponentByClass<UPointLightComponent>();
        if (!Light || !Light->IsRegistered() || !Light->IsVisible() || !Light->bAffectsWorld ||
            !Light->CastShadows || Light->Intensity <= 0.f) continue;
        const double Range = Light->MaxDrawDistance > 0.f ? Light->MaxDrawDistance : 15000.;
        if (FVector::DistSquared(Eye, Light->GetComponentLocation()) > FMath::Square(Range + Light->AttenuationRadius)) continue;
        Fixtures.Add({Light->GetPathName(), Light->GetComponentLocation(), Light->AttenuationRadius});
    }
    return !Fixtures.IsEmpty();
}

void FVillageShadowCapture::Start(UWorld& World)
{
    bActive = true;
    auto& Console = IConsoleManager::Get();
    if (auto* CVar = Console.FindConsoleVariable(TEXT("r.Shadow.Virtual.NonNanite.NumPageAreaDiagSlots")))
    {
        if (CVar->GetInt() == 0)
        {
            OwnedSlots = CVar;
            CVar->Set(8, ECVF_SetByPluginHighPriority, VillageShadowTag);
        }
        PageSlots = CVar->GetInt();
    }
    if (auto* CVar = Console.FindConsoleVariable(TEXT("r.Shadow.Virtual.NonNanite.LargeInstancePageAreaThreshold")))
    {
        if (PageSlots != 0 && CVar->GetInt() < 0)
        {
            OwnedThreshold = CVar;
            CVar->Set(128, ECVF_SetByPluginHighPriority, VillageShadowTag);
        }
        PageThreshold = CVar->GetInt();
    }
    for (TActorIterator<AActor> It(&World); It; ++It)
    {
        TInlineComponentArray<UPrimitiveComponent*> Parts(*It);
        for (auto* Part : Parts)
        {
            if (!Part->IsRegistered() || !Part->CastShadow || !Part->bCastDynamicShadow ||
                ((!Part->IsVisible() || Part->bHiddenInGame || It->IsHidden()) && !Part->bCastHiddenShadow)) continue;
            const FBox Bounds = Part->Bounds.GetBox();
            int32 Nearest = INDEX_NONE;
            double Best = TNumericLimits<double>::Max();
            for (int32 I = 0; I < Fixtures.Num(); ++I)
            {
                const double Separation = Bounds.ComputeSquaredDistanceToPoint(Fixtures[I].Center);
                if (Separation < Best && Separation <= FMath::Square(Fixtures[I].Radius))
                {
                    Best = Separation;
                    Nearest = I;
                }
            }
            if (Nearest == INDEX_NONE) continue;
            auto& Row = Casters.AddDefaulted_GetRef();
            Row.Component = Part;
            Row.Path = Part->GetPathName();
            Row.LightIndex = Nearest;
            Row.Transform = Part->GetComponentTransform();
            Row.Bounds = Bounds;
            Row.InitialExtent = Bounds.GetExtent();
            Row.BoundsScale = Part->BoundsScale;
            Row.bParentBounds = Part->bUseAttachParentBound;
            Row.Invalidation = StaticEnum<EShadowCacheInvalidationBehavior>()->GetNameStringByValue(int64(Part->ShadowCacheInvalidationBehavior));
            if (const auto* Static = Cast<UStaticMeshComponent>(Part); Static && Static->GetStaticMesh())
                Row.Mesh = Static->GetStaticMesh()->GetPathName();
        }
    }
    CandidateCount = Casters.Num();
    if (CandidateCount > MaxSampledCasters)
    {
        Casters.Sort([this](const FCaster& A, const FCaster& B) {
            return A.Bounds.ComputeSquaredDistanceToPoint(Eye) < B.Bounds.ComputeSquaredDistanceToPoint(Eye);
        });
        Casters.SetNum(MaxSampledCasters);
    }
    Sample();
}

void FVillageShadowCapture::Sample()
{
    if (!bActive) return;
    const double Now = FPlatformTime::Seconds();
    if (Now < NextSample) return;
    NextSample = Now + .25;
    const int32 Index = SampleTimes.Add(Now);
    for (auto& Row : Casters)
    {
        if (Row.GoneAt != INDEX_NONE) continue;
        const auto* Part = Row.Component.Get();
        if (!Part || !Part->IsRegistered()) { Row.GoneAt = Index; continue; }
        const FTransform& Transform = Part->GetComponentTransform();
        const FBox Bounds = Part->Bounds.GetBox();
        if (!Transform.Equals(Row.Transform)) Row.Moved.Add(Index);
        if (!Bounds.GetExtent().Equals(Row.Bounds.GetExtent(), .1)) Row.Resized.Add(Index);
        Row.Transform = Transform;
        Row.Bounds = Bounds;
    }
}

void FVillageShadowCapture::Finish(const FString& Directory)
{
    if (!bActive) return;
    bActive = false;
    if (OwnedSlots) OwnedSlots->Unset(ECVF_SetByPluginHighPriority, VillageShadowTag);
    if (OwnedThreshold) OwnedThreshold->Unset(ECVF_SetByPluginHighPriority, VillageShadowTag);
    auto Doc = MakeShared<FJsonObject>();
    Doc->SetStringField(TEXT("world"), WorldName);
    Doc->SetStringField(TEXT("scope"), TEXT("Fixtures and eligible component bounds at capture start; nearest intersecting light sphere, without occlusion or spot-cone clipping. CPU movement and extent changes sampled at 4 Hz are candidates. VSM counters in engine.utrace are renderer totals; native LogRenderer page-overlap warnings name large non-Nanite footprints, not per-component invalidated pages."));
    Doc->SetArrayField(TEXT("camera_start_cm"), VectorValues(Eye));
    Doc->SetNumberField(TEXT("eligible_components"), CandidateCount);
    Doc->SetNumberField(TEXT("native_overlap_slots"), PageSlots);
    Doc->SetNumberField(TEXT("native_overlap_page_threshold"), PageThreshold);
    Doc->SetArrayField(TEXT("sample_monotonic_seconds"), ShadowNumbers(SampleTimes));
    TArray<TSharedPtr<FJsonValue>> Lights, Objects;
    for (const auto& Light : Fixtures)
    {
        auto Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("path"), Light.Path);
        Item->SetArrayField(TEXT("position_cm"), VectorValues(Light.Center));
        Item->SetNumberField(TEXT("radius_cm"), Light.Radius);
        Lights.Add(MakeShared<FJsonValueObject>(Item));
    }
    for (const auto& Row : Casters)
    {
        auto Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("path"), Row.Path);
        Item->SetStringField(TEXT("static_mesh"), Row.Mesh);
        Item->SetNumberField(TEXT("nearest_fixture"), Row.LightIndex);
        Item->SetArrayField(TEXT("initial_extent_cm"), VectorValues(Row.InitialExtent));
        Item->SetNumberField(TEXT("bounds_scale"), Row.BoundsScale);
        Item->SetBoolField(TEXT("uses_parent_bounds"), Row.bParentBounds);
        Item->SetStringField(TEXT("shadow_cache_behavior"), Row.Invalidation);
        Item->SetArrayField(TEXT("moved_sample_indices"), ShadowNumbers(Row.Moved));
        Item->SetArrayField(TEXT("resized_sample_indices"), ShadowNumbers(Row.Resized));
        if (Row.GoneAt != INDEX_NONE) Item->SetNumberField(TEXT("unregistered_sample"), Row.GoneAt);
        Objects.Add(MakeShared<FJsonValueObject>(Item));
    }
    Doc->SetArrayField(TEXT("fixtures"), Lights);
    Doc->SetArrayField(TEXT("casters"), Objects);
    FString Json;
    if (!FJsonSerializer::Serialize(Doc, TJsonWriterFactory<>::Create(&Json)) ||
        !FFileHelper::SaveStringToFile(Json, *(Directory / TEXT("village-shadows.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
        UE_LOG(LogTemp, Warning, TEXT("F6: could not save village shadow observations to %s"), *Directory);
}