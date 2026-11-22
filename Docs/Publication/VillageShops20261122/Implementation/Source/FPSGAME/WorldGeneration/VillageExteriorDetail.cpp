#include "VillageExteriorDetail.h"
#include "VillagePresentationView.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/AssetManager.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "InstancedStaticMeshDelegates.h"
#include "Misc/ScopeRWLock.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "StaticMeshComponentLODInfo.h"
#include "Serialization/JsonSerializer.h"

namespace
{
// Interior stock and tools have no distant silhouette. Apply once when the village
// binds so split-screen views use renderer culling and collision stays authoritative.
void ApplyShopPropDistance(UStaticMeshComponent& Part)
{
    static const TSet<FName> Small = {
        TEXT("SM_BakeryCounterBaguette"), TEXT("SM_BakeryCounterBread"), TEXT("SM_BakeryCoolingBoard"),
        TEXT("SM_CarpenterTools"), TEXT("SM_Gunshop_AccessoriesMounts"), TEXT("SM_Gunshop_OpticsMounts"),
        TEXT("SM_Gunshop_CounterTray"), TEXT("SM_HerbalistDryBunch"), TEXT("SM_HerbalistFlowerBunch"),
        TEXT("SM_HerbalistGatheringSieve"), TEXT("SM_TavernDish"), TEXT("SM_TavernEatingBowl"),
        TEXT("SM_TavernPitcher"), TEXT("SM_TavernSherd"), TEXT("SM_TavernTankard"), TEXT("SM_VillageIronStock")
    };
    static const TSet<FName> Medium = {
        TEXT("SM_BakeryGrainSack"), TEXT("SM_CarpenterJoinersChest"), TEXT("SM_CarpenterJoinersChestLid"),
        TEXT("SM_CarpenterStackedCases"), TEXT("SM_CarpenterWashBarrel"), TEXT("SM_SmithTongStand"),
        TEXT("SM_SmithWheelAndCases"), TEXT("SM_TavernAleCask")
    };
    const FName Name = Part.GetStaticMesh()->GetFName();
    const int32 End = Small.Contains(Name) ? 3500 : Medium.Contains(Name) ? 5500 : 0;
    if (!End) return;
    if (auto* Instances = Cast<UInstancedStaticMeshComponent>(&Part))
    {
        int32 Begin, CurrentEnd;
        Instances->GetCullDistances(Begin, CurrentEnd);
        if (!CurrentEnd || CurrentEnd > End)
            Instances->SetCullDistances(Begin > 0 ? FMath::Min(Begin, End - 500) : End - 500, End);
    }
    else if (Part.LDMaxDrawDistance <= 0.f || Part.LDMaxDrawDistance > End)
        Part.SetCullDistance(End);
}

// Only these fixed components can invalidate a baked group. All loaded villages share
// one pair of engine listeners, including in split screen or multi-world PIE.
class FExteriorChangeRouter
{
public:
    static FExteriorChangeRouter& Get()
    {
        static FExteriorChangeRouter Router;
        return Router;
    }

    void Watch(const TArray<TWeakObjectPtr<UStaticMeshComponent>>& Parts, TAtomic<bool>& Dirty)
    {
        if (!StateHandle.IsValid())
        {
            StateHandle = UActorComponent::MarkRenderStateDirtyEvent.AddRaw(this, &FExteriorChangeRouter::OnState);
            InstanceHandle = FInstancedStaticMeshDelegates::OnInstanceIndexUpdated.AddRaw(this, &FExteriorChangeRouter::OnInstances);
        }
        FWriteScopeLock Guard(Lock);
        for (const auto& Weak : Parts) if (auto* Part = Weak.Get()) Sources.Add(Part, &Dirty);
    }

    void Forget(TAtomic<bool>& Dirty)
    {
        bool bEmpty;
        {
            FWriteScopeLock Guard(Lock);
            for (auto It = Sources.CreateIterator(); It; ++It)
                if (It.Value() == &Dirty) It.RemoveCurrent();
            bEmpty = Sources.IsEmpty();
        }
        if (bEmpty)
        {
            UActorComponent::MarkRenderStateDirtyEvent.Remove(StateHandle);
            FInstancedStaticMeshDelegates::OnInstanceIndexUpdated.Remove(InstanceHandle);
            StateHandle.Reset();
            InstanceHandle.Reset();
        }
    }

private:
    FRWLock Lock;
    TMap<const UActorComponent*, TAtomic<bool>*> Sources;
    FDelegateHandle StateHandle, InstanceHandle;

    void OnState(UActorComponent& Part)
    {
        FReadScopeLock Guard(Lock);
        if (auto** Dirty = Sources.Find(&Part)) (*Dirty)->Store(true);
    }

    void OnInstances(UInstancedStaticMeshComponent* Part,
        TArrayView<const FInstancedStaticMeshDelegates::FInstanceIndexUpdateData>)
    {
        if (Part) OnState(*Part);
    }
};

bool ReadPlacement(UStaticMeshComponent& Part, const UInstancedStaticMeshComponent* Instances,
    int32 Index, const FTransform& Frame, FTransform& Local)
{
    FTransform World = Part.GetComponentTransform();
    if (Instances && !Instances->GetInstanceTransform(Index, World, true)) return false;
    Local = World.GetRelativeTransform(Frame);
    return true;
}

bool SamePlacement(const FTransform& A, const FTransform& B)
{
    return A.GetLocation().Equals(B.GetLocation(), .2) && A.GetRotation().Equals(B.GetRotation(), .0002) &&
        A.GetScale3D().Equals(B.GetScale3D(), .0002);
}

const FSoftObjectPath GateTimberFinish(TEXT("/Game/WorldGeneration/TemperateHills/AbandonedVillage/ExteriorMaterials/MI_Wood_00B_VillageExterior.MI_Wood_00B_VillageExterior"));
const FSoftObjectPath FinishPaths[] = {
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/AbandonedVillage/ExteriorMaterials/MI_Wood_00A_VillageExterior.MI_Wood_00A_VillageExterior")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/AbandonedVillage/ExteriorMaterials/MI_Slate_00A_VillageExterior.MI_Slate_00A_VillageExterior")),
    GateTimberFinish
};

const FSoftObjectPath SourcePaths[] = {
    FSoftObjectPath(TEXT("/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A.MI_Wood_00A")),
    FSoftObjectPath(TEXT("/Game/UnrealNormandy/MaterialInstances/MI_Slate_00A.MI_Slate_00A")),
    FSoftObjectPath(TEXT("/Game/UnrealNormandy/MaterialInstances/MI_Wood_00B.MI_Wood_00B"))
};

bool HasAuthoredSlateControls(const UMaterialInterface& Slate)
{
    static const TCHAR* const Names[] = {TEXT("RoughnessPower"), TEXT("AO_Power"), TEXT("Roughness_Multiplier"), TEXT("AO_Multiplier")};
    for (int32 Layer = 0; Layer < 3; ++Layer)
        for (const TCHAR* Name : Names)
        {
            float Value = 0.f;
            const FName Parameter(*FString::Printf(TEXT("TS%02d_%s"), Layer, Name));
            if (!Slate.GetScalarParameterValue(FMaterialParameterInfo(Parameter), Value) || Value != 1.f) return false;
        }
    return true;
}

struct FExteriorFinishes
{
    UMaterialInterface* Originals[UE_ARRAY_COUNT(FinishPaths)] = {};
    UMaterialInstance* Variants[UE_ARRAY_COUNT(FinishPaths)] = {};

    FExteriorFinishes()
    {
        for (int32 I = 0; I < UE_ARRAY_COUNT(FinishPaths); ++I)
        {
            auto* MI = Cast<UMaterialInstance>(FinishPaths[I].ResolveObject());
            float Strength = 1.f;
            auto* Source = Cast<UMaterialInterface>(SourcePaths[I].ResolveObject());
            if (MI && Source && Source->GetScalarParameterValue(FMaterialParameterInfo(TEXT("NormalGlobal_Intensity")), Strength) &&
                Strength == 0.f && (I != 1 || HasAuthoredSlateControls(*Source)))
            {
                Originals[I] = Source;
                Variants[I] = MI;
            }
        }
    }

    UMaterialInterface* Original(UMaterialInterface* Material) const
    {
        for (int32 I = 0; I < UE_ARRAY_COUNT(Variants); ++I)
            if (Variants[I] && Material == Variants[I]) return Originals[I];
        return Material;
    }

    void Apply(UStaticMeshComponent& Part) const
    {
        for (int32 Slot = 0; Slot < Part.GetNumMaterials(); ++Slot)
        {
            const auto* Current = Part.GetMaterial(Slot);
            for (int32 I = 0; I < UE_ARRAY_COUNT(Variants); ++I)
                if (Variants[I] && Current == Originals[I]) { Part.SetMaterial(Slot, Variants[I]); break; }
        }
    }
};

bool MatchesPlacement(UStaticMeshComponent& Part, const FJsonObject& Item, const FTransform& ActorPose,
    const FExteriorFinishes& Finishes, TArray<FTransform>& Placements)
{
    if (!Part.GetStaticMesh() || Part.GetStaticMesh()->GetPathName() != Item.GetStringField(TEXT("mesh")) ||
        !Part.bRenderInMainPass || Part.bRenderCustomDepth) return false;
    if (!Part.GetCustomPrimitiveData().Data.IsEmpty()) return false;
    for (const auto& LOD : Part.LODData) if (LOD.OverrideVertexColors) return false;
    const auto& Materials = Item.GetArrayField(TEXT("materials"));
    if (Part.GetNumMaterials() != Materials.Num()) return false;
    for (int32 I = 0; I < Materials.Num(); ++I)
        if (!Part.GetMaterial(I) || Finishes.Original(Part.GetMaterial(I))->GetPathName() != Materials[I]->AsString()) return false;
    auto* Instances = Cast<UInstancedStaticMeshComponent>(&Part);
    const auto& Poses = Item.GetArrayField(TEXT("poses"));
    if (Item.GetBoolField(TEXT("instanced")) != (Instances != nullptr) ||
        Poses.Num() != (Instances ? Instances->GetInstanceCount() : 1)) return false;
    for (int32 I = 0; I < Poses.Num(); ++I)
    {
        const auto& P = Poses[I]->AsArray();
        if (P.Num() != 10) return false;
        auto N = [&P](int32 J) { return P[J]->AsNumber(); };
        const FTransform Baked(FQuat(N(3),N(4),N(5),N(6)), FVector(N(0),N(1),N(2)), FVector(N(7),N(8),N(9)));
        FTransform Local;
        if (!ReadPlacement(Part, Instances, I, ActorPose, Local) || !SamePlacement(Local, Baked)) return false;
        Placements.Add(Baked);
    }
    return true;
}
}

UVillageExteriorDetail::UVillageExteriorDetail()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UVillageExteriorDetail::BindGateTimber(UStaticMeshComponent& Left, UStaticMeshComponent& Right)
{
    if (!Left.GetWorld() || Left.GetWorld()->IsNetMode(NM_DedicatedServer)) return;
    auto Apply = [LeftLeaf = TWeakObjectPtr<UStaticMeshComponent>(&Left), RightLeaf = TWeakObjectPtr<UStaticMeshComponent>(&Right)]()
    {
        const FExteriorFinishes Finishes;
        if (auto* Part = LeftLeaf.Get()) Finishes.Apply(*Part);
        if (auto* Part = RightLeaf.Get()) Finishes.Apply(*Part);
    };
    if (GateTimberFinish.ResolveObject()) Apply();
    else UAssetManager::GetStreamableManager().RequestAsyncLoad(GateTimberFinish,
        FStreamableDelegate::CreateWeakLambda(&Left, MoveTemp(Apply)));
}

void UVillageExteriorDetail::BindLevel(ULevel& Level)
{
    if (!Level.GetWorld() || Level.GetWorld()->IsNetMode(NM_DedicatedServer)) return;
    TArray<FSoftObjectPath> Pending;
    for (const auto& Path : FinishPaths)
        if (!Path.ResolveObject()) Pending.Add(Path);
    for (const auto& Path : SourcePaths)
        if (!Path.ResolveObject()) Pending.Add(Path);
    if (Pending.IsEmpty())
    {
        BindPreparedLevel(Level);
        return;
    }
    UAssetManager::GetStreamableManager().RequestAsyncLoad(Pending,
        FStreamableDelegate::CreateWeakLambda(&Level, [Weak = TWeakObjectPtr<ULevel>(&Level)]()
        {
            if (auto* Loaded = Weak.Get(); Loaded && Loaded->bIsVisible) BindPreparedLevel(*Loaded);
        }));
}

void UVillageExteriorDetail::BindPreparedLevel(ULevel& Level)
{
    const FExteriorFinishes Finishes;
    for (AActor* Actor : Level.Actors)
    {
        if (!IsValid(Actor)) continue;
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Actor);
        for (auto* Part : Meshes) if (Part->GetStaticMesh())
        {
            Finishes.Apply(*Part);
            ApplyShopPropDistance(*Part);
        }
    }
    FString Json;
    if (!FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir() /
        TEXT("WorldGeneration/TemperateHills/FixedLayout/village-exterior-lod.json")))) return;
    TArray<TSharedPtr<FJsonValue>> Groups;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Groups)) return;
    TMap<FName,AActor*> Actors;
    for (AActor* Actor : Level.Actors) if (IsValid(Actor)) Actors.Add(Actor->GetFName(), Actor);
    for (const auto& Entry : Groups)
    {
        const auto& Group = *Entry->AsObject();
        auto* Owner = Actors.FindRef(FName(*Group.GetStringField(TEXT("actor"))));
        if (!Owner || !Owner->GetRootComponent()) continue;
        const FSoftObjectPath AssetPath(Group.GetStringField(TEXT("proxy")));
        TInlineComponentArray<UVillageExteriorDetail*> Existing(Owner);
        if (Existing.ContainsByPredicate([&](const auto* Other) { return Other->Asset == AssetPath; })) continue;
        FBox Bounds(ForceInit);
        TArray<TWeakObjectPtr<UStaticMeshComponent>> Members;
        TArray<bool> Depth;
        TArray<FSourceAppearance> Expected;
        for (const auto& Value : Group.GetArrayField(TEXT("parts")))
        {
            const auto& Item = *Value->AsObject();
            auto* Part = FindObjectFast<UStaticMeshComponent>(Owner, FName(*Item.GetStringField(TEXT("component"))));
            auto& Appearance = Expected.AddDefaulted_GetRef();
            if (!Part || !MatchesPlacement(*Part, Item, Owner->GetActorTransform(), Finishes, Appearance.Placements)) break;
            Appearance.Mesh = Part->GetStaticMesh();
            for (int32 Slot = 0; Slot < Part->GetNumMaterials(); ++Slot)
                Appearance.Materials.Add(Part->GetMaterial(Slot));
            Members.Add(Part);
            Depth.Add(Part->bRenderInDepthPass);
            Bounds += Part->Bounds.GetBox();
        }
        if (Members.IsEmpty() || Members.Num() != Group.GetArrayField(TEXT("parts")).Num()) continue;
        auto* Detail = NewObject<UVillageExteriorDetail>(Owner, NAME_None, RF_Transient);
        Detail->Parts = MoveTemp(Members);
        Detail->DepthPass = MoveTemp(Depth);
        Detail->Appearances = MoveTemp(Expected);
        Detail->Asset = AssetPath;
        Detail->LocalCenter = Owner->GetActorTransform().InverseTransformPosition(Bounds.GetCenter());
        Detail->Radius = Bounds.GetExtent().Size();
        Owner->AddInstanceComponent(Detail);
        Detail->RegisterComponent();
    }
}

void UVillageExteriorDetail::OnRegister()
{
    Super::OnRegister();
    if (!Parts.IsEmpty())
    {
        bSourcesChanged.Store(true);
        FExteriorChangeRouter::Get().Watch(Parts, bSourcesChanged);
    }
}

void UVillageExteriorDetail::OnUnregister()
{
    if (!Parts.IsEmpty()) FExteriorChangeRouter::Get().Forget(bSourcesChanged);
    Display(false);
    Super::OnUnregister();
}

bool UVillageExteriorDetail::SourcesStillMatch() const
{
    const FTransform Frame = GetOwner()->GetActorTransform();
    for (int32 I = 0; I < Parts.Num(); ++I)
    {
        auto* Part = Parts[I].Get();
        const auto& Expected = Appearances[I];
        if (!Part || Part->GetStaticMesh() != Expected.Mesh.Get() ||
            Part->GetNumMaterials() != Expected.Materials.Num() || !Part->GetCustomPrimitiveData().Data.IsEmpty()) return false;
        for (int32 Slot = 0; Slot < Expected.Materials.Num(); ++Slot)
            if (Part->GetMaterial(Slot) != Expected.Materials[Slot].Get()) return false;
        auto* Instances = Cast<UInstancedStaticMeshComponent>(Part);
        if (Instances && Instances->GetInstanceCount() != Expected.Placements.Num()) return false;
        for (int32 J = 0; J < Expected.Placements.Num(); ++J)
        {
            FTransform Local;
            if (!ReadPlacement(*Part, Instances, J, Frame, Local) || !SamePlacement(Local, Expected.Placements[J])) return false;
        }
    }
    return true;
}

void UVillageExteriorDetail::PrepareProxy()
{
    auto* Mesh = Cast<UStaticMesh>(Asset.ResolveObject());
    if (!Mesh || !GetOwner() || !IsRegistered() || Proxy) return;
    Proxy = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
    Proxy->SetupAttachment(GetOwner()->GetRootComponent());
    Proxy->SetMobility(GetOwner()->GetRootComponent()->Mobility);
    Proxy->SetVisibility(false);
    Proxy->SetRenderInMainPass(false);
    Proxy->SetRenderInDepthPass(false);
    Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Proxy->SetGenerateOverlapEvents(false);
    Proxy->SetCanEverAffectNavigation(false);
    Proxy->SetCastShadow(false);
    Proxy->SetAffectDistanceFieldLighting(false);
    Proxy->bAffectDynamicIndirectLighting = false;
    Proxy->bVisibleInReflectionCaptures = false;
    Proxy->bVisibleInRealTimeSkyCaptures = false;
    Proxy->SetVisibleInRayTracing(false);
    Proxy->SetStaticMesh(Mesh);
    FExteriorFinishes().Apply(*Proxy);
    GetOwner()->AddInstanceComponent(Proxy);
    Proxy->RegisterComponent();
}

void UVillageExteriorDetail::Display(bool bUseProxy)
{
    if (bShowingProxy == bUseProxy) return;
    for (int32 I = 0; I < Parts.Num(); ++I)
        if (auto* Part = Parts[I].Get())
        {
            Part->SetRenderInMainPass(!bUseProxy);
            Part->SetRenderInDepthPass(!bUseProxy && DepthPass[I]);
        }
    if (Proxy)
    {
        Proxy->SetVisibility(bUseProxy);
        Proxy->SetRenderInMainPass(bUseProxy);
        Proxy->SetRenderInDepthPass(bUseProxy);
    }
    bShowingProxy = bUseProxy;
}

void UVillageExteriorDetail::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(Dt, Type, TickFunction);
    const FVector Center = GetOwner()->GetActorTransform().TransformPosition(LocalCenter);
    const double Distance = VillagePresentationView::Distance(*GetWorld(), Center, Radius);
    const double Enter = FMath::Max(7400., Radius * 5.);
    bool bFar = Distance > Enter * (bShowingProxy ? .84 : 1.) && !GetOwner()->IsHidden();
    bool bRefresh = false;
    if (bFar)
    {
        // Keep repair visibility and lifetime immediate. Material slots and instance
        // transforms only need comparing when entering the far range or after an edit.
        for (const auto& Weak : Parts)
        {
            const auto* Part = Weak.Get();
            if (!Part || !Part->IsRegistered() || !Part->IsVisible() || Part->bHiddenInGame || Part->bRenderCustomDepth)
            {
                bFar = false;
                break;
            }
            bRefresh |= Part->IsRenderStateDirty() || Part->IsRenderTransformDirty() || Part->IsRenderInstancesDirty();
        }
        if (bFar)
        {
            const bool bDirty = bSourcesChanged.Exchange(false);
            if (!bWasEligible || bDirty || bRefresh) bSourcesMatch = SourcesStillMatch();
        }
    }
    bWasEligible = bFar;
    bFar &= bSourcesMatch;
    if (bFar && !Loading && !Proxy)
        Loading = UAssetManager::GetStreamableManager().RequestAsyncLoad(Asset,
            FStreamableDelegate::CreateUObject(this, &ThisClass::PrepareProxy));
    Display(bFar && Proxy && !Proxy->IsPSOPrecaching());
}

void UVillageExteriorDetail::EndPlay(const EEndPlayReason::Type Reason)
{
    Display(false);
    if (Loading) Loading->CancelHandle();
    Loading.Reset();
    if (Proxy) Proxy->DestroyComponent();
    Super::EndPlay(Reason);
}
