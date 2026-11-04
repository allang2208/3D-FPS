#include "TacticalHatchetImportLibrary.h"
#include "Engine/StaticMesh.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshOperations.h"
#include "StaticMeshCompiler.h"
#endif

bool UTacticalHatchetImportLibrary::FinalizeMesh(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh)return false;
    const FString AssetPath=Mesh->GetPathName();
    if(AssetPath!=TEXT("/Game/Weapons/TacticalHatchet20261101/SM_TacticalHatchet.SM_TacticalHatchet")
        &&!AssetPath.StartsWith(TEXT("/Game/Weapons/TacticalHatchet20261101/ModulesV1/")))return false;
    FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});
    const auto* Source=Mesh->GetMeshDescription(0);if(!Source)return false;
    FMeshDescription Description=*Source;
    FStaticMeshOperations::ComputeTriangleTangentsAndNormals(Description);
    FStaticMeshOperations::ComputeTangentsAndNormals(Description,EComputeNTBsFlags::Tangents|EComputeNTBsFlags::UseMikkTSpace|EComputeNTBsFlags::IgnoreDegenerateTriangles);
    FStaticMeshAttributes Attributes(Description);
    const auto Normals=Attributes.GetVertexInstanceNormals();
    auto Tangents=Attributes.GetVertexInstanceTangents();auto Signs=Attributes.GetVertexInstanceBinormalSigns();
    int32 Corrected=0;
    for(const FVertexInstanceID V:Description.VertexInstances().GetElementIDs())
    {
        const FVector3f N=Normals[V].GetSafeNormal();if(N.ContainsNaN()||N.IsNearlyZero())return false;
        FVector3f X=Tangents[V];
        X=(X-N*FVector3f::DotProduct(X,N)).GetSafeNormal();
        if(X.ContainsNaN()||X.IsNearlyZero())
        {
            const auto Axis=FMath::Abs(N.Z)<.9f?FVector3f::UpVector:FVector3f::RightVector;
            X=FVector3f::CrossProduct(Axis,N).GetSafeNormal();++Corrected;
        }
        Tangents[V]=X;Signs[V]=Signs[V]<0.f?-1.f:1.f;
    }
    // Retain source topology, UVs, authored normals and material assignment.
    // Degenerate UV corners receive a stable tangent; never rebuild from Nanite's reduced fallback.
    Mesh->Modify();*Mesh->CreateMeshDescription(0)=MoveTemp(Description);Mesh->CommitMeshDescription(0);
    auto& Build=Mesh->GetSourceModel(0).BuildSettings;
    Build.bRecomputeNormals=false;Build.bRecomputeTangents=false;
    Build.bUseHighPrecisionTangentBasis=true;Build.bUseFullPrecisionUVs=true;
    Mesh->PostEditChange();FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});Mesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("HATCHET_TANGENTS_AUTHORED corrected_corners=%d"),Corrected);
    return true;
#else
    return false;
#endif
}
