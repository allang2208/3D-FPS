#pragma once

#include "CoreMinimal.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
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
#include "Misc/App.h"
#include "PSOPrecache.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/BellowSacLobber.h"
#include "../Monsters/BellowSacProjectile.h"
#include "../Monsters/QuadrupedAnimationTemplate.h"
#include "../Monsters/M14SoftBodyDeath.h"
#include "DungeonCombatEffectPreparation.h"

/** Precache only loaded encounter templates; never spawn/register hidden monsters. */
struct FDungeonMonsterRenderPreparation
{
    TArray<TWeakObjectPtr<UClass>> Classes;
    TArray<TStrongObjectPtr<UPrimitiveComponent>> Components;
    int32 SubmitCursor = 0;
    double StartedAt = 0.;
    TArray<TSharedPtr<FStreamableHandle>> DependencyLoads;
    int32 DependencyPathsRequested = 0;
    int32 AdoptedDependencyLoads = 0;
    bool bReportedPSOMode = false;
    TSet<FSoftObjectPath> RequestedDependencies;
    FDungeonCombatEffectPreparation CombatEffects;

    ~FDungeonMonsterRenderPreparation()
    {
        CancelDependencyLoads();
    }

    void CancelDependencyLoads()
    {
        // A failed assembly keeps its state for the error report. Cancel at
        // failure/cancellation too, rather than waiting for state destruction.
        for (const auto& Handle : DependencyLoads)
            if (Handle.IsValid() && !Handle->HasLoadCompleted()) Handle->CancelHandle();
        DependencyLoads.Reset();
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
        CombatEffects.RetainDependencies(Assets);
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
        // Inspect authored property containers, not arbitrary UObject graphs.
        // Arrays/maps/structs can hold the same FX soft references as direct fields.
        TFunction<void(FProperty*,const void*)> CollectValue;
        CollectValue = [this,&Paths,&CollectValue](FProperty* Property,const void* Value)
        {
            if(const auto* Soft=CastField<FSoftObjectProperty>(Property))
            {
                const auto Path=Soft->GetPropertyValue(Value).ToSoftObjectPath();
                if(!Path.IsNull()&&!RequestedDependencies.Contains(Path))
                {RequestedDependencies.Add(Path);Paths.Add(Path);}
            }
            else if(const auto* Object=CastField<FObjectPropertyBase>(Property))
                CombatEffects.Add(Object->GetObjectPropertyValue(Value));
            else if(const auto* Array=CastField<FArrayProperty>(Property))
            {
                FScriptArrayHelper Values(Array,Value);
                for(int32 I=0;I<Values.Num();++I)CollectValue(Array->Inner,Values.GetRawPtr(I));
            }
            else if(const auto* Map=CastField<FMapProperty>(Property))
            {
                FScriptMapHelper Values(Map,Value);
                for(int32 I=0;I<Values.GetMaxIndex();++I)if(Values.IsValidIndex(I))
                {CollectValue(Map->KeyProp,Values.GetKeyPtr(I));CollectValue(Map->ValueProp,Values.GetValuePtr(I));}
            }
            else if(const auto* Set=CastField<FSetProperty>(Property))
            {
                FScriptSetHelper Values(Set,Value);
                for(int32 I=0;I<Values.GetMaxIndex();++I)if(Values.IsValidIndex(I))CollectValue(Set->ElementProp,Values.GetElementPtr(I));
            }
            else if(const auto* Struct=CastField<FStructProperty>(Property))
                for(TFieldIterator<FProperty> It(Struct->Struct);It;++It)
                    for(int32 I=0;I<It->ArrayDim;++I)CollectValue(*It,It->ContainerPtrToValuePtr<void>(Value,I));
        };
        auto Collect = [&CollectValue](const UObject* Object)
        {
            for(TFieldIterator<FProperty> It(Object->GetClass());It;++It)
                for(int32 I=0;I<It->ArrayDim;++I)CollectValue(*It,It->ContainerPtrToValuePtr<void>(Object,I));
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
        // Dedicated servers and NullRHI test peers still need the gameplay soft
        // dependencies, but cannot provide GPU render/PSO readiness.
        const bool bNeedsRendering = FApp::CanEverRender();
        if (bNeedsRendering && !bReportedPSOMode)
        {
            bReportedPSOMode = true;
            UE_LOG(LogTemp, Display, TEXT("[DungeonPreparation] Component PSO precaching enabled=%d editor=%d. Asset readiness and instance GPU warmup are separate stages."),
                IsComponentPSOPrecachingEnabled(), GIsEditor);
        }
        // Package readiness alone does not prepare Niagara scripts or its PSOs.
        while(AdoptedDependencyLoads<DependencyLoads.Num()&&FPlatformTime::Seconds()<Deadline)
        {
            const auto& Handle=DependencyLoads[AdoptedDependencyLoads];
            if(Handle.IsValid()&&!Handle->HasLoadCompleted()&&!Handle->WasCanceled())break;
            if(Handle.IsValid()&&Handle->HasLoadCompleted())
            {
                TArray<UObject*> Loaded;Handle->GetLoadedAssets(Loaded);
                for(auto* Asset:Loaded)CombatEffects.Add(Asset);
            }
            ++AdoptedDependencyLoads;
        }
        while (bNeedsRendering && SubmitCursor < Classes.Num() && FPlatformTime::Seconds() < Deadline)
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
            const auto* SoftBinding=Cast<UMonsterSoftCorpseBinding>(Mesh->GetAssetUserDataOfClass(UMonsterSoftCorpseBinding::StaticClass()));
            auto* CorpseMesh=SoftBinding&&SoftBinding->Data?SoftBinding->Data->CorpseMesh.Get():nullptr;
            if(CorpseMesh&&CorpseMesh->IsCompiling())break;
            if (!Data || !Data->IsLODDataReady() || (Bellow && Bellow->SacMesh && Bellow->SacMesh->IsCompiling())) break;
            auto* Component = NewObject<USkeletalMeshComponent>(GetTransientPackage(), NAME_None, RF_Transient, Defaults->GetMesh());
            Components.Emplace(Component);
            Component->SetSkeletalMeshAsset(Mesh);
            Component->PrecachePSOs();
            if(CorpseMesh)
            {
                // Death uses a different mesh/material set and a poseable component.
                // Prepare that actual vertex-factory path without starting a corpse.
                auto* Corpse=NewObject<UPoseableMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
                Components.Emplace(Corpse);Corpse->SetSkinnedAssetAndUpdate(CorpseMesh);
                Corpse->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                Corpse->SetBoundsScale(3.f);Corpse->SetForcedLOD(1);Corpse->PrecachePSOs();
            }
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
        bool bReady = !bNeedsRendering || SubmitCursor == Classes.Num();
        bReady &= AdoptedDependencyLoads==DependencyLoads.Num();
        if(bNeedsRendering)bReady &= CombatEffects.Pump(Deadline,Error);
        for (const auto& Handle : DependencyLoads)
            if (Handle.IsValid()) bReady &= Handle->HasLoadCompleted() || Handle->WasCanceled();
        for (const auto& Component : Components) bReady &= !Component->IsPSOPrecaching();
        if (!bReady && FPlatformTime::Seconds() - StartedAt > 120.)
            Error = TEXT("怪物材质与渲染管线准备超时");
        return bReady;
    }
};
