#include "StablemasterFaceCommandlet.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "EditorAssetLibrary.h"
#include "Engine/SkeletalMesh.h"
#include "MeshDescription.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Serialization/JsonSerializer.h"
#include "StaticMeshAttributes.h"

namespace
{
struct FBrush { FVector Center,Radius,Offset; };

FVector VectorField(const FJsonObject& Row,const TCHAR* Key)
{
    const auto& A=Row.GetArrayField(Key);
    return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());
}

FVector Deform(const FVector& P,const TArray<FBrush>& Brushes)
{
    if(P.Z<=144 || P.Y<=1.5)return P;
    FVector Delta=FVector::ZeroVector;
    for(const auto& Brush:Brushes)
    {
        const FVector Local=(P-Brush.Center)/Brush.Radius;
        const double R2=Local.SizeSquared();
        if(R2<10.)Delta+=Brush.Offset*FMath::Exp(-R2);
    }
    return P+Delta*FMath::SmoothStep(144.,146.,P.Z)*FMath::SmoothStep(1.5,4.,P.Y);
}
}
#endif

int32 UStablemasterFaceCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    const FString Native=TEXT("/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/SKM_MHC_Kaitlin_FaceMesh");
    const FString Target=TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/StablemasterR2/SK_Stablemaster_Face");
    const FString SourceDir=FPaths::ProjectDir()/TEXT("SourceAssets/HillsVillageStable/StablemasterR2");
    FString Json;TSharedPtr<FJsonObject> Recipe;
    if(!FFileHelper::LoadFileToString(Json,*(SourceDir/TEXT("sculpt.json"))) ||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Recipe) || !Recipe)return 1;
    TArray<FBrush> Brushes;
    for(const auto& Value:Recipe->GetArrayField(TEXT("brushes")))
    {
        const auto& Row=*Value->AsObject();
        Brushes.Add({VectorField(Row,TEXT("center")),VectorField(Row,TEXT("radius")),VectorField(Row,TEXT("offset"))});
    }
    auto* Donor=Cast<USkeletalMesh>(UEditorAssetLibrary::LoadAsset(Native));
    if(!Donor || !Donor->GetImportedModel() || Brushes.IsEmpty())return 2;
    auto* Head=Cast<USkeletalMesh>(UEditorAssetLibrary::DoesAssetExist(Target)?
        UEditorAssetLibrary::LoadAsset(Target):UEditorAssetLibrary::DuplicateAsset(Native,Target));
    if(!Head || Head==Donor)return 3;
    FAssetCompilingManager::Get().FinishAllCompilation();
    Head->Modify();
    for(int32 Lod=0;Lod<Donor->GetLODNum();++Lod)
    {
        FMeshDescription Copy;
        if(auto* Source=Donor->GetMeshDescription(Lod))Copy=*Source;
        else Donor->GetImportedModel()->LODModels[Lod].GetMeshDescription(Donor,Lod,Copy);
        if(Copy.Vertices().Num()==0)return 4;
        FStaticMeshAttributes Attributes(Copy);
        auto Pos=Attributes.GetVertexPositions();
        auto Normals=Attributes.GetVertexInstanceNormals();
        auto Tangents=Attributes.GetVertexInstanceTangents();
        // Keep the eyeballs and teeth rigid. Eyelids and lashes follow the same
        // smooth field as skin; UV seams retain their independent tangent frames.
        TSet<FVertexID> Rigid;
        for(FPolygonGroupID G:Copy.PolygonGroups().GetElementIDs())
        {
            const FString Slot=Attributes.GetPolygonGroupMaterialSlotNames()[G].ToString();
            if(!Slot.StartsWith(TEXT("eyeLeft"),ESearchCase::IgnoreCase) &&
               !Slot.StartsWith(TEXT("eyeRight"),ESearchCase::IgnoreCase) &&
               !Slot.StartsWith(TEXT("teeth"),ESearchCase::IgnoreCase))continue;
            for(FPolygonID Poly:Copy.GetPolygonGroupPolygons(G))
                for(FVertexInstanceID VI:Copy.GetPolygonVertexInstances(Poly))Rigid.Add(Copy.GetVertexInstanceVertex(VI));
        }
        for(FVertexID V:Copy.Vertices().GetElementIDs())
        {
            if(Rigid.Contains(V))continue;
            const FVector P(Pos[V]),Q=Deform(P,Brushes);
            if(P.Equals(Q,1.e-6))continue;
            for(FVertexInstanceID VI:Copy.GetVertexVertexInstanceIDs(V))
            {
                const FVector N(Normals[VI]),T(Tangents[VI]),B=FVector::CrossProduct(N,T);
                if(B.IsNearlyZero())continue;
                constexpr double H=.01;
                const FVector DT=(Deform(P+H*T,Brushes)-Deform(P-H*T,Brushes)).GetSafeNormal();
                const FVector DB=(Deform(P+H*B,Brushes)-Deform(P-H*B,Brushes)).GetSafeNormal();
                Normals[VI]=FVector3f(FVector::CrossProduct(DT,DB).GetSafeNormal());
                Tangents[VI]=FVector3f(DT);
            }
            Pos[V]=FVector3f(Q);
        }
        Head->CreateMeshDescription(Lod,MoveTemp(Copy));
        USkeletalMesh::FCommitMeshDescriptionParams Commit;Commit.bForceUpdate=true;
        if(!Head->CommitMeshDescription(Lod,Commit))return 5;
    }
    Head->InvalidateDeriveDataCacheGUID();Head->Build();
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!UEditorAssetLibrary::SaveLoadedAsset(Head,false))return 6;
    UE_LOG(LogTemp,Display,TEXT("Saved stablemaster face at %s with %d native LODs"),*Target,Head->GetLODNum());
    return 0;
#else
    return 1;
#endif
}
