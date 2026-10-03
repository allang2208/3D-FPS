#include "M07InteractingClothingAsset.h"
#if WITH_EDITOR
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Utils/ClothingMeshUtils.h"
#include <queue>
#include <vector>
#include <functional>

namespace
{
constexpr int32 M07GillCount = 6;

int32 GillPanelFromRenderColor(const FColor& Color)
{
    const int32 Bits = (Color.R > 127 ? 1 : 0) | (Color.G > 127 ? 2 : 0) | (Color.B > 127 ? 4 : 0);
    switch (Bits)
    {
        case 1: return 0; case 2: return 1; case 4: return 2;
        case 3: return 3; case 5: return 4; case 6: return 5;
        default: return INDEX_NONE;
    }
}

int32 GillPanelFromBone(FName BoneName)
{
    const FString Name = BoneName.ToString();
    if (!Name.StartsWith(TEXT("gill_"), ESearchCase::IgnoreCase) || Name.Len() < 8 || Name[7] != TCHAR('_'))
        return INDEX_NONE;
    int32 Number = 0;
    if (!LexTryParseString(Number, *Name.Mid(5, 2)) || Number < 1 || Number > M07GillCount)
        return INDEX_NONE;
    return Number - 1;
}

int32 GillPanelFromVertex(const FClothPhysicalMeshData& Physical, int32 Vertex)
{
    if (!Physical.VertexColors.IsValidIndex(Vertex)) return INDEX_NONE;
    const int32 Number = Physical.VertexColors[Vertex].B;
    return Number >= 1 && Number <= M07GillCount ? Number - 1 : INDEX_NONE;
}

FVector ReconstructGillPoint(const FVector4f& Bary, const FVector* Positions, const FVector* Normals)
{
    return Bary.X * (Positions[0] - Bary.W * Normals[0]) +
        Bary.Y * (Positions[1] - Bary.W * Normals[1]) +
        Bary.Z * (Positions[2] - Bary.W * Normals[2]);
}

bool HasStableGillFit(const FVector& Target, const FVector* Positions, const FVector* Normals,
    const FVector4f& Bary, bool bPosition, bool bLocalRepair = false)
{
    for (int32 Axis = 0; Axis < 4; ++Axis)
        if (!FMath::IsFinite(Bary[Axis])) return false;
    const float Limit = bLocalRepair ? (bPosition ? 1.015f : 4.f) : (bPosition ? 1.25f : 8.f);
    if (FMath::Max3(FMath::Abs(Bary.X), FMath::Abs(Bary.Y), FMath::Abs(Bary.Z)) > Limit ||
        FMath::Abs(Bary.W) > (bLocalRepair ? (bPosition ? 3.f : 4.5f) : 30.f) ||
        (bPosition && FMath::Min3(Bary.X, Bary.Y, Bary.Z) < (bLocalRepair ? -.015f : -.25f))) return false;
    if (bLocalRepair && (Normals[0].Dot(Normals[1]) < .15 || Normals[0].Dot(Normals[2]) < .15 || Normals[1].Dot(Normals[2]) < .15)) return false;
    return FVector::DistSquared(ReconstructGillPoint(Bary, Positions, Normals), Target) < .0004;
}

// Invert the shader's interpolated-normal prism, retaining the authored rest
// position. An unstable root is rejected rather than clamping the barycentrics.
bool FitGillPoint(const FVector& Target, const FVector* Positions, const FVector* Normals,
    FVector4f& Result, bool bPosition, bool bLocalRepair = false)
{
    const FVector Closest = FMath::ClosestPointOnTriangleToPoint(Target, Positions[0], Positions[1], Positions[2]);
    const FVector Bary = FMath::ComputeBaryCentric2D(Closest, Positions[0], Positions[1], Positions[2]);
    double U = Bary.Y, V = Bary.Z;
    const FVector InitialNormal = (1. - U - V) * Normals[0] + U * Normals[1] + V * Normals[2];
    double Height = -(Target - Closest).Dot(InitialNormal) / FMath::Max(1.e-8, InitialNormal.SizeSquared());
    for (int32 Iteration = 0; Iteration < 16; ++Iteration)
    {
        const FVector Normal = Normals[0] + U * (Normals[1] - Normals[0]) + V * (Normals[2] - Normals[0]);
        const FVector Current = Positions[0] + U * (Positions[1] - Positions[0]) +
            V * (Positions[2] - Positions[0]) - Height * Normal;
        const FVector Error = Target - Current;
        if (Error.SizeSquared() < 1.e-8) break;
        const FVector DU = Positions[1] - Positions[0] - Height * (Normals[1] - Normals[0]);
        const FVector DV = Positions[2] - Positions[0] - Height * (Normals[2] - Normals[0]);
        const FVector DH = -Normal;
        const double Determinant = DU.Dot(DV.Cross(DH));
        if (FMath::Abs(Determinant) < 1.e-9) return false;
        U += Error.Dot(DV.Cross(DH)) / Determinant;
        V += DU.Dot(Error.Cross(DH)) / Determinant;
        Height += DU.Dot(DV.Cross(Error)) / Determinant;
        if (!FMath::IsFinite(U) || !FMath::IsFinite(V) || !FMath::IsFinite(Height) || FMath::Abs(Height) > 30.)
            return false;
    }
    Result = FVector4f(1. - U - V, U, V, Height);
    return HasStableGillFit(Target, Positions, Normals, Result, bPosition, bLocalRepair);
}

void SmoothGillCapture(TArray<FMeshToMeshVertData>& Mapping, const TArray<FVector3f>& Positions,
    const TArray<uint32>& Indices, const TArray<int32>& Panels)
{
    // Weld UV duplicates within each anatomical leaf before making a 5 cm
    // surface transition around shoulder roots and rejected prism regions.
    TArray<TMap<FIntVector, int32>> WeldMaps; WeldMaps.SetNum(M07GillCount);
    TArray<int32> NodeForVertex; NodeForVertex.SetNum(Positions.Num());
    TArray<FVector3f> Nodes;
    TArray<uint16> Skin;
    for (int32 Vertex = 0; Vertex < Positions.Num(); ++Vertex)
    {
        const auto& P = Positions[Vertex];
        const FIntVector Key(FMath::RoundToInt(P.X*1000),FMath::RoundToInt(P.Y*1000),FMath::RoundToInt(P.Z*1000));
        auto& Map = WeldMaps[Panels[Vertex]];
        int32* Existing = Map.Find(Key);
        const int32 Node = Existing ? *Existing : Nodes.Num();
        if (!Existing) { Map.Add(Key,Node); Nodes.Add(P); Skin.Add(0); }
        NodeForVertex[Vertex] = Node;
        Skin[Node] = FMath::Max(Skin[Node],Mapping[Vertex].SourceMeshVertIndices[3]);
    }
    TArray<TArray<TPair<int32,float>>> Edges; Edges.SetNum(Nodes.Num());
    for (int32 Triangle = 0; Triangle < Indices.Num()/3; ++Triangle)
        for (int32 Corner = 0; Corner < 3; ++Corner)
        {
            const int32 A = Indices[Triangle*3+Corner], B = Indices[Triangle*3+(Corner+1)%3];
            if (Panels[A] != Panels[B]) continue;
            const int32 U=NodeForVertex[A],V=NodeForVertex[B];
            if (U==V) continue;
            const float Length=(Nodes[U]-Nodes[V]).Size();
            Edges[U].Emplace(V,Length); Edges[V].Emplace(U,Length);
        }
    using Step = std::pair<float,int32>;
    std::priority_queue<Step,std::vector<Step>,std::greater<Step>> Queue;
    TArray<float> Distances; Distances.Init(TNumericLimits<float>::Max(),Nodes.Num());
    for (int32 Node=0;Node<Nodes.Num();++Node)
        if (Skin[Node]==0xffff) { Distances[Node]=0; Queue.emplace(0.f,Node); }
    while (!Queue.empty())
    {
        const auto Current=Queue.top(); Queue.pop();
        if (Current.first!=Distances[Current.second] || Current.first>=5.f) continue;
        for (const auto& Edge:Edges[Current.second])
        {
            const float Next=Current.first+Edge.Value;
            if (Next<5.f && Next<Distances[Edge.Key])
            { Distances[Edge.Key]=Next; Queue.emplace(Next,Edge.Key); }
        }
    }
    int32 Blended=0;
    for (int32 Vertex=0;Vertex<Mapping.Num();++Vertex)
    {
        const int32 Node=NodeForVertex[Vertex];
        const float T=FMath::Clamp(Distances[Node]/5.f,0.f,1.f);
        const float Shoulder=1.f-T*T*(3.f-2.f*T);
        const uint16 Flag=static_cast<uint16>(FMath::RoundToInt(FMath::Max(Skin[Node]/65535.f,Shoulder)*65535.f));
        Mapping[Vertex].SourceMeshVertIndices[3]=Flag;
        Blended+=Flag>0 && Flag<0xffff;
    }
    UE_LOG(LogTemp,Display,TEXT("M07_V09_CAPTURE_TRANSITION blended=%d welded_nodes=%d fade_cm=5"),Blended,Nodes.Num());
}

// Labels belong to anatomical islands. Non-fixed vertices decide a triangle's
// island first; shared fixed roots only vote when the entire triangle is fixed.
int32 GillPanelFromTriangle(const FClothPhysicalMeshData& Physical, const FPointWeightMap* MaxDistances,
    int32 Triangle)
{
    int32 MovingVotes[M07GillCount] = {}, AllVotes[M07GillCount] = {};
    int32 MovingCount = 0;
    for (int32 Corner = 0; Corner < 3; ++Corner)
    {
        const int32 Vertex = Physical.Indices[Triangle * 3 + Corner];
        const int32 Panel = GillPanelFromVertex(Physical, Vertex);
        if (Panel == INDEX_NONE) continue;
        ++AllVotes[Panel];
        if (!MaxDistances || (*MaxDistances)[Vertex] > 0.f)
        {
            ++MovingVotes[Panel];
            ++MovingCount;
        }
    }
    const int32* Votes = MovingCount ? MovingVotes : AllVotes;
    int32 Panel = INDEX_NONE, Best = 0;
    for (int32 Candidate = 0; Candidate < M07GillCount; ++Candidate)
        if (Votes[Candidate] > Best ||
            (Votes[Candidate] == Best && Best > 0 && Panel != INDEX_NONE && AllVotes[Candidate] > AllVotes[Panel]))
        {
            Panel = Candidate;
            Best = Votes[Candidate];
        }
    return Panel;
}

bool GenerateFilteredGillCapture(USkeletalMesh* Mesh, FSkeletalMeshLODModel& Lod, FSkelMeshSection& Section,
    const FClothLODDataCommon& ClothLod, TArray<FMeshToMeshVertData>& OutMapping)
{
    const auto& Physical = ClothLod.PhysicalMeshData;
    const bool bLocalRepair = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV11") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18");
    const auto* MaxDistances = Physical.FindWeightMap(EWeightMapTargetCommon::MaxDistance);
    TArray<ClothingMeshUtils::FMeshToMeshFilterSet> Filters;
    Filters.SetNum(M07GillCount);
    TArray<TArray<int32>> PanelTriangles;
    PanelTriangles.SetNum(M07GillCount);
    for (int32 Triangle = 0; Triangle < Physical.Indices.Num() / 3; ++Triangle)
    {
        const int32 A = Physical.Indices[Triangle * 3];
        const int32 B = Physical.Indices[Triangle * 3 + 1];
        const int32 C = Physical.Indices[Triangle * 3 + 2];
        if ((Physical.Vertices[B] - Physical.Vertices[A]).Cross(Physical.Vertices[C] - Physical.Vertices[A]).SizeSquared() < 1.e-8f)
            continue;
        const int32 Panel = GillPanelFromTriangle(Physical, MaxDistances, Triangle);
        if (Panel != INDEX_NONE)
        {
            // The utility's filter contract takes triangle IDs, not offsets
            // into Physical.Indices. Its candidate search multiplies by three.
            Filters[Panel].SourceTriangles.Add(Triangle);
            PanelTriangles[Panel].Add(Triangle);
        }
    }
    for (int32 Panel = 0; Panel < M07GillCount; ++Panel)
        if (PanelTriangles[Panel].IsEmpty())
        {
            UE_LOG(LogTemp, Error, TEXT("M07_CONTINUOUS_CAPTURE panel=%d has no labelled nondegenerate source triangles"), Panel + 1);
            return false;
        }

    TArray<FVector3f> Positions, Normals, Tangents;
    Positions.Reserve(Section.SoftVertices.Num());
    Normals.Reserve(Section.SoftVertices.Num());
    Tangents.Reserve(Section.SoftVertices.Num());
    TArray<int32> TargetPanels;
    TargetPanels.SetNum(Section.SoftVertices.Num());
    TArray<uint8> SkinOnly;
    SkinOnly.Init(0, Section.SoftVertices.Num());
    TArray<int32> BonePanels;
    BonePanels.Init(INDEX_NONE, Section.BoneMap.Num());
    const FReferenceSkeleton& Skeleton = Mesh->GetRefSkeleton();
    for (int32 Bone = 0; Bone < Section.BoneMap.Num(); ++Bone)
        if (Skeleton.IsValidIndex(Section.BoneMap[Bone]))
            BonePanels[Bone] = GillPanelFromBone(Skeleton.GetBoneName(Section.BoneMap[Bone]));

    int32 ShoulderSkinCount = 0;
    int32 TaggedVertexCount = 0;
    for (int32 Vertex = 0; Vertex < Section.SoftVertices.Num(); ++Vertex)
    {
        const FSoftSkinVertex& Render = Section.SoftVertices[Vertex];
        Positions.Add(Render.Position);
        Normals.Add(Render.TangentZ);
        Tangents.Add(Render.TangentX);
        uint32 PanelWeights[M07GillCount] = {};
        for (int32 Influence = 0; Influence < UE_ARRAY_COUNT(Render.InfluenceBones); ++Influence)
        {
            const int32 Bone = Render.InfluenceBones[Influence];
            if (Render.InfluenceWeights[Influence] > 0 && BonePanels.IsValidIndex(Bone) && BonePanels[Bone] != INDEX_NONE)
                PanelWeights[BonePanels[Bone]] += Render.InfluenceWeights[Influence];
        }
        int32 Panel = INDEX_NONE;
        uint32 BestWeight = 0;
        for (int32 Candidate = 0; Candidate < M07GillCount; ++Candidate)
            if (PanelWeights[Candidate] > BestWeight)
            {
                BestWeight = PanelWeights[Candidate];
                Panel = Candidate;
            }
        const int32 TaggedPanel=bLocalRepair ? GillPanelFromRenderColor(Render.Color) : INDEX_NONE;
        if (TaggedPanel!=INDEX_NONE)
        {
            ++TaggedVertexCount;
            if (Panel==INDEX_NONE) { SkinOnly[Vertex]=1; ++ShoulderSkinCount; }
            Panel=TaggedPanel;
        }
        if (Panel == INDEX_NONE)
        {
            // Shoulder/back anchor vertices carry only the original body
            // weights. Give the generator a nearby island, then retain pure
            // skinning; never let these shared roots join two cloth panels.
            SkinOnly[Vertex] = 1;
            ++ShoulderSkinCount;
            double BestSquared = TNumericLimits<double>::Max();
            for (int32 Source = 0; Source < Physical.Vertices.Num(); ++Source)
            {
                const int32 Candidate = GillPanelFromVertex(Physical, Source);
                if (Candidate == INDEX_NONE) continue;
                const double Squared = FVector::DistSquared(FVector(Render.Position), FVector(Physical.Vertices[Source]));
                if (Squared < BestSquared)
                {
                    BestSquared = Squared;
                    Panel = Candidate;
                }
            }
        }
        if (Panel == INDEX_NONE) return false;
        TargetPanels[Vertex] = Panel;
        Filters[Panel].TargetVertices.Add(Vertex);
    }
    if (bLocalRepair && TaggedVertexCount!=Section.SoftVertices.Num())
    {
        UE_LOG(LogTemp,Error,TEXT("M07_V09_CAPTURE requires explicit original-leaf identities; tagged=%d expected=%d"),TaggedVertexCount,Section.SoftVertices.Num());
        return false;
    }
    if (bLocalRepair) UE_LOG(LogTemp,Display,TEXT("M07_V09_CAPTURE_LEAF_IDENTITIES tagged=%d"),TaggedVertexCount);

    TArray<uint32> Indices;
    Indices.Reserve(Section.NumTriangles * 3);
    for (uint32 Index = 0; Index < Section.NumTriangles * 3u; ++Index)
    {
        const int32 SectionIndex = Section.BaseIndex + Index;
        if (!Lod.IndexBuffer.IsValidIndex(SectionIndex)) return false;
        const int32 Vertex = int32(Lod.IndexBuffer[SectionIndex]) - int32(Section.BaseVertexIndex);
        if (!Positions.IsValidIndex(Vertex)) return false;
        Indices.Add(Vertex);
    }
    const ClothingMeshUtils::ClothMeshDesc TargetMesh(Positions, Normals, Tangents, Indices);
    const ClothingMeshUtils::ClothMeshDesc SourceMesh(Physical.Vertices, Physical.Indices);
    // One record per display vertex keeps the fixed/skin flag unambiguous.
    // All three physical indices remain in the factory's whole-mesh numbering.
    ClothingMeshUtils::GenerateMeshToMeshVertData(OutMapping, TargetMesh, SourceMesh, MaxDistances,
        ClothLod.bSmoothTransition, false, ClothLod.SkinningKernelRadius, Filters);
    if (OutMapping.Num() != Section.SoftVertices.Num()) return false;

    const auto& SourceNormals = SourceMesh.GetNormals();
    int32 RepairedCount = 0, FallbackCount = 0;
    int32 PositionRejected = 0, NormalRejected = 0, TangentRejected = 0;
    for (int32 Vertex = 0; Vertex < OutMapping.Num(); ++Vertex)
    {
        FMeshToMeshVertData& Mapping = OutMapping[Vertex];
        if (SkinOnly[Vertex])
        {
            Mapping.SourceMeshVertIndices[3] = 0xffff;
            continue;
        }
        if (Mapping.SourceMeshVertIndices[3] == 0xffff) continue;
        const FVector Target(Positions[Vertex]);
        const FVector NormalTarget = Target + FVector(Normals[Vertex]);
        const FVector TangentTarget = Target + FVector(Tangents[Vertex]);
        FVector P[3], N[3];
        bool bValid = true;
        for (int32 Corner = 0; Corner < 3; ++Corner)
        {
            const int32 Source = Mapping.SourceMeshVertIndices[Corner];
            if (!Physical.Vertices.IsValidIndex(Source)) { bValid = false; break; }
            P[Corner] = FVector(Physical.Vertices[Source]);
            N[Corner] = FVector(SourceNormals[Source]);
        }
        if (bValid && HasStableGillFit(Target, P, N, Mapping.PositionBaryCoordsAndDist, true, bLocalRepair) &&
            HasStableGillFit(NormalTarget, P, N, Mapping.NormalBaryCoordsAndDist, false, bLocalRepair) &&
            HasStableGillFit(TangentTarget, P, N, Mapping.TangentBaryCoordsAndDist, false, bLocalRepair)) continue;

        TArray<TPair<double, int32>> Nearest;
        Nearest.Reserve(33);
        for (int32 Triangle : PanelTriangles[TargetPanels[Vertex]])
        {
            const int32 Base = Triangle * 3;
            const FVector A(Physical.Vertices[Physical.Indices[Base]]);
            const FVector B(Physical.Vertices[Physical.Indices[Base + 1]]);
            const FVector C(Physical.Vertices[Physical.Indices[Base + 2]]);
            const double Squared = FVector::DistSquared(Target, FMath::ClosestPointOnTriangleToPoint(Target, A, B, C));
            if (Nearest.Num() == 32 && Squared >= Nearest.Last().Key) continue;
            Nearest.Emplace(Squared, Triangle);
            for (int32 Rank = Nearest.Num() - 1; Rank > 0 && Nearest[Rank].Key < Nearest[Rank - 1].Key; --Rank)
                Swap(Nearest[Rank], Nearest[Rank - 1]);
            if (Nearest.Num() > 32) Nearest.Pop(EAllowShrinking::No);
        }
        bool bFitted = false;
        for (const auto& Candidate : Nearest)
        {
            const int32 Base = Candidate.Value * 3;
            for (int32 Corner = 0; Corner < 3; ++Corner)
            {
                const int32 Source = Physical.Indices[Base + Corner];
                P[Corner] = FVector(Physical.Vertices[Source]);
                N[Corner] = FVector(SourceNormals[Source]);
            }
            FMeshToMeshVertData Replacement = Mapping;
            const bool PositionFit = FitGillPoint(Target, P, N, Replacement.PositionBaryCoordsAndDist, true, bLocalRepair);
            const bool NormalFit = PositionFit && FitGillPoint(NormalTarget, P, N, Replacement.NormalBaryCoordsAndDist, false, bLocalRepair);
            const bool TangentFit = NormalFit && FitGillPoint(TangentTarget, P, N, Replacement.TangentBaryCoordsAndDist, false, bLocalRepair);
            if (!TangentFit)
            {
                PositionRejected += !PositionFit;
                NormalRejected += PositionFit && !NormalFit;
                TangentRejected += NormalFit && !TangentFit;
                if (FallbackCount == 0 && Candidate.Value == Nearest[0].Value)
                    UE_LOG(LogTemp, Display, TEXT("M07_CAPTURE_FIRST_REJECT vertex=%d panel=%d closest_cm=%.6f stage=%s target=%s normal_target=%s tangent_target=%s P=[%s;%s;%s] N=[%s;%s;%s] baryP=%s baryN=%s baryT=%s"),
                        Vertex, TargetPanels[Vertex] + 1, FMath::Sqrt(Candidate.Key),
                        !PositionFit ? TEXT("position") : !NormalFit ? TEXT("normal") : TEXT("tangent"),
                        *Target.ToString(), *NormalTarget.ToString(), *TangentTarget.ToString(),
                        *P[0].ToString(), *P[1].ToString(), *P[2].ToString(),
                        *N[0].ToString(), *N[1].ToString(), *N[2].ToString(),
                        *Replacement.PositionBaryCoordsAndDist.ToString(), *Replacement.NormalBaryCoordsAndDist.ToString(),
                        *Replacement.TangentBaryCoordsAndDist.ToString());
                continue;
            }
            for (int32 Corner = 0; Corner < 3; ++Corner)
                Replacement.SourceMeshVertIndices[Corner] = Physical.Indices[Base + Corner];
            // The fourth index is the skin/cloth blend flag, not a particle.
            // Preserve it when changing the three physical triangle indices.
            Mapping = Replacement;
            bFitted = true;
            ++RepairedCount;
            break;
        }
        if (!bFitted)
        {
            Mapping.SourceMeshVertIndices[3] = 0xffff;
            SkinOnly[Vertex] = 1;
            ++FallbackCount;
        }
    }
    if (bLocalRepair)
    {
        // The fourth value is a UNORM skin contribution and belongs to the
        // FINAL source triangle, including all repaired captures above.
        ClothingMeshUtils::ComputeVertexContributions(OutMapping,MaxDistances,true,false);
        for (int32 Vertex=0;Vertex<OutMapping.Num();++Vertex)
            if (SkinOnly[Vertex]) OutMapping[Vertex].SourceMeshVertIndices[3]=0xffff;
        SmoothGillCapture(OutMapping,Positions,Indices,TargetPanels);
    }
    UE_LOG(LogTemp, Display, TEXT("M07_CONTINUOUS_CAPTURE mesh=%s triangles=[%d,%d,%d,%d,%d,%d] vertices=%d shoulder_skin=%d prism_refitted=%d local_skin_fallback=%d"),
        *Mesh->GetName(), PanelTriangles[0].Num(), PanelTriangles[1].Num(), PanelTriangles[2].Num(),
        PanelTriangles[3].Num(), PanelTriangles[4].Num(), PanelTriangles[5].Num(), OutMapping.Num(),
        ShoulderSkinCount, RepairedCount, FallbackCount);
    UE_LOG(LogTemp, Display, TEXT("M07_CAPTURE_REJECTIONS position=%d normal=%d tangent=%d"), PositionRejected, NormalRejected, TangentRejected);
    return true;
}

void RestoreLodMap(TArray<int32>& LodMap, const TArray<int32>& PreviousMap, int32 MeshLod, int32 AssetLod, bool bBound)
{
    LodMap = PreviousMap;
    if (!bBound) return;
    while (LodMap.Num() <= MeshLod) LodMap.Add(INDEX_NONE);
    LodMap[MeshLod] = AssetLod;
}
}

bool UM07InteractingClothingAsset::BindToSkeletalMesh(USkeletalMesh* Mesh, int32 MeshLod, int32 SectionIndex, int32 AssetLod)
{
    if (!Mesh || Mesh != GetOuter() || !LodData.IsValidIndex(AssetLod) || !Mesh->GetImportedModel() ||
        !Mesh->GetImportedModel()->LODModels.IsValidIndex(MeshLod)) return false;
    auto& Lod = Mesh->GetImportedModel()->LODModels[MeshLod];
    if (!Lod.Sections.IsValidIndex(SectionIndex)) return false;
    const int32 Material = Lod.Sections[SectionIndex].MaterialIndex;
    if (!Mesh->GetMaterials().IsValidIndex(Material)) return false;
    const auto& Slot = Mesh->GetMaterials()[Material];
    if (Slot.ImportedMaterialSlotName == FName(TEXT("M07_Gills")) || Slot.MaterialSlotName == FName(TEXT("M07_Gills")))
    {
        // The complete six-island physical mesh owns the one reference frame.
        // Never replace it with a temporary panel during a bind/DDC rebuild.
        FScopedSkeletalMeshPostEditChange Change(Mesh);
        auto& ClothLod = LodData[AssetLod];
        ClothLod.bUseMultipleInfluences = false;
        if (Mesh->GetOutermost()->GetName()==TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09") ||
            Mesh->GetOutermost()->GetName()==TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV11") ||
            Mesh->GetOutermost()->GetName()==TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12") ||
            Mesh->GetOutermost()->GetName()==TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") ||
            Mesh->GetOutermost()->GetName()==TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18")) ClothLod.bSmoothTransition=true;
        const auto PreviousMap = LodMap;
        LodMap.Reset();
        const bool bBound = UClothingAssetCommon::BindToSkeletalMesh(Mesh, MeshLod, SectionIndex, AssetLod);
        RestoreLodMap(LodMap, PreviousMap, MeshLod, AssetLod, bBound);
        if (!bBound) return false;
        auto& BoundLod = Mesh->GetImportedModel()->LODModels[MeshLod];
        auto& Section = BoundLod.Sections[SectionIndex];
        TArray<FMeshToMeshVertData> FilteredMapping;
        if (!GenerateFilteredGillCapture(Mesh, BoundLod, Section, ClothLod, FilteredMapping))
        {
            UClothingAssetCommon::UnbindFromSkeletalMesh(Mesh, MeshLod, SectionIndex);
            LodMap = PreviousMap;
            return false;
        }
        Section.ClothMappingDataLODs[0] = MoveTemp(FilteredMapping);
        const FName ReferenceBoneName = Mesh->GetRefSkeleton().IsValidIndex(ReferenceBoneIndex)
            ? Mesh->GetRefSkeleton().GetBoneName(ReferenceBoneIndex) : NAME_None;
        UE_LOG(LogTemp, Display, TEXT("M07_CONTINUOUS_BIND cloth=%s reference_bone=%s reference_index=%d mesh_lod=%d asset_lod=%d physical_vertices=%d"),
            *GetName(), *ReferenceBoneName.ToString(), ReferenceBoneIndex, MeshLod, AssetLod,
            ClothLod.PhysicalMeshData.Vertices.Num());
        return true;
    }
    int32 Panel = PanelMaterialSlots.IndexOfByKey(Slot.ImportedMaterialSlotName);
    if (Panel == INDEX_NONE) Panel = PanelMaterialSlots.IndexOfByKey(Slot.MaterialSlotName);
    if (!PanelSimulations.IsValidIndex(Panel) || !PanelVertexOffsets.IsValidIndex(Panel)) return false;

    // UE's common factory assumes one render section per cloth LOD. Capture
    // each section against its own anatomical island, then express that
    // capture in the one shared simulation's vertex numbering. The outer
    // scope keeps cache rebuilding outside the temporary physical subset.
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    auto FullPhysical = MoveTemp(LodData[AssetLod].PhysicalMeshData);
    const int32 FullReferenceBoneIndex = ReferenceBoneIndex;
    LodData[AssetLod].PhysicalMeshData = PanelSimulations[Panel];
    const auto PreviousMap = LodMap;
    LodMap.Reset();
    const bool bBound = Super::BindToSkeletalMesh(Mesh, MeshLod, SectionIndex, AssetLod);
    LodData[AssetLod].PhysicalMeshData = MoveTemp(FullPhysical);
    ReferenceBoneIndex = FullReferenceBoneIndex;
    RestoreLodMap(LodMap, PreviousMap, MeshLod, AssetLod, bBound);
    if (!bBound) return false;
    auto& Section = Mesh->GetImportedModel()->LODModels[MeshLod].Sections[SectionIndex];
    for (auto& MappingLod : Section.ClothMappingDataLODs)
        for (auto& Mapping : MappingLod)
            for (int32 Corner = 0; Corner < 3; ++Corner)
                Mapping.SourceMeshVertIndices[Corner] += PanelVertexOffsets[Panel];
    return true;
}
#endif
