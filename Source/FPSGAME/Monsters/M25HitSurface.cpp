#include "VortexCofferM25.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "UObject/Package.h"

namespace M25HitSurface
{
struct FRegion
{
    int32 Count = 0;
    FVector Points[26];
    double Support[26];
    FRegion() { for (double& Value : Support) Value = -DBL_MAX; }
    void Add(FVector P, const TArray<FVector>& Directions)
    {
        ++Count;
        for (int32 I = 0; I < Directions.Num(); ++I)
        {
            const double Dot = FVector::DotProduct(P, Directions[I]);
            if (Dot > Support[I]) { Support[I] = Dot; Points[I] = P; }
        }
    }
};
}
#endif

UPhysicsAsset* AVortexCofferM25::BuildHitSurfacePhysics(USkeletalMesh* InMesh, const FString& AssetPath)
{
#if WITH_EDITOR
    if (!InMesh || !AssetPath.StartsWith(TEXT("/Game/Monsters/VortexCofferM25/"))
        || !InMesh->GetImportedModel() || InMesh->GetImportedModel()->LODModels.IsEmpty()) return nullptr;
    const auto& Ref = InMesh->GetRefSkeleton();
    const int32 Maw = Ref.FindBoneIndex(TEXT("maw")), Socket = Ref.FindBoneIndex(TEXT("socket_maw"));
    if (Maw == INDEX_NONE || Socket == INDEX_NONE) return nullptr;
    TArray<FTransform> Frames = Ref.GetRefBonePose();
    for (int32 I = 0; I < Frames.Num(); ++I)
        if (Ref.GetParentIndex(I) >= 0) Frames[I] *= Frames[Ref.GetParentIndex(I)];
    const FVector MouthCenter = Frames[Maw].GetLocation();
    const FVector Forward = (Frames[Socket].GetLocation() - MouthCenter).GetSafeNormal();
    const FVector Side = FVector::CrossProduct(Forward, FVector::UpVector).GetSafeNormal();
    const FVector Up = FVector::CrossProduct(Side, Forward).GetSafeNormal();
    TArray<FTransform> InverseFrames;
    TArray<bool> MouthBones;
    for (int32 I = 0; I < Ref.GetNum(); ++I)
    {
        InverseFrames.Add(Frames[I].Inverse());
        MouthBones.Add(I == Maw || Ref.GetBoneName(I).ToString().StartsWith(TEXT("maw_rim_")));
    }
    TArray<FVector> Directions;
    for (int32 X = -1; X <= 1; ++X) for (int32 Y = -1; Y <= 1; ++Y) for (int32 Z = -1; Z <= 1; ++Z)
        if (X || Y || Z) Directions.Add(FVector(X,Y,Z).GetSafeNormal());

    // A bounded support cloud per bone. This traverses the original full-resolution
    // skin only during authoring; runtime collision never scans mesh vertices.
    TArray<M25HitSurface::FRegion> Regions;
    Regions.SetNum(Ref.GetNum() * 5);
    for (const auto& Section : InMesh->GetImportedModel()->LODModels[0].Sections)
        for (const auto& Vertex : Section.SoftVertices)
        {
            int32 Influence = 0;
            for (int32 J = 1; J < MAX_TOTAL_INFLUENCES; ++J)
                if (Vertex.InfluenceWeights[J] > Vertex.InfluenceWeights[Influence]) Influence = J;
            if (!Vertex.InfluenceWeights[Influence]) continue;
            const int32 Bone = Section.BoneMap[Vertex.InfluenceBones[Influence]];
            const FVector Position(Vertex.Position);
            const bool Mouth = MouthBones[Bone];
            int32 Sector = 0;
            const FVector Delta = Position - MouthCenter;
            if (!Mouth && FVector::DotProduct(Delta, Forward) > -8.f)
            {
                // Split ordinary tissue around the mouth into four convex sectors.
                // A single front-body hull would bridge and cover the weakpoint opening.
                const float X = FVector::DotProduct(Delta, Side), Z = FVector::DotProduct(Delta, Up);
                Sector = FMath::Abs(X) >= FMath::Abs(Z) ? (X >= 0 ? 1 : 2) : (Z >= 0 ? 3 : 4);
            }
            Regions[Bone * 5 + Sector].Add(InverseFrames[Bone].TransformPosition(Position), Directions);
        }

    UPackage* Package = CreatePackage(*AssetPath);
    const FName Name(*FPackageName::GetLongPackageAssetName(AssetPath));
    auto* Asset = FindObject<UPhysicsAsset>(Package, *Name.ToString());
    const bool NewAsset = !Asset;
    if (!Asset) Asset = NewObject<UPhysicsAsset>(Package, Name, RF_Public | RF_Standalone | RF_Transactional);
    Asset->Modify();
    Asset->SkeletalBodySetups.Reset();
    Asset->ConstraintSetup.Reset();
    Asset->CollisionDisableTable.Reset();
    for (int32 Bone = 0; Bone < Ref.GetNum(); ++Bone)
    {
        USkeletalBodySetup* Body = nullptr;
        for (int32 Sector = 0; Sector < 5; ++Sector)
        {
            const auto& Region = Regions[Bone * 5 + Sector];
            if (Region.Count < 4) continue;
            FKConvexElem Hull;
            const float Padding = .6f / FMath::Max(Frames[Bone].GetScale3D().GetAbsMax(), .001f);
            for (int32 D = 0; D < Directions.Num(); ++D)
                Hull.VertexData.AddUnique(Region.Points[D] + Directions[D] * Padding);
            if (Hull.VertexData.Num() < 4) continue;
            Hull.UpdateElemBox();
            if (!Body)
            {
                Body = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
                Body->BoneName = Ref.GetBoneName(Bone);
                Body->PhysicsType = PhysType_Kinematic;
                Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
                Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
                Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryOnly);
                Asset->SkeletalBodySetups.Add(Body);
            }
            Body->AggGeom.ConvexElems.Add(MoveTemp(Hull));
        }
        if (Body) { Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes(); }
    }
    Asset->UpdateBodySetupIndexMap();
    Asset->UpdateBoundsBodiesArray();
    Asset->MarkPackageDirty();
    if (NewAsset) FAssetRegistryModule::AssetCreated(Asset);
    return Asset;
#else
    return nullptr;
#endif
}
