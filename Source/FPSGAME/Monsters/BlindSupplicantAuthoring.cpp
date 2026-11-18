#include "BlindSupplicantAuthoring.h"

#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if WITH_EDITOR
#include "WitchRebuiltClothingAsset.h"
#include "M07InteractingClothingAsset.h"
#include "M07MembraneClothingAsset.h"
#include "ClothingAssetFactory.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "Math/RotationMatrix.h"
#include "Misc/FileHelper.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshModel.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#endif

#include "BlindSupplicantClothAuthoringPrivate.h"
using namespace BlindSupplicantCloth;

namespace BlindSupplicantCloth
{
FString WriteGillReceipt(const TSharedRef<FJsonObject>& Receipt)
{
    FString Result;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
    FJsonSerializer::Serialize(Receipt, Writer);
    return Result;
}

}

FString UBlindSupplicantAuthoring::BuildGillCloth(USkeletalMesh* Mesh, const FString& WeightManifestFile, bool bExtractSimulation)
{
    const TSharedRef<FJsonObject> Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("success"), false);
    Receipt->SetStringField(TEXT("mesh"), Mesh ? Mesh->GetPathName() : FString());
    Receipt->SetBoolField(TEXT("extract_simulation"), bExtractSimulation);
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("tested"), false);
    Receipt->SetBoolField(TEXT("inter_panel_collision"), false);
    Receipt->SetStringField(TEXT("collision_boundary"), TEXT("Six separate cloth assets collide with the supplied body capsules; panel-to-panel collision is not provided. Author static panel clearance in the source mesh."));
    bool bChanged = false;
    auto Fail = [&](const FString& Stage, const FString& Error)
    {
        Receipt->SetStringField(TEXT("stage"), Stage);
        Receipt->SetStringField(TEXT("error"), Error);
        Receipt->SetBoolField(TEXT("mesh_changed"), bChanged);
        return WriteGillReceipt(Receipt);
    };
#if WITH_EDITOR
    if (!Mesh || !Mesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/BlindSupplicantM07/")))
        return Fail(TEXT("scope"), TEXT("Only skeletal meshes inside /Game/Monsters/BlindSupplicantM07/ can be authored."));
    if (!IsInGameThread()) return Fail(TEXT("thread"), TEXT("Invoke this authoring function on the editor/commandlet game thread."));
    auto* Model = Mesh->GetImportedModel();
    if (!Model || Model->LODModels.IsEmpty()) return Fail(TEXT("mesh"), TEXT("The mesh has no imported LOD0 model."));

    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(WeightManifestFile, Panels, Capsules, Error)) return Fail(TEXT("manifest"), Error);
    for (const auto& Capsule : Capsules)
        if (Mesh->GetRefSkeleton().FindBoneIndex(Capsule.Bone) == INDEX_NONE)
            return Fail(TEXT("collision_bone"), FString::Printf(TEXT("Collision bone %s is absent from this mesh's skeleton."), *Capsule.Bone.ToString()));

    TArray<FGillDraft> Drafts;
    Drafts.SetNum(GillCount);
    const auto PreviousAssets = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : PreviousAssets)
    {
        int32 PanelIndex = INDEX_NONE;
        if (Asset && Asset->GetOuter() == Mesh)
            for (int32 Index = 0; Index < GillCount; ++Index)
            {
                const FString Base = GillAssetName(Index);
                if (Asset->GetName() == Base || Asset->GetName().StartsWith(Base + TEXT("_"))) PanelIndex = Index;
            }
        auto* Gill = Cast<UWitchRebuiltClothingAsset>(Asset);
        if (PanelIndex == INDEX_NONE || !Gill || Drafts[PanelIndex].Asset.IsValid())
            return Fail(TEXT("existing_cloth"), TEXT("The mesh contains unknown, external or duplicate cloth assets; they have been left unchanged."));
        Drafts[PanelIndex].Asset.Reset(Gill);
    }

    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        const FString DisplaySlot = TEXT("M07_Gill_") + Panels[Index].Id;
        const auto Display = GillSections(Mesh, DisplaySlot);
        if (Display.Num() != 1)
            return Fail(TEXT("display_section"), FString::Printf(TEXT("Expected one LOD0 section for material slot %s; found %d."), *DisplaySlot, Display.Num()));
        if (bExtractSimulation)
        {
            const FString ProxySlot = TEXT("M07_GillSimulationProxy_") + Panels[Index].Id;
            const auto Proxy = GillSections(Mesh, ProxySlot);
            if (Proxy.Num() != 1 || Model->LODModels[0].Sections[Proxy[0]].HasClothingData())
                return Fail(TEXT("proxy_section"), FString::Printf(TEXT("Expected one unbound LOD0 section for material slot %s."), *ProxySlot));
        }
        else if (!Drafts[Index].Asset.IsValid() || Drafts[Index].Asset->LodData.IsEmpty())
            return Fail(TEXT("saved_cloth"), FString::Printf(TEXT("No saved simulation asset for panel %s; extract the ClothBuildSource mesh first."), *Panels[Index].Id));
    }

    if (bExtractSimulation)
    {
        TStrongObjectPtr<UClothingAssetFactory> Factory(NewObject<UClothingAssetFactory>());
        for (int32 Index = 0; Index < GillCount; ++Index)
        {
            FSkeletalMeshClothBuildParams Params;
            Params.AssetName = GillAssetName(Index) + TEXT("_Extract");
            Params.LodIndex = 0;
            Params.SourceSection = GillSections(Mesh, TEXT("M07_GillSimulationProxy_") + Panels[Index].Id)[0];
            // Stage all six simulations and manifest maps before removing any
            // render sections, so malformed input leaves the source geometry.
            Params.bRemoveFromMesh = false;
            TStrongObjectPtr<UClothingAssetCommon> Extracted(Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Mesh, Params)));
            if (!Extracted.IsValid() || Extracted->LodData.IsEmpty())
                return Fail(TEXT("extraction"), FString::Printf(TEXT("Cannot extract the simulation proxy for panel %s."), *Panels[Index].Id));
            auto* Cloth = NewObject<UWitchRebuiltClothingAsset>(Mesh,
                MakeUniqueObjectName(Mesh, UWitchRebuiltClothingAsset::StaticClass(), FName(*GillAssetName(Index))), RF_Transactional);
            Cloth->InitializeSimulationFrom(Extracted.Get());
            Drafts[Index].Asset.Reset(Cloth);
        }
    }
    for (int32 Index = 0; Index < GillCount; ++Index)
        if (!MapGillDistances(Panels[Index], Drafts[Index], Error)) return Fail(TEXT("weight_mapping"), Error);

    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    bChanged = true;
    for (UClothingAssetBase* Asset : PreviousAssets) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    if (bExtractSimulation)
    {
        TArray<int32> Proxies;
        for (const auto& Panel : Panels)
            Proxies.Add(GillSections(Mesh, TEXT("M07_GillSimulationProxy_") + Panel.Id)[0]);
        Proxies.Sort([](int32 A, int32 B) { return A > B; });
        for (const int32 SectionIndex : Proxies) Mesh->RemoveMeshSection(0, SectionIndex);
    }

    auto* Collision = MakeGillCollision(Mesh, Capsules);
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh,
        MakeUniqueObjectName(Mesh, UChaosClothSharedSimConfig::StaticClass(), TEXT("M07_GillChaosSharedConfig")), RF_Transactional);
    Shared->IterationCount = 4;
    Shared->MaxIterationCount = 6;
    Shared->SubdivisionCount = 1;
    Shared->bUseLocalSpaceSimulation = true;
    for (auto& Draft : Drafts)
    {
        ConfigureGill(Draft, Collision, Shared);
        Draft.Asset->RefreshBoneMapping(Mesh);
        Mesh->AddClothingAsset(Draft.Asset.Get());
    }

    TArray<TSharedPtr<FJsonValue>> PanelReceipts;
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        auto* Cloth = Drafts[Index].Asset.Get();
        const auto RenderSections = GillSections(Mesh, TEXT("M07_Gill_") + Panels[Index].Id);
        if (RenderSections.Num() != 1 || !Cloth->BindToSkeletalMesh(Mesh, 0, RenderSections[0], 0))
            return Fail(TEXT("binding"), FString::Printf(TEXT("Cannot bind saved simulation to the display section for panel %s."), *Panels[Index].Id));
        const int32 Render = RenderSections[0];
        auto& Lod = Mesh->GetImportedModel()->LODModels[0];
        auto& Section = Lod.Sections[Render];
        Section.bDisabled = false;
        auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.bDisabled = false;
        User.CorrespondClothAssetIndex = Index;
        User.ClothingData.AssetGuid = Cloth->GetAssetGuid();
        User.ClothingData.AssetLodIndex = 0;

        const TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("id"), Panels[Index].Id);
        Item->SetStringField(TEXT("cloth_asset"), Cloth->GetPathName());
        Item->SetNumberField(TEXT("display_section"), Render);
        Item->SetNumberField(TEXT("simulation_vertices"), Drafts[Index].Distances.Num());
        Item->SetNumberField(TEXT("simulation_triangles"), Cloth->LodData[0].PhysicalMeshData.Indices.Num() / 3);
        Item->SetNumberField(TEXT("pinned_vertices"), Drafts[Index].PinnedVertices);
        Item->SetNumberField(TEXT("max_distance_cm"), Drafts[Index].MaxDistanceCm);
        Item->SetNumberField(TEXT("max_manifest_match_error_cm"), Drafts[Index].MaxMatchErrorCm);
        PanelReceipts.Add(MakeShared<FJsonValueObject>(Item));
    }
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"), true);
    Receipt->SetBoolField(TEXT("mesh_changed"), true);
    Receipt->SetStringField(TEXT("stage"), TEXT("authored"));
    Receipt->SetStringField(TEXT("package"), Mesh->GetOutermost()->GetName());
    Receipt->SetStringField(TEXT("collision_asset"), Collision->GetPathName());
    Receipt->SetNumberField(TEXT("collision_capsules"), Capsules.Num());
    Receipt->SetNumberField(TEXT("proxy_sections_removed"), bExtractSimulation ? GillCount : 0);
    Receipt->SetNumberField(TEXT("manifest_match_tolerance_cm"), ManifestMatchToleranceCm);
    Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
    Receipt->SetArrayField(TEXT("panels"), PanelReceipts);
    return WriteGillReceipt(Receipt);
#else
    return Fail(TEXT("editor_only"), TEXT("Gill cloth authoring requires an Editor or commandlet build."));
#endif
}

FString UBlindSupplicantAuthoring::BuildInteractingGillCloth(USkeletalMesh* Mesh, const FString& WeightManifestFile)
{
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("success"), false);
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("tested"), false);
    auto Fail = [&](const FString& Error)
    {
        Receipt->SetStringField(TEXT("error"), Error);
        return WriteGillReceipt(Receipt);
    };
#if WITH_EDITOR
    if (!Mesh || Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07"))
        return Fail(TEXT("Only the saved M07 display mesh may be authored."));
    const auto Previous = Mesh->GetMeshClothingAssets();
    if (Previous.Num() == 1 && Cast<UM07InteractingClothingAsset>(Previous[0]))
    {
        Receipt->SetBoolField(TEXT("success"), true);
        Receipt->SetBoolField(TEXT("inter_panel_collision"), true);
        Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
        Receipt->SetStringField(TEXT("cloth_asset"), Previous[0]->GetPathName());
        return WriteGillReceipt(Receipt);
    }
    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(WeightManifestFile, Panels, Capsules, Error)) return Fail(Error);
    TArray<FGillDraft> Parts;
    Parts.SetNum(GillCount);
    if (Previous.Num() != GillCount) return Fail(TEXT("The six original saved simulations are required."));
    for (const auto& Base : Previous)
    {
        auto* Part = Cast<UWitchRebuiltClothingAsset>(Base.Get());
        if (!Part || Part->LodData.Num() != 1) return Fail(TEXT("An original gill simulation is unavailable."));
        int32 Id = INDEX_NONE;
        for (int32 Index = 0; Index < GillCount; ++Index)
            if (Part->GetName().StartsWith(GillAssetName(Index))) Id = Index;
        if (Id == INDEX_NONE || Parts[Id].Asset.IsValid()) return Fail(TEXT("The original gill identities must be unique."));
        Parts[Id].Asset.Reset(Part);
    }
    int32 VertexCount = 0, IndexCount = 0;
    TArray<int32> Offsets, Sections;
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        if (!Parts[Index].Asset.IsValid() || !MapGillDistances(Panels[Index], Parts[Index], Error)) return Fail(Error);
        const auto Render = GillSections(Mesh, TEXT("M07_Gill_") + Panels[Index].Id);
        if (Render.Num() != 1) return Fail(TEXT("Each gill display panel requires one saved section."));
        const auto& Section = Mesh->GetImportedModel()->LODModels[0].Sections[Render[0]];
        if (Section.ClothingData.AssetGuid != Parts[Index].Asset->GetAssetGuid() || Section.ClothMappingDataLODs.IsEmpty())
            return Fail(TEXT("Each original display-to-simulation mapping must already be authored."));
        Offsets.Add(VertexCount);
        Sections.Add(Render[0]);
        const auto& Physical = Parts[Index].Asset->LodData[0].PhysicalMeshData;
        VertexCount += Physical.Vertices.Num();
        IndexCount += Physical.Indices.Num();
    }
    // Reuse the six existing low-density islands and their exact display
    // captures. They remain disconnected anatomically, but share one solver
    // particle set, so triangle self-collision includes neighbouring panels.
    TStrongObjectPtr<UClothingAssetCommon> CombinedSource(NewObject<UClothingAssetCommon>());
    CombinedSource->LodData.AddDefaulted();
    auto& Physical = CombinedSource->LodData[0].PhysicalMeshData;
    Physical.Reset(VertexCount, IndexCount);
    FGillDraft Combined;
    int32 TriangleIndex = 0;
    for (int32 PartIndex = 0; PartIndex < GillCount; ++PartIndex)
    {
        auto* Source = Parts[PartIndex].Asset.Get();
        const auto& Input = Source->LodData[0].PhysicalMeshData;
        const int32 Offset = Offsets[PartIndex];
        for (int32 Index = 0; Index < Input.Vertices.Num(); ++Index)
        {
            Physical.Vertices[Offset + Index] = Input.Vertices[Index];
            Physical.Normals[Offset + Index] = Input.Normals[Index];
            Physical.VertexColors[Offset + Index] = Input.VertexColors.IsValidIndex(Index) ? Input.VertexColors[Index] : FColor::White;
            auto BoneData = Input.BoneData[Index];
            for (int32 Influence = 0; Influence < FClothVertBoneData::MaxTotalInfluences; ++Influence)
            {
                if (BoneData.BoneWeights[Influence] <= 0.f) continue;
                const int32 BoneIndex = BoneData.BoneIndices[Influence];
                if (!Source->UsedBoneNames.IsValidIndex(BoneIndex)) return Fail(TEXT("An original simulation influence has no named bone."));
                BoneData.BoneIndices[Influence] = CombinedSource->UsedBoneNames.AddUnique(Source->UsedBoneNames[BoneIndex]);
            }
            Physical.BoneData[Offset + Index] = BoneData;
        }
        for (uint32 Index : Input.Indices) Physical.Indices[TriangleIndex++] = Index + Offset;
        Combined.Distances.Append(Parts[PartIndex].Distances);
        Combined.PinnedVertices += Parts[PartIndex].PinnedVertices;
        Combined.MaxDistanceCm = FMath::Max(Combined.MaxDistanceCm, Parts[PartIndex].MaxDistanceCm);
    }
    Physical.CalculateNumInfluences();
    auto* Cloth = NewObject<UM07InteractingClothingAsset>(Mesh,
        MakeUniqueObjectName(Mesh, UM07InteractingClothingAsset::StaticClass(), TEXT("M07_InteractingGills")), RF_Transactional);
    Cloth->InitializeSimulationFrom(CombinedSource.Get());
    Cloth->PanelVertexOffsets = Offsets;
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        auto& Panel = Cloth->PanelSimulations.Add_GetRef(Parts[Index].Asset->LodData[0].PhysicalMeshData);
        for (int32 Vertex = 0; Vertex < Panel.BoneData.Num(); ++Vertex)
            Panel.BoneData[Vertex] = Cloth->LodData[0].PhysicalMeshData.BoneData[Offsets[Index] + Vertex];
        Cloth->PanelMaterialSlots.Add(FName(*(TEXT("M07_Gill_") + Panels[Index].Id)));
    }
    Combined.Asset.Reset(Cloth);
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh,
        MakeUniqueObjectName(Mesh, UChaosClothSharedSimConfig::StaticClass(), TEXT("M07_InteractingGillsShared")), RF_Transactional);
    Shared->IterationCount = 6;
    Shared->MaxIterationCount = 8;
    Shared->SubdivisionCount = 1;
    Shared->bUseLocalSpaceSimulation = true;
    auto* Collision = MakeGillCollision(Mesh, Capsules);
    ConfigureGill(Combined, Collision, Shared);
    auto* Config = Cloth->GetClothConfig<UChaosClothConfig>();
    Config->bUseSelfCollisions = true;
    Config->SelfCollisionThickness = 1.0f;
    Config->SelfCollisionFriction = 0.1f;
    Config->AnimDriveStiffness = {0.28f, 0.28f};
    Cloth->RefreshBoneMapping(Mesh);
    Cloth->CalculateReferenceBoneIndex();
    Cloth->LodMap = {0};
    Cloth->InvalidateAllCachedData();

    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    // No high-detail mesh recapture is needed: existing section captures are
    // local indices into each island. Offset only the three particle indices;
    // the fourth index stores skinning/fixed-vertex flags and is preserved.
    auto& Lod = Mesh->GetImportedModel()->LODModels[0];
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        auto& Section = Lod.Sections[Sections[Index]];
        for (auto& MappingLod : Section.ClothMappingDataLODs)
            for (auto& Mapping : MappingLod)
                for (int32 Corner = 0; Corner < 3; ++Corner)
                    Mapping.SourceMeshVertIndices[Corner] += Offsets[Index];
        Section.CorrespondClothAssetIndex = 0;
        Section.ClothingData.AssetGuid = Cloth->GetAssetGuid();
        Section.ClothingData.AssetLodIndex = 0;
        auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex = 0;
        User.ClothingData = Section.ClothingData;
        User.bDisabled = false;
        Section.bDisabled = false;
    }
    Mesh->SetMeshClothingAssets({Cloth});
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"), true);
    Receipt->SetBoolField(TEXT("inter_panel_collision"), true);
    Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
    Receipt->SetStringField(TEXT("cloth_asset"), Cloth->GetPathName());
    Receipt->SetStringField(TEXT("collision_asset"), Collision->GetPathName());
    Receipt->SetNumberField(TEXT("display_panels"), GillCount);
    Receipt->SetNumberField(TEXT("simulation_vertices"), VertexCount);
    Receipt->SetNumberField(TEXT("simulation_triangles"), IndexCount / 3);
    Receipt->SetNumberField(TEXT("pinned_vertices"), Combined.PinnedVertices);
    Receipt->SetNumberField(TEXT("self_collision_thickness_cm"), Config->SelfCollisionThickness);
    return WriteGillReceipt(Receipt);
#else
    return Fail(TEXT("Editor authoring build required."));
#endif
}

FString UBlindSupplicantAuthoring::RemoveGillClothForReimport(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if (!Mesh || (Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ArmSweepV16") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_LegJointsV17") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18")) ||
        !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty())
        return TEXT("{\"success\":false,\"error\":\"Only this task's imported M07 display may be detached.\"}");
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    const auto Previous = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : Previous)
        if (Asset) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    for (auto& Lod : Mesh->GetImportedModel()->LODModels)
        for (auto& Section : Lod.Sections)
        {
            Section.ClothingData.AssetGuid.Invalidate();
            Section.ClothingData.AssetLodIndex = INDEX_NONE;
            Section.CorrespondClothAssetIndex = INDEX_NONE;
            Section.ClothMappingDataLODs.Reset();
            auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
            User.ClothingData = Section.ClothingData;
            User.CorrespondClothAssetIndex = INDEX_NONE;
        }
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    return TEXT("{\"success\":true,\"saved\":false,\"stage\":\"detached_for_geometry_reimport\"}");
#else
    return TEXT("{\"success\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}

FString UBlindSupplicantAuthoring::BuildWitchStyleMembrane(USkeletalMesh* Mesh, USkeletalMesh* SimulationSource,
    UClothingAssetCommon* ReferenceCloth, const FString& WeightManifestFile)
{
#if WITH_EDITOR
    auto Receipt=MakeShared<FJsonObject>();Receipt->SetBoolField(TEXT("success"),false);
    auto Fail=[&](const FString& Error){Receipt->SetStringField(TEXT("error"),Error);return WriteGillReceipt(Receipt);};
    if(!Mesh || Mesh->GetOutermost()->GetName()!=TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18") ||
        !SimulationSource || !SimulationSource->GetImportedModel() || SimulationSource->GetImportedModel()->LODModels.IsEmpty() ||
        !ReferenceCloth || !ReferenceCloth->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/WitchRebuilt/")))
        return Fail(TEXT("M07 display/proxy and current Witch cloth reference are required."));
    const auto Proxy=GillSections(SimulationSource,TEXT("M07_GillSimulation"));
    if(Proxy.Num()!=1)return Fail(TEXT("The two continuous sheets must share one hidden proxy section."));
    TArray<FGillPanelManifest> Panels;TArray<FGillCapsuleManifest> Capsules;FString Error;
    if(!ReadGillManifest(WeightManifestFile,Panels,Capsules,Error,2))return Fail(Error);
    for(const auto& Capsule:Capsules)
        if(Mesh->GetRefSkeleton().FindBoneIndex(Capsule.Bone)==INDEX_NONE)return Fail(TEXT("A membrane collider bone is missing."));
    UChaosClothConfig* TemplateConfig=nullptr;UChaosClothSharedSimConfig* TemplateShared=nullptr;
    for(const auto& Pair:ReferenceCloth->ClothConfigs)
    {
        if(auto* Config=Cast<UChaosClothConfig>(Pair.Value))TemplateConfig=Config;
        if(auto* Shared=Cast<UChaosClothSharedSimConfig>(Pair.Value))TemplateShared=Shared;
    }
    if(!TemplateConfig||!TemplateShared)return Fail(TEXT("The saved Witch cloth has no Chaos configuration."));
    FSkeletalMeshClothBuildParams Params;
    Params.AssetName=TEXT("M07_ContinuousMembraneProxyV36");Params.LodIndex=0;Params.SourceSection=Proxy[0];Params.bRemoveFromMesh=false;
    TStrongObjectPtr<UClothingAssetFactory> Factory(NewObject<UClothingAssetFactory>());
    TStrongObjectPtr<UClothingAssetCommon> Extracted(Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(SimulationSource,Params)));
    if(!Extracted.IsValid()||Extracted->LodData.Num()!=1)return Fail(TEXT("Continuous membrane extraction failed."));
    auto* Cloth=NewObject<UM07MembraneClothingAsset>(Mesh,
        MakeUniqueObjectName(Mesh,UM07MembraneClothingAsset::StaticClass(),TEXT("M07_WitchStyleMembraneV36")),RF_Transactional);
    Cloth->InitializeSimulationFrom(Extracted.Get());
    FGillDraft Draft;Draft.Asset.Reset(Cloth);
    const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
    Draft.Distances.SetNum(Physical.Vertices.Num());
    for(int32 V=0;V<Physical.Vertices.Num();++V)
    {
        double Best=TNumericLimits<double>::Max();float Distance=0;
        for(const auto& Panel:Panels)for(int32 I=0;I<Panel.VerticesCm.Num();++I)
        {
            const double D=FVector3f::DistSquared(Physical.Vertices[V],Panel.VerticesCm[I]);
            if(D<Best){Best=D;Distance=Panel.MaxDistanceCm[I];}
        }
        if(Best>FMath::Square(ManifestMatchToleranceCm))return Fail(TEXT("Imported proxy units differ from authored centimeters."));
        Draft.Distances[V]=Distance;Draft.PinnedVertices+=Distance==0;Draft.MaxDistanceCm=FMath::Max(Draft.MaxDistanceCm,Distance);
    }
    if(!Draft.PinnedVertices||Draft.PinnedVertices==Draft.Distances.Num())return Fail(TEXT("Continuous sheets require fixed roots and free hems."));
    auto* Shared=DuplicateObject<UChaosClothSharedSimConfig>(TemplateShared,Cloth);
    ConfigureGill(Draft,MakeGillCollision(Mesh,Capsules),Shared);
    // Copy the actual installed Witch config, then adapt the contact scale to
    // the taller membrane. No separate point/face self-collision solver.
    auto* Config=DuplicateObject<UChaosClothConfig>(TemplateConfig,Cloth);
    Config->CollisionThickness=1.2f;
    Config->bUseSelfCollisions=false;Config->bUseSelfCollisionSpheres=true;
    Config->SelfCollisionSphereRadius=1.1f;Config->SelfCollisionSphereRadiusCullMultiplier=2.5f;
    Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(),Config);
    Cloth->ApplyParameterMasks(true);Cloth->InvalidateAllCachedData();
    Cloth->RefreshBoneMapping(Mesh);Cloth->CalculateReferenceBoneIndex();
    FScopedSkeletalMeshPostEditChange Change(Mesh);Mesh->Modify();
    const auto Old=Mesh->GetMeshClothingAssets();
    for(UClothingAssetBase* Asset:Old)if(Asset)Asset->UnbindFromSkeletalMesh(Mesh,INDEX_NONE,INDEX_NONE);
    Mesh->SetMeshClothingAssets({Cloth});
    auto& Lod=Mesh->GetImportedModel()->LODModels[0];
    int32 Bound=0;
    for(int32 S=0;S<Lod.Sections.Num();++S)
    {
        bool HasMovingVertex=false;
        for(const auto& V:Lod.Sections[S].SoftVertices)if(V.Color.A>0){HasMovingVertex=true;break;}
        if(!HasMovingVertex)continue;
        if(!Cloth->BindToSkeletalMesh(Mesh,0,S,0))return Fail(TEXT("A membrane display section could not bind."));
        auto& Section=Lod.Sections[S];auto& User=Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex=0;User.ClothingData=Section.ClothingData;User.bDisabled=Section.bDisabled=false;++Bound;
    }
    if(!Bound)return Fail(TEXT("The imported display has no authored cloth mobility alpha."));
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"),true);Receipt->SetBoolField(TEXT("saved"),false);
    Receipt->SetStringField(TEXT("template"),ReferenceCloth->GetPathName());
    Receipt->SetStringField(TEXT("cloth"),Cloth->GetPathName());
    Receipt->SetNumberField(TEXT("physical_vertices"),Physical.Vertices.Num());
    Receipt->SetNumberField(TEXT("physical_triangles"),Physical.Indices.Num()/3);
    Receipt->SetNumberField(TEXT("pinned_vertices"),Draft.PinnedVertices);
    Receipt->SetNumberField(TEXT("maximum_travel_cm"),Draft.MaxDistanceCm);
    Receipt->SetNumberField(TEXT("bound_sections"),Bound);
    Receipt->SetNumberField(TEXT("solver_iterations"),Shared->IterationCount);
    Receipt->SetNumberField(TEXT("solver_max_iterations"),Shared->MaxIterationCount);
    Receipt->SetNumberField(TEXT("solver_subdivisions"),Shared->SubdivisionCount);
    Receipt->SetNumberField(TEXT("anim_drive_stiffness"),Config->AnimDriveStiffness.Low);
    return WriteGillReceipt(Receipt);
#else
    return TEXT("{\"success\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}

FString UBlindSupplicantAuthoring::BuildInteractingGillClothFromSavedSource(USkeletalMesh* Mesh, USkeletalMesh* SimulationSource, const FString& WeightManifestFile)
{
#if WITH_EDITOR
    auto Receipt = MakeShared<FJsonObject>();
    auto Fail = [&](const FString& Error)
    {
        Receipt->SetBoolField(TEXT("success"), false);
        Receipt->SetStringField(TEXT("error"), Error);
        return WriteGillReceipt(Receipt);
    };
    if (!Mesh || (Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ContinuousV02") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV03") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV04") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV05") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV06") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV07") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV08") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV11") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ArmSweepV16") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_LegJointsV17") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18")) || !SimulationSource ||
        !SimulationSource->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/BlindSupplicantM07/Working/")))
        return Fail(FString::Printf(TEXT("Only the M07 display and its preserved simulation source may be restored. Display=%s Simulation=%s"),
            *GetPathNameSafe(Mesh), *GetPathNameSafe(SimulationSource)));
    if (GillSections(Mesh, TEXT("M07_Gills")).Num() == 1)
        return BuildContinuousGillCloth(Mesh, SimulationSource, WeightManifestFile);
    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(WeightManifestFile, Panels, Capsules, Error)) return Fail(Error);
    const auto Sources = SimulationSource->GetMeshClothingAssets();
    if (Sources.Num() != GillCount) return Fail(TEXT("The preserved source must contain the six original gill simulations."));
    TArray<FGillDraft> Parts;
    Parts.SetNum(GillCount);
    for (UClothingAssetBase* Base : Sources)
    {
        auto* Source = Cast<UClothingAssetCommon>(Base);
        if (!Source || Source->LodData.Num() != 1) return Fail(TEXT("The preserved source cloth data is unavailable."));
        int32 Index = INDEX_NONE;
        for (int32 Id = 0; Id < GillCount; ++Id)
            if (Source->GetName().StartsWith(GillAssetName(Id))) Index = Id;
        if (Index == INDEX_NONE || Parts[Index].Asset.IsValid()) return Fail(TEXT("The preserved source gill identities are ambiguous."));
        TStrongObjectPtr<UClothingAssetCommon> Copy(NewObject<UClothingAssetCommon>());
        Copy->LodData = Source->LodData;
        Copy->UsedBoneNames = Source->UsedBoneNames;
        Copy->UsedBoneIndices = Source->UsedBoneIndices;
        Copy->ReferenceBoneIndex = Source->ReferenceBoneIndex;
        auto* Part = NewObject<UWitchRebuiltClothingAsset>(Mesh,
            MakeUniqueObjectName(Mesh, UWitchRebuiltClothingAsset::StaticClass(), FName(*GillAssetName(Index))), RF_Transactional);
        Part->InitializeSimulationFrom(Copy.Get());
        Parts[Index].Asset.Reset(Part);
        if (!MapGillDistances(Panels[Index], Parts[Index], Error)) return Fail(Error);
    }
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    const auto Old = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : Old) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    auto* Collision = MakeGillCollision(Mesh, Capsules);
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh, NAME_None, RF_Transactional);
    Shared->IterationCount = 4;
    Shared->MaxIterationCount = 6;
    Shared->SubdivisionCount = 1;
    for (auto& Part : Parts)
    {
        ConfigureGill(Part, Collision, Shared);
        Part.Asset->RefreshBoneMapping(Mesh);
        Mesh->AddClothingAsset(Part.Asset.Get());
    }
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        const auto Render = GillSections(Mesh, TEXT("M07_Gill_") + Panels[Index].Id);
        if (Render.Num() != 1 || !Parts[Index].Asset->BindToSkeletalMesh(Mesh, 0, Render[0], 0))
            return Fail(TEXT("A preserved gill simulation could not be restored to the display section."));
        auto& Lod = Mesh->GetImportedModel()->LODModels[0];
        auto& Section = Lod.Sections[Render[0]];
        auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex = Index;
        User.ClothingData = Section.ClothingData;
        User.bDisabled = Section.bDisabled = false;
    }
    return BuildInteractingGillCloth(Mesh, WeightManifestFile);
#else
    return TEXT("{\"success\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}
