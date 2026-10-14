#pragma once

#include "CoreMinimal.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/World.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "UObject/UnrealType.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "UObject/StrongObjectPtr.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/BellowSacLobber.h"
#include "../Monsters/BellowSacProjectile.h"
#include "../Monsters/QuadrupedAnimationTemplate.h"

/** Precache only loaded encounter templates; never spawn/register hidden monsters. */
struct FDungeonMonsterRenderPreparation
{
    TArray<TWeakObjectPtr<UClass>> Classes;
    TArray<TStrongObjectPtr<UPrimitiveComponent>> Components;
    int32 SubmitCursor = 0;
    double StartedAt = 0.;
    TArray<TSharedPtr<FStreamableHandle>> DependencyLoads;
    int32 DependencyPathsRequested = 0;

    ~FDungeonMonsterRenderPreparation()
    {
        for (const auto& Handle : DependencyLoads)
            if (Handle.IsValid() && !Handle->HasLoadCompleted()) Handle->CancelHandle();
    }

    static USkeletalMesh* BodyMesh(const ACharacter* Defaults)
    {
        USkeletalMesh* Mesh = Defaults->GetMesh()->GetSkeletalMeshAsset();
        // All ground M-series except Wolf derivatives expose the actual body
        // through VisualMesh; their native OnConstruction binds it later.
        if (const auto* Property = FindFProperty<FObjectPropertyBase>(Defaults->GetClass(), TEXT("VisualMesh")))
            if (auto* Visual = Cast<USkeletalMesh>(Property->GetObjectPropertyValue_InContainer(Defaults))) Mesh = Visual;
        if (const auto* Wolf = Cast<AWolfMonster>(Defaults); Wolf && Wolf->AnimationSet)
            Mesh = Wolf->AnimationSet->ReferenceMesh;
        return Mesh;
    }

    void RetainDependencies(TArray<TObjectPtr<UObject>>& Assets) const
    {
        // Skills can keep soft references after BeginPlay. Keep this run's
        // selected dependencies alive, not every species in the catalogue.
        for (const auto& Handle : DependencyLoads)
            if (Handle.IsValid())
            {
                TArray<UObject*> Loaded;
                Handle->GetLoadedAssets(Loaded);
                for (UObject* Asset : Loaded) if (Asset) Assets.AddUnique(Asset);
            }
    }

    void AddClass(UClass* Class)
    {
        if (!Class || !Class->IsChildOf(AActor::StaticClass())) return;
        if (Classes.Contains(Class)) return;
        Classes.Add(Class);
        TArray<FSoftObjectPath> Paths;
        auto Collect = [&Paths](const UObject* Object)
        {
            for (TFieldIterator<FSoftObjectProperty> It(Object->GetClass()); It; ++It)
            {
                for (int32 Index = 0; Index < It->ArrayDim; ++Index)
                {
                    const auto* Value = It->GetPropertyValuePtr_InContainer(Object, Index);
                    if (Value && !Value->IsNull()) Paths.AddUnique(Value->ToSoftObjectPath());
                }
            }
        };
        const auto* Defaults = Class->GetDefaultObject<AActor>();
        Collect(Defaults);
        TInlineComponentArray<UActorComponent*> Parts(Defaults);
        for (const auto* Part : Parts) Collect(Part);
        if (!Paths.IsEmpty())
        {
            DependencyPathsRequested += Paths.Num();
            DependencyLoads.Add(UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths));
        }
        if (StartedAt == 0.) StartedAt = FPlatformTime::Seconds();
    }

    bool Pump(double Deadline, FString& Error)
    {
        while (SubmitCursor < Classes.Num() && FPlatformTime::Seconds() < Deadline)
        {
            const UClass* Class = Classes[SubmitCursor].Get();
            const auto* Defaults = Class ? Cast<ACharacter>(Class->GetDefaultObject()) : nullptr;
            if (!Defaults) { ++SubmitCursor; continue; }
            USkeletalMesh* Mesh = BodyMesh(Defaults);
            // These species bind their authored mesh in OnConstruction. Reading
            // only the CDO's component would silently precache an empty/wrong mesh.
            const auto* Bellow = Cast<ABellowSacLobber>(Defaults);
            if (!Mesh) { Error = TEXT("怪物缺少渲染网格：") + Class->GetPathName(); return false; }
            const auto* Data = Mesh->IsCompiling() ? nullptr : Mesh->GetResourceForRendering();
            if (!Data || !Data->IsLODDataReady() || (Bellow && Bellow->SacMesh && Bellow->SacMesh->IsCompiling())) break;
            auto* Component = NewObject<USkeletalMeshComponent>(GetTransientPackage(), NAME_None, RF_Transient, Defaults->GetMesh());
            Components.Emplace(Component);
            Component->SetSkeletalMeshAsset(Mesh);
            Component->PrecachePSOs();
            // Native auxiliary meshes with an assigned template are part of
            // the real recipe too (weapons, tissue, props and cloth proxies).
            TInlineComponentArray<UMeshComponent*> MeshTemplates(Defaults);
            for (auto* Template : MeshTemplates)
            {
                if (Template == Defaults->GetMesh()) continue;
                if (auto* Static = Cast<UStaticMeshComponent>(Template); Static && Static->GetStaticMesh())
                {
                    auto* Part = NewObject<UStaticMeshComponent>(GetTransientPackage(), Static->GetClass(), NAME_None, RF_Transient, Static);
                    Components.Emplace(Part); Part->PrecachePSOs();
                }
                else if (auto* Skinned = Cast<USkeletalMeshComponent>(Template); Skinned && Skinned->GetSkeletalMeshAsset())
                {
                    auto* Part = NewObject<USkeletalMeshComponent>(GetTransientPackage(), NAME_None, RF_Transient, Skinned);
                    Components.Emplace(Part); Part->PrecachePSOs();
                }
            }
            if (const auto* Property = FindFProperty<FObjectPropertyBase>(Defaults->GetClass(), TEXT("CloakMaterial")))
                if (auto* Material = Cast<UMaterialInterface>(Property->GetObjectPropertyValue_InContainer(Defaults)))
                {
                    auto* Cloaked = NewObject<USkeletalMeshComponent>(GetTransientPackage(), NAME_None, RF_Transient, Defaults->GetMesh());
                    Components.Emplace(Cloaked); Cloaked->SetSkeletalMeshAsset(Mesh);
                    for (int32 Slot = 0; Slot < Cloaked->GetNumMaterials(); ++Slot) Cloaked->SetMaterial(Slot, Material);
                    Cloaked->PrecachePSOs();
                }
            if (Bellow && Bellow->SacMesh)
            {
                // Match both the capsule and instanced fragments, without spawning
                // an attack, registering components or allocating a preview world.
                const auto* Projectile = GetDefault<ABellowSacProjectile>();
                TInlineComponentArray<UStaticMeshComponent*> Templates(Projectile);
                for (auto* Template : Templates)
                {
                    auto* Part = NewObject<UStaticMeshComponent>(GetTransientPackage(), Template->GetClass(), NAME_None, RF_Transient, Template);
                    Components.Emplace(Part);
                    Part->SetStaticMesh(Bellow->SacMesh);
                    Part->SetMaterial(0, Bellow->SacMaterial);
                    Part->PrecachePSOs();
                }
            }
            ++SubmitCursor;
        }
        bool bReady = SubmitCursor == Classes.Num();
        for (const auto& Handle : DependencyLoads)
            if (Handle.IsValid()) bReady &= Handle->HasLoadCompleted() || Handle->WasCanceled();
        for (const auto& Component : Components) bReady &= !Component->IsPSOPrecaching();
        if (!bReady && FPlatformTime::Seconds() - StartedAt > 120.)
            Error = TEXT("怪物材质与渲染管线准备超时");
        return bReady;
    }
};
