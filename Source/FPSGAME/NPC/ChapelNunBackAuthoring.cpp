#include "CoreMinimal.h"
#if WITH_EDITOR
#include "Engine/SkeletalMesh.h"
#include "AssetCompilingManager.h"
#include "ClothingAsset.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/SavePackage.h"
#include "UObject/Package.h"
#include "Serialization/JsonSerializer.h"

// The old mage robe has a separate outer hood and a disconnected inner hood
// inside TorsoLining. Remove only those shells, preserving the back panel and
// the existing skirt simulation asset, collision and all unaffected attributes.
int32 RepairChapelNunBack(const FString& OutputDirectory)
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe"));
    if(!Mesh||!Mesh->GetImportedModel())return 20;
    FAssetCompilingManager::Get().FinishAllCompilation();
    struct FNunClothBinding { UClothingAssetCommon* Cloth; int32 Lod; int32 ClothLod; FName Slot; };
    TArray<FNunClothBinding> Bindings;
    for(int32 Lod=0;Lod<Mesh->GetImportedModel()->LODModels.Num();++Lod)
        for(const auto& Section:Mesh->GetImportedModel()->LODModels[Lod].Sections)
            if(Section.HasClothingData())
                for(const auto& Asset:Mesh->GetMeshClothingAssets())
                    if(auto* Cloth=Cast<UClothingAssetCommon>(Asset);Cloth&&Cloth->GetAssetGuid()==Section.ClothingData.AssetGuid)
                        Bindings.Add({Cloth,Lod,Section.ClothingData.AssetLodIndex,Mesh->GetMaterials()[Section.MaterialIndex].MaterialSlotName});
    TArray<TSharedPtr<FJsonValue>> LodReports;
    Mesh->Modify();
    for(const auto& Binding:Bindings)Binding.Cloth->UnbindFromSkeletalMesh(Mesh,Binding.Lod,INDEX_NONE);
    for(int32 Lod=0;Lod<Mesh->GetLODNum();++Lod)
    {
        FMeshDescription* Description=Mesh->GetMeshDescription(Lod);
        if(!Description)
        {
            FMeshDescription Recovered;
            Mesh->GetImportedModel()->LODModels[Lod].GetMeshDescription(Mesh,Lod,Recovered);
            Description=Mesh->CreateMeshDescription(Lod,MoveTemp(Recovered));
            auto* Info=Mesh->GetLODInfo(Lod);
            Info->BuildSettings.bRecomputeNormals=false;
            Info->ReductionSettings.BaseLOD=Lod;
            Info->ReductionSettings.NumOfTrianglesPercentage=1.f;
            Info->ReductionSettings.NumOfVertPercentage=1.f;
            Info->ReductionSettings.MaxNumOfTrianglesPercentage=MAX_uint32;
            Info->ReductionSettings.MaxNumOfVertsPercentage=MAX_uint32;
        }
        if(!Description)return 21;
        FStaticMeshAttributes Attributes(*Description);
        const auto Positions=Attributes.GetVertexPositions();
        const auto SlotNames=Attributes.GetPolygonGroupMaterialSlotNames();
        TArray<FTriangleID> Remove;
        TArray<FTriangleID> Lining;
        for(FTriangleID Triangle:Description->Triangles().GetElementIDs())
        {
            const FName Slot=SlotNames[Description->GetTrianglePolygonGroup(Triangle)];
            if(Slot==TEXT("RobeHood"))Remove.Add(Triangle);
            else if(Slot==TEXT("TorsoLining"))Lining.Add(Triangle);
        }
        const int32 OuterCount=Remove.Num();
        // Weld only for component classification; never alter the source mesh.
        TMap<FIntVector,TArray<int32>> AtPosition;
        for(int32 I=0;I<Lining.Num();++I)
            for(FVertexID Vertex:Description->GetTriangleVertices(Lining[I]))
            {
                const FVector3f P=Positions[Vertex];
                AtPosition.FindOrAdd(FIntVector(FMath::RoundToInt(P.X*1000.f),FMath::RoundToInt(P.Y*1000.f),FMath::RoundToInt(P.Z*1000.f))).Add(I);
            }
        TBitArray<> Visited(false,Lining.Num());
        for(int32 Seed=0;Seed<Lining.Num();++Seed)
        {
            if(Visited[Seed])continue;
            TArray<int32> Component;Component.Add(Seed);Visited[Seed]=true;
            FBox Bounds(ForceInit);
            for(int32 Cursor=0;Cursor<Component.Num();++Cursor)
                for(FVertexID Vertex:Description->GetTriangleVertices(Lining[Component[Cursor]]))
                {
                    const FVector3f P=Positions[Vertex];Bounds+=FVector(P);
                    const FIntVector Key(FMath::RoundToInt(P.X*1000.f),FMath::RoundToInt(P.Y*1000.f),FMath::RoundToInt(P.Z*1000.f));
                    for(int32 Neighbor:AtPosition.FindChecked(Key))
                        if(!Visited[Neighbor]){Visited[Neighbor]=true;Component.Add(Neighbor);}
                }
            const bool Hood=Bounds.Min.X>-10.5&&Bounds.Max.X<10.5&&Bounds.Min.Y<-12.&&Bounds.Max.Y<-7.
                &&Bounds.Min.Z>121.&&Bounds.Max.Z<144.5;
            if(Hood)for(int32 I:Component)Remove.Add(Lining[I]);
        }
        if(Remove.IsEmpty())return 22;
        const int32 BeforeCount=Description->Triangles().Num();
        TSet<FPolygonID> RemovePolygons;
        for(FTriangleID Triangle:Remove)RemovePolygons.Add(Description->GetTrianglePolygon(Triangle));
        Description->DeletePolygons(RemovePolygons.Array());
        FElementIDRemappings Remap;Description->Compact(Remap);
        // Section indices change when the hood group disappears; material names
        // in the mesh description now provide the authoritative slot mapping.
        Mesh->GetLODInfo(Lod)->LODMaterialMap.Reset();
        USkeletalMesh::FCommitMeshDescriptionParams Commit;Commit.bForceUpdate=true;
        if(!Mesh->CommitMeshDescription(Lod,Commit))return 23;
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("lod"),Lod);
        Row->SetNumberField(TEXT("triangles_before"),BeforeCount);Row->SetNumberField(TEXT("outer_hood_removed"),OuterCount);
        Row->SetNumberField(TEXT("inner_hood_removed"),Remove.Num()-OuterCount);Row->SetNumberField(TEXT("triangles_after"),Description->Triangles().Num());
        LodReports.Add(MakeShared<FJsonValueObject>(Row));
    }
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->Build();
    FAssetCompilingManager::Get().FinishAllCompilation();
    {
    // The custom robe binding refines cloth mapping immediately after the base
    // bind. Defer its nested PostEditChange until section user data is committed.
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    for(const auto& Binding:Bindings)
    {
        auto& Model=Mesh->GetImportedModel()->LODModels[Binding.Lod];int32 Index=INDEX_NONE;
        for(int32 I=0;I<Model.Sections.Num();++I)
            if(Mesh->GetMaterials()[Model.Sections[I].MaterialIndex].MaterialSlotName==Binding.Slot){Index=I;break;}
        if(Index==INDEX_NONE||!Binding.Cloth->BindToSkeletalMesh(Mesh,Binding.Lod,Index,Binding.ClothLod))return 24;
        auto& Section=Model.Sections[Index];auto& User=Model.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.ClothingData=Section.ClothingData;User.CorrespondClothAssetIndex=Section.CorrespondClothAssetIndex;
    }
    for(auto& Model:Mesh->GetImportedModel()->LODModels)
        for(auto& Section:Model.Sections)
        {
            const bool Proxy=Mesh->GetMaterials()[Section.MaterialIndex].MaterialSlotName==TEXT("RobeSimulationProxy");
            Section.bDisabled=Proxy;
            Model.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex).bDisabled=Proxy;
        }
    Mesh->InvalidateDeriveDataCacheGUID();
    }
    FAssetCompilingManager::Get().FinishAllCompilation();Mesh->MarkPackageDirty();
    FSavePackageArgs Save;Save.TopLevelFlags=RF_Public|RF_Standalone;Save.SaveFlags=SAVE_NoError;
    const FString Filename=FPaths::ProjectContentDir()/TEXT("Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe.uasset");
    if(!UPackage::SavePackage(Mesh->GetOutermost(),Mesh,*Filename,Save))return 25;
    auto Report=MakeShared<FJsonObject>();Report->SetStringField(TEXT("asset"),Mesh->GetPathName());
    Report->SetArrayField(TEXT("lods"),LodReports);Report->SetNumberField(TEXT("cloth_bindings_restored"),Bindings.Num());
    Report->SetNumberField(TEXT("cloth_assets_retained"),Mesh->GetMeshClothingAssets().Num());
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    IFileManager::Get().MakeDirectory(*OutputDirectory,true);
    FFileHelper::SaveStringToFile(Json,*(OutputDirectory/TEXT("back_repair_saved.json")));
    UE_LOG(LogTemp,Display,TEXT("NUN_BACK_HOOD_REMOVED %s"),*Json);
    return 0;
}
int32 FinalizeChapelNunBackMaterials(const FString& OutputDirectory)
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe"));
    if(!Mesh)return 26;
    FAssetCompilingManager::Get().FinishAllCompilation();
    TArray<TArray<int32>> Maps;
    for(int32 Lod=0;Lod<Mesh->GetLODNum();++Lod)
    {
        auto* Description=Mesh->GetMeshDescription(Lod);if(!Description)return 27;
        FStaticMeshAttributes Attributes(*Description);
        const auto Names=Attributes.GetPolygonGroupMaterialSlotNames();
        TArray<int32> Map;
        for(FPolygonGroupID Group:Description->PolygonGroups().GetElementIDs())
        {
            const int32 Material=Mesh->GetMaterials().IndexOfByPredicate([&](const FSkeletalMaterial& M){return M.MaterialSlotName==Names[Group]||M.ImportedMaterialSlotName==Names[Group];});
            if(Material==INDEX_NONE)return 28;
            Map.Add(Material);
        }
        Maps.Add(Map);
        // These source descriptions already contain each authored LOD. Bake them
        // directly rather than reducing their newly compacted group indices again.
        auto& Reduction=Mesh->GetLODInfo(Lod)->ReductionSettings;
        Reduction.BaseLOD=Lod;Reduction.NumOfTrianglesPercentage=1.f;Reduction.NumOfVertPercentage=1.f;
        Reduction.MaxNumOfTrianglesPercentage=MAX_uint32;Reduction.MaxNumOfVertsPercentage=MAX_uint32;
        Mesh->GetLODInfo(Lod)->LODMaterialMap=Map;
    }
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->Build();FAssetCompilingManager::Get().FinishAllCompilation();
    TArray<TSharedPtr<FJsonValue>> Rows;
    {
        FScopedSkeletalMeshPostEditChange Change(Mesh);
        for(int32 Lod=0;Lod<Maps.Num();++Lod)
        {
            auto& Model=Mesh->GetImportedModel()->LODModels[Lod];
            if(Model.Sections.Num()!=Maps[Lod].Num())return 29;
            Mesh->GetLODInfo(Lod)->LODMaterialMap=Maps[Lod];
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("lod"),Lod);TArray<TSharedPtr<FJsonValue>> Slots;
            for(int32 I=0;I<Model.Sections.Num();++I)
            {
                auto& Section=Model.Sections[I];Section.MaterialIndex=Maps[Lod][I];
                const FName Slot=Mesh->GetMaterials()[Section.MaterialIndex].MaterialSlotName;
                Section.bDisabled=Slot==TEXT("RobeSimulationProxy");
                Model.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex).bDisabled=Section.bDisabled;
                Slots.Add(MakeShared<FJsonValueString>(Slot.ToString()));
            }
            Row->SetArrayField(TEXT("slots"),Slots);Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    FSavePackageArgs Save;Save.TopLevelFlags=RF_Public|RF_Standalone;Save.SaveFlags=SAVE_NoError;
    const FString Filename=FPaths::ProjectContentDir()/TEXT("Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe.uasset");
    if(!UPackage::SavePackage(Mesh->GetOutermost(),Mesh,*Filename,Save))return 30;
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("lods"),Rows);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(OutputDirectory/TEXT("back_materials_saved.json")));
    UE_LOG(LogTemp,Display,TEXT("NUN_BACK_MATERIALS_SAVED %s"),*Json);return 0;
}
#endif
