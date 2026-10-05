#include "SpiralPillarM14.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "SkeletalMeshAttributes.h"
#include "Misc/FileHelper.h"
#include "Serialization/MemoryReader.h"
#endif

bool ASpiralPillarM14::ApplyHardwareSkin(USkeletalMesh* SourceMesh,const FString& DataFile,const TArray<FName>& SourceBones)
{
#if WITH_EDITOR
    if(!SourceMesh)return false;
    FMeshDescription* Description=SourceMesh->GetMeshDescription(0);if(!Description)return false;
    TArray<uint8> Bytes;if(!FFileHelper::LoadFileToArray(Bytes,*DataFile))return false;
    FMemoryReader Reader(Bytes);int32 Count=0;Reader<<Count;
    if(Count<=0||Bytes.Num()!=4+int64(Count)*84)return false;
    const auto& Ref=SourceMesh->GetRefSkeleton();TArray<int32> BoneMap;
    for(const FName Name:SourceBones){const int32 Index=Ref.FindBoneIndex(Name);if(Index==INDEX_NONE)return false;BoneMap.Add(Index);}
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Base=Ref.FindBoneIndex(TEXT("base")),XB=Ref.FindBoneIndex(TEXT("roottoe_00")),YB=Ref.FindBoneIndex(TEXT("roottoe_02"));
    if(Base==INDEX_NONE||XB==INDEX_NONE||YB==INDEX_NONE)return false;
    const FVector X=(Frames[XB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    const FVector Y=(Frames[YB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    auto ToBlender=[&](const FVector& P){return FVector(P.Dot(X),P.Dot(Y),P.Z)*.01;};
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X*10000.),FMath::RoundToInt(P.Y*10000.),FMath::RoundToInt(P.Z*10000.));};
    struct FRecord{float V[21];};
    TMap<FIntVector,FRecord> Records[2];
    for(int32 I=0;I<Count;++I)
    {
        FRecord R;Reader.Serialize(R.V,84);
        Records[R.V[3]>.5f?1:0].Add(Key(FVector(R.V[0],R.V[1],R.V[2])),R);
    }
    SourceMesh->Modify();FSkeletalMeshAttributes Attributes(*Description);
    auto Positions=Attributes.GetVertexPositions();auto Weights=Attributes.GetVertexSkinWeights();
    const auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();
    TSet<FVertexID> Metal,Tissue;
    for(const FTriangleID Triangle:Description->Triangles().GetElementIDs())
    {
        const bool IsMetal=Slots[Description->GetTrianglePolygonGroup(Triangle)].ToString().Contains(TEXT("Metal"));
        for(const FVertexID V:Description->GetTriangleVertices(Triangle))(IsMetal?Metal:Tissue).Add(V);
    }
    // Original import already split the material islands. Never apply rigid
    // weights to a shared tissue point if an incompatible source is supplied.
    for(const FVertexID V:Metal)if(Tissue.Contains(V))
    {UE_LOG(LogTemp,Error,TEXT("M14_HARDWARE shared source vertex needs splitting %d"),V.GetValue());return false;}
    const FName MorphNames[3]={TEXT("M14_DeathSag"),TEXT("M14_DeathFold"),TEXT("M14_DeathSpread")};
    TArray<TVertexAttributesRef<FVector3f>> Deltas;
    for(const FName Name:MorphNames)Deltas.Add(Attributes.GetVertexMorphPositionDelta(Name));
    int32 Changed=0,MissingMetal=0;
    for(const FVertexID Vertex:Description->Vertices().GetElementIDs())
    {
        const bool IsMetal=Metal.Contains(Vertex);const FVector P=ToBlender(FVector(Positions[Vertex]));
        const FIntVector K=Key(P);const auto& Table=Records[IsMetal?1:0];const FRecord* R=Table.Find(K);
        if(!R)
        {
            // Quantization may straddle a cell after the FBX axis conversion.
            double Best=FMath::Square(.00016);
            for(int32 I=-1;I<=1;++I)for(int32 J=-1;J<=1;++J)for(int32 Z=-1;Z<=1;++Z)
                if(const FRecord* Candidate=Table.Find(K+FIntVector(I,J,Z)))
                {const double Dist=FVector::DistSquared(P,FVector(Candidate->V[0],Candidate->V[1],Candidate->V[2]));if(Dist<Best){Best=Dist;R=Candidate;}}
        }
        if(!R){if(IsMetal)++MissingMetal;continue;}
        TArray<UE::AnimationCore::FBoneWeight,TInlineAllocator<4>> NewWeights;
        for(int32 J=0;J<4;++J)if(R->V[8+J]>0.f)
        {
            const int32 Source=int32(R->V[4+J]);if(!BoneMap.IsValidIndex(Source))return false;
            NewWeights.Add(UE::AnimationCore::FBoneWeight(BoneMap[Source],R->V[8+J]));
        }
        Weights.Set(Vertex,MakeArrayView(NewWeights));
        // Source-material cuts duplicate the same surface point. Boundary
        // tissue rows must carry the same deltas as their rigid hardware mate.
        for(int32 J=0;J<3;++J)
        {
            const float* D=R->V+12+J*3;
            Deltas[J][Vertex]=FVector3f((X*D[0]+Y*D[1]+FVector::UpVector*D[2])*100.);
        }
        ++Changed;
    }
    UE_LOG(LogTemp,Display,TEXT("M14_HARDWARE applied=%d metal=%d missingMetal=%d"),Changed,Metal.Num(),MissingMetal);
    if(Metal.IsEmpty()||MissingMetal>0||!SourceMesh->CommitMeshDescription(0))return false;
    SourceMesh->PostEditChange();SourceMesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}

bool ASpiralPillarM14::ApplySupportSkin(USkeletalMesh* SourceMesh,const FString& DataFile,const TArray<FName>& SourceBones)
{
#if WITH_EDITOR
    if(!SourceMesh)return false;
    FMeshDescription* Description=SourceMesh->GetMeshDescription(0);if(!Description)return false;
    TArray<uint8> Bytes;if(!FFileHelper::LoadFileToArray(Bytes,*DataFile))return false;
    FMemoryReader Reader(Bytes);int32 Count=0;Reader<<Count;
    if(Count<=0||Bytes.Num()!=4+int64(Count)*76)return false;
    const auto& Ref=SourceMesh->GetRefSkeleton();TArray<int32> BoneMap;
    for(const FName Name:SourceBones){const int32 I=Ref.FindBoneIndex(Name);if(I==INDEX_NONE)return false;BoneMap.Add(I);}
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Base=Ref.FindBoneIndex(TEXT("base")),XB=Ref.FindBoneIndex(TEXT("roottoe_00")),YB=Ref.FindBoneIndex(TEXT("roottoe_02"));
    if(Base==INDEX_NONE||XB==INDEX_NONE||YB==INDEX_NONE)return false;
    const FVector X=(Frames[XB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    const FVector Y=(Frames[YB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X*10000.),FMath::RoundToInt(P.Y*10000.),FMath::RoundToInt(P.Z*10000.));};
    struct FRecord{float V[19];};TMap<FIntVector,FRecord> Records;Records.Reserve(Count);
    for(int32 I=0;I<Count;++I)
    {FRecord R;Reader.Serialize(R.V,76);Records.Add(Key(FVector(R.V[0],R.V[1],R.V[2])),R);}
    SourceMesh->Modify();FSkeletalMeshAttributes Attributes(*Description);
    const auto Positions=Attributes.GetVertexPositions();auto Weights=Attributes.GetVertexSkinWeights();int32 Changed=0;
    for(const FVertexID Vertex:Description->Vertices().GetElementIDs())
    {
        const FVector Original(Positions[Vertex]);const FVector P=FVector(Original.Dot(X),Original.Dot(Y),Original.Z)*.01;
        const FIntVector K=Key(P);const FRecord* R=Records.Find(K);
        if(!R)
        {
            double Best=FMath::Square(.00016);
            for(int32 I=-1;I<=1;++I)for(int32 J=-1;J<=1;++J)for(int32 Z=-1;Z<=1;++Z)
                if(const FRecord* Candidate=Records.Find(K+FIntVector(I,J,Z)))
                {const double Dist=FVector::DistSquared(P,FVector(Candidate->V[0],Candidate->V[1],Candidate->V[2]));if(Dist<Best){Best=Dist;R=Candidate;}}
        }
        if(!R)continue;
        TArray<UE::AnimationCore::FBoneWeight,TInlineAllocator<8>> NewWeights;
        for(int32 J=0;J<8;++J)if(R->V[11+J]>0.f)
        {
            const int32 Source=int32(R->V[3+J]);if(!BoneMap.IsValidIndex(Source))return false;
            NewWeights.Add(UE::AnimationCore::FBoneWeight(BoneMap[Source],R->V[11+J]));
        }
        Weights.Set(Vertex,MakeArrayView(NewWeights));++Changed;
    }
    // Preserve the repaired transition weights instead of dropping the fifth
    // influence at an arbitrary rank boundary and creating another skin spike.
    if(auto* LOD=SourceMesh->GetLODInfo(0))LOD->BuildSettings.BoneInfluenceLimit=8;
    UE_LOG(LogTemp,Display,TEXT("M14_SUPPORT_SKIN changed=%d sourceRows=%d"),Changed,Count);
    if(!Changed||!SourceMesh->CommitMeshDescription(0))return false;
    SourceMesh->PostEditChange();SourceMesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}
