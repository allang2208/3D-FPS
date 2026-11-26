#pragma once
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"

// Diagnostic only: the actual posed torso's front/back surface at a queried
// mesh-X/Z position. This catches forearm/hand/weapon vertices inside the body;
// it is not a cloth collision solver or a visual acceptance claim.
struct FPistolReloadSkinProbe
{
    struct FTriangle { FVector A,B,C; };
    struct FResult { int32 Inside=0;double Depth=0.;FVector Point=FVector::ZeroVector;FName Bone;int32 Vertex=INDEX_NONE; };
    TArray<FVector3f> Vertices;
    TArray<uint8> Groups;
    TArray<int32> TorsoIndices;
    TArray<FTriangle> Triangles;
    TMap<FIntPoint,TArray<int32>> Grid;
    double ReferenceFrontFromSpine=0.;
    static FIntPoint Cell(const FVector& P){return FIntPoint(FMath::FloorToInt(P.X/4.),FMath::FloorToInt(P.Z/4.));}
    static void Skin(USkeletalMeshComponent* Mesh,TArray<FVector3f>& Out)
    {
        TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);
        const auto& LOD=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
        USkinnedMeshComponent::ComputeSkinnedPositions(Mesh,Out,Matrices,LOD,*Mesh->GetSkinWeightBuffer(0));
    }
    void Initialize(USkeletalMeshComponent* Body)
    {
        const auto& Ref=Body->GetSkeletalMeshAsset()->GetRefSkeleton();
        const auto& LOD=Body->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
        const auto* Weights=Body->GetSkinWeightBuffer(0);
        Groups.Init(0,LOD.GetNumVertices());
        const int32 Pelvis=Ref.FindBoneIndex(TEXT("pelvis"));
        const int32 Clavicles[2]={Ref.FindBoneIndex(TEXT("clavicle_r")),Ref.FindBoneIndex(TEXT("clavicle_l"))};
        const int32 Lower[2]={Ref.FindBoneIndex(TEXT("lowerarm_r")),Ref.FindBoneIndex(TEXT("lowerarm_l"))};
        const int32 Thigh[2]={Ref.FindBoneIndex(TEXT("thigh_r")),Ref.FindBoneIndex(TEXT("thigh_l"))};
        const int32 Neck=Ref.FindBoneIndex(TEXT("neck_01"));
        const auto Within=[&](int32 Bone,int32 Root){return Root!=INDEX_NONE&&(Bone==Root||Ref.BoneIsChildOf(Bone,Root));};
        for(const auto& Section:LOD.RenderSections)
            for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
            {
                int32 Bone=INDEX_NONE;uint16 Highest=0;
                for(uint32 J=0;J<Weights->GetMaxBoneInfluences();++J)
                    if(const uint16 Weight=Weights->GetBoneWeight(V,J);Weight>Highest)
                    {Highest=Weight;Bone=Section.BoneMap[Weights->GetBoneIndex(V,J)];}
                if(Bone==INDEX_NONE)continue;
                if(Within(Bone,Lower[0]))Groups[V]=2;
                else if(Within(Bone,Lower[1]))Groups[V]=3;
                else if(Within(Bone,Pelvis)&&!Within(Bone,Clavicles[0])&&!Within(Bone,Clavicles[1])&&
                    !Within(Bone,Thigh[0])&&!Within(Bone,Thigh[1])&&!Within(Bone,Neck))Groups[V]=1;
            }
        const auto* Indices=LOD.MultiSizeIndexContainer.GetIndexBuffer();
        FTransform SpineBind=FTransform::Identity;
        for(int32 B=Ref.FindBoneIndex(TEXT("spine_03"));B!=INDEX_NONE;B=Ref.GetParentIndex(B))
            SpineBind=SpineBind*Ref.GetRefBonePose()[B];
        for(int32 V=0;V<Groups.Num();++V)if(Groups[V]==1)
            ReferenceFrontFromSpine=FMath::Max(ReferenceFrontFromSpine,double(LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V).Y)-SpineBind.GetLocation().Y);
        for(int32 I=0;I<Indices->Num();I+=3)
        {
            const int32 A=Indices->Get(I),B=Indices->Get(I+1),C=Indices->Get(I+2);
            if(Groups[A]==1&&Groups[B]==1&&Groups[C]==1)
            {TorsoIndices.Add(A);TorsoIndices.Add(B);TorsoIndices.Add(C);}
        }
    }
    void Update(USkeletalMeshComponent* Body)
    {
        Skin(Body,Vertices);Triangles.Reset();Grid.Reset();
        for(int32 I=0;I<TorsoIndices.Num();I+=3)
        {
            const FTriangle T{FVector(Vertices[TorsoIndices[I]]),FVector(Vertices[TorsoIndices[I+1]]),FVector(Vertices[TorsoIndices[I+2]])};
            const int32 Index=Triangles.Add(T);
            const FIntPoint Lo=Cell(T.A.ComponentMin(T.B).ComponentMin(T.C)),Hi=Cell(T.A.ComponentMax(T.B).ComponentMax(T.C));
            for(int32 X=Lo.X;X<=Hi.X;++X)for(int32 Z=Lo.Y;Z<=Hi.Y;++Z)Grid.FindOrAdd(FIntPoint(X,Z)).Add(Index);
        }
    }
    double Depth(const FVector& P) const
    {
        const auto* Candidates=Grid.Find(Cell(P));if(!Candidates)return 0.;
        double Front=-DBL_MAX,Back=DBL_MAX;
        for(int32 I:*Candidates)
        {
            const auto& T=Triangles[I];const FVector AB=T.B-T.A,AC=T.C-T.A,AP=P-T.A;
            const double D=AB.X*AC.Z-AB.Z*AC.X;if(FMath::Abs(D)<1.e-8)continue;
            const double U=(AP.X*AC.Z-AP.Z*AC.X)/D,V=(AB.X*AP.Z-AB.Z*AP.X)/D;
            if(U<0.||V<0.||U+V>1.)continue;
            const double Y=T.A.Y+U*AB.Y+V*AC.Y;Front=FMath::Max(Front,Y);Back=FMath::Min(Back,Y);
        }
        return Front>Back?FMath::Max(0.,FMath::Min(Front-P.Y,P.Y-Back)):0.;
    }
    void Add(FResult& Result,const FVector& P) const
    {
        const double D=Depth(P);Result.Inside+=D>.2;
        if(D>Result.Depth){Result.Depth=D;Result.Point=P;}
    }
    FResult Arm(int32 Side) const
    {
        FResult Result;for(int32 V=0;V<Vertices.Num();++V)if(Groups[V]==Side+2)Add(Result,FVector(Vertices[V]));
        return Result;
    }
    FResult Weapon(USkeletalMeshComponent* Mesh,const FTransform& BodyFrame) const
    {
        FResult Result;TArray<FVector3f> Points;Skin(Mesh,Points);
        const auto& LOD=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
        const auto Frame=Mesh->GetComponentTransform().GetRelativeTransform(BodyFrame);
        const auto* Weights=Mesh->GetSkinWeightBuffer(0);
        const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
        for(const auto& Section:LOD.RenderSections)if(Mesh->IsMaterialSectionShown(Section.MaterialIndex,0))
            for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
            {
                const double Previous=Result.Depth;
                Add(Result,Frame.TransformPosition(FVector(Points[V])));
                if(Result.Depth<=Previous)continue;
                uint16 Highest=0;int32 Dominant=INDEX_NONE;
                for(uint32 J=0;J<Weights->GetMaxBoneInfluences();++J)
                    if(const uint16 Weight=Weights->GetBoneWeight(V,J);Weight>Highest)
                    {Highest=Weight;Dominant=Section.BoneMap[Weights->GetBoneIndex(V,J)];}
                Result.Bone=Dominant!=INDEX_NONE?Ref.GetBoneName(Dominant):NAME_None;Result.Vertex=V;
            }
        return Result;
    }
    void Part(FResult& Result,UStaticMeshComponent* Mesh,const FTransform& BodyFrame) const
    {
        if(!Mesh||!Mesh->GetStaticMesh()||!Mesh->IsVisible()||Mesh->bHiddenInGame)return;
        const auto& Buffer=Mesh->GetStaticMesh()->GetRenderData()->LODResources[0].VertexBuffers.PositionVertexBuffer;
        const auto Frame=Mesh->GetComponentTransform().GetRelativeTransform(BodyFrame);
        for(uint32 V=0;V<Buffer.GetNumVertices();++V)Add(Result,Frame.TransformPosition(FVector(Buffer.VertexPosition(V))));
    }
};
