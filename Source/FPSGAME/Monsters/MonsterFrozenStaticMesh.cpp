#include "MonsterCorpseMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "StaticMeshAttributes.h"
#include "MeshDescription.h"

bool UMonsterCorpseMeshComponent::ShouldCreateRenderState() const
{
    return !FrozenStaticMesh && Super::ShouldCreateRenderState();
}

bool UMonsterCorpseMeshComponent::TryBuildFrozenStaticMesh()
{
    // Only immutable poses with resident cooked CPU data; never flush the GPU for a corpse.
    USkeletalMesh* Source = GetSkeletalMeshAsset();
    if (FrozenStaticMesh || !Source || !IsVisible() || IsComponentTickEnabled() || IsSimulatingPhysics()
        || GetMeshDeformerInstance() || GetOverlayMaterial() || LeaderPoseComponent.IsValid()
        || !GetClothingSimulationInstances().IsEmpty() || !GetMorphTargetCurves().IsEmpty()
        || GetComponentSpaceTransforms().IsEmpty()) return false;
    TArray<TObjectPtr<UMaterialInterface>> Overlays;
    GetMaterialSlotsOverlayMaterial(Overlays);
    if (!Overlays.IsEmpty() && Overlays.ContainsByPredicate([](const auto& M){ return M != nullptr; })) return false;
    const auto* Data = Source->GetResourceForRendering();
    if (!Data || Data->LODRenderData.IsEmpty()) return false;
    // The nearest player is already outside the near-detail band. Prefer the
    // displayed LOD when possible, then the authored CPU-readable distant LOD.
    int32 Lod = GetPredictedLODLevel();
    while (Data->LODRenderData.IsValidIndex(Lod))
    {
        const auto* Info = Source->GetLODInfo(Lod);
        if (Info && Info->bAllowCPUAccess && Data->LODRenderData[Lod].GetTotalFaces()<=4500) break;
        ++Lod;
    }
    if (!Data->LODRenderData.IsValidIndex(Lod)) return false;
    const auto& Render = Data->LODRenderData[Lod];
    const auto& Buffers = Render.StaticVertexBuffers;
    const auto& Verts = Buffers.StaticMeshVertexBuffer;
    const auto* Indices = Render.MultiSizeIndexContainer.GetIndexBuffer();
    const auto* Weights = GetSkinWeightBuffer(Lod);
    if (!Indices || !Indices->GetNeedsCPUAccess() || !Weights || !Weights->GetNeedsCPUAccess()
        || !Buffers.PositionVertexBuffer.GetVertexData() || !Verts.GetTexCoordData()
        || !Verts.GetTangentData() || !Weights->GetDataVertexBuffer()->GetWeightData()
        || Render.GetNumVertices()==0 || Render.GetTotalFaces()>4500 || Render.GetTotalFaces()==0) return false;
    if (Buffers.ColorVertexBuffer.GetNumVertices() && !Buffers.ColorVertexBuffer.GetVertexData()) return false;
    TArray<FMatrix44f> Matrices;
    GetCurrentRefToLocalMatrices(Matrices,Lod);
    TArray<FVector3f> Positions;
    ComputeSkinnedPositions(this,Positions,Matrices,Render,*Weights);
    if (Positions.Num()!=Render.GetNumVertices()) return false;
    FMeshDescription Desc;
    FStaticMeshAttributes Attr(Desc);
    Attr.Register();
    auto Points=Attr.GetVertexPositions();
    auto UVs=Attr.GetVertexInstanceUVs();
    auto Normals=Attr.GetVertexInstanceNormals();
    auto Tangents=Attr.GetVertexInstanceTangents();
    auto Signs=Attr.GetVertexInstanceBinormalSigns();
    auto Colors=Attr.GetVertexInstanceColors();
    auto SlotNames=Attr.GetPolygonGroupMaterialSlotNames();
    UVs.SetNumChannels(Verts.GetNumTexCoords());
    for (const auto& P : Positions) Points[Desc.CreateVertex()]=P;
    auto* StaticMesh=NewObject<UStaticMesh>(GetOwner(), NAME_None, RF_Transient);
    const auto* Info=Source->GetLODInfo(Lod);
    for (int32 SectionIndex=0;SectionIndex<Render.RenderSections.Num();++SectionIndex)
    {
        const auto& Section=Render.RenderSections[SectionIndex];
        if (Section.bDisabled || !Section.NumTriangles || !IsMaterialSectionShown(Section.MaterialIndex,Lod)) continue;
        int32 Slot=Section.MaterialIndex;
        if (Info && Info->LODMaterialMap.IsValidIndex(SectionIndex) && Info->LODMaterialMap[SectionIndex]!=INDEX_NONE)
            Slot=Info->LODMaterialMap[SectionIndex];
        const FName Name(*FString::Printf(TEXT("Section%d"),SectionIndex));
        auto* Material=GetMaterial(Slot);
        if (!Material) return false;
        StaticMesh->GetStaticMaterials().Emplace(Material, Name);
        const auto Group=Desc.CreatePolygonGroup();
        SlotNames[Group]=Name;
        TArray<FVertexInstanceID> SectionVertices;
        SectionVertices.Reserve(Section.NumVertices);
        for (uint32 I=Section.BaseVertexIndex;I<Section.BaseVertexIndex+Section.NumVertices;++I)
        {
            const auto Instance=Desc.CreateVertexInstance(FVertexID(I));
            SectionVertices.Add(Instance);
            const auto Z=Verts.VertexTangentZ(I);
            const auto X=Verts.VertexTangentX(I);
            FVector3f Normal=FVector3f::ZeroVector,Tangent=FVector3f::ZeroVector;
            for (uint32 Influence=0;Influence<Weights->GetMaxBoneInfluences();++Influence)
            {
                const float W=Weights->GetBoneWeight(I,Influence)/65535.f;
                if (!W) continue;
                const auto Bone=Section.BoneMap[Weights->GetBoneIndex(I,Influence)];
                Normal+=FVector3f(Matrices[Bone].TransformVector(FVector3f(Z)))*W;
                Tangent+=FVector3f(Matrices[Bone].TransformVector(FVector3f(X)))*W;
            }
            Normals[Instance]=Normal.GetSafeNormal();Tangents[Instance]=Tangent.GetSafeNormal();
            Signs[Instance]=Z.W < 0 ? -1.f : 1.f;
            Colors[Instance]=Buffers.ColorVertexBuffer.GetNumVertices() ? FVector4f(FLinearColor(Buffers.ColorVertexBuffer.VertexColor(I))) : FVector4f(1,1,1,1);
            for (uint32 UV=0;UV<Verts.GetNumTexCoords();++UV) UVs.Set(Instance,UV,Verts.GetVertexUV(I,UV));
        }
        for (uint32 T=0;T<Section.NumTriangles;++T)
        {
            FVertexInstanceID Corners[3];
            for (int32 K=0;K<3;++K) Corners[K]=SectionVertices[Indices->Get(Section.BaseIndex+3*T+K)-Section.BaseVertexIndex];
            Desc.CreateTriangle(Group,MakeArrayView(Corners));
        }
    }
    if (Desc.Triangles().Num()==0) return false;
    UStaticMesh::FBuildMeshDescriptionsParams Params;
    Params.bFastBuild=true;Params.bMarkPackageDirty=false;Params.bCommitMeshDescription=false;
    if (!StaticMesh->BuildFromMeshDescriptions({&Desc}, Params)) return false;
    auto* Proxy=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
    GetOwner()->AddInstanceComponent(Proxy);
    Proxy->SetupAttachment(this);
    Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Proxy->SetCanEverAffectNavigation(false);
    Proxy->SetCastShadow(CastShadow);
    Proxy->SetStaticMesh(StaticMesh);
    Proxy->RegisterComponent();
    FrozenStaticMesh=Proxy;
    if (IsRenderStateCreated()) DestroyRenderState_Concurrent();
    return true;
}

void UMonsterCorpseMeshComponent::RestoreFrozenSkeletalMesh()
{
    if (!FrozenStaticMesh) return;
    FrozenStaticMesh->DestroyComponent();
    FrozenStaticMesh=nullptr;
    if (IsRegistered() && GetWorld() && !IsRenderStateCreated()) CreateRenderState_Concurrent(nullptr);
}

int32 UMonsterCorpseMeshComponent::PrepareFrozenProxyLOD(USkeletalMesh* Source)
{
#if WITH_EDITOR
    if (!Source || !Source->GetPathName().StartsWith(TEXT("/Game/Monsters/"))) return INDEX_NONE;
    const auto* Data=Source->GetResourceForRendering();
    if (!Data || Data->LODRenderData.IsEmpty()) return INDEX_NONE;
    int32 Lod=INDEX_NONE;
    for (int32 I=0;I<Data->LODRenderData.Num();++I)
    {
        const int32 Faces=Data->LODRenderData[I].GetTotalFaces();
        if (Faces>0 && Faces<=4500) {Lod=I;break;}
    }
    Source->Modify();
    if (Lod==INDEX_NONE)
    {
        const int32 Faces=Data->LODRenderData[0].GetTotalFaces();
        if (Faces<1) return INDEX_NONE;
        const auto Settings=Source->GetLODInfo(0)->BuildSettings;
        Lod=Source->GetLODNum();
        Source->AddLODInfo();
        auto* Info=Source->GetLODInfo(Lod);
        Info->BuildSettings=Settings;
        Info->ReductionSettings.BaseLOD=0;
        Info->ReductionSettings.TerminationCriterion=SMTC_NumOfTriangles;
        Info->ReductionSettings.NumOfTrianglesPercentage=FMath::Clamp(3000.f/Faces,.001f,1.f);
        Info->ReductionSettings.MaxBonesPerVertex=4;
        Info->ReductionSettings.bEnforceBoneBoundaries=true;
        Info->bHasBeenSimplified=true;
        Info->ScreenSize.Default=.001f;
        Info->LODHysteresis=0.f;
    }
    Source->GetLODInfo(Lod)->bAllowCPUAccess=true;
    Source->MarkPackageDirty();
    return Lod;
#else
    return INDEX_NONE;
#endif
}
