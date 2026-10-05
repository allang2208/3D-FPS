#include "SpiralPillarM14.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "SkeletalMeshAttributes.h"
#include "Misc/FileHelper.h"
#include "Serialization/MemoryReader.h"
#endif

bool ASpiralPillarM14::ApplySoftDeathSequence(USkeletalMesh* SourceMesh,const FString& DataFile,const TArray<FName>& MorphNames)
{
#if WITH_EDITOR
    if(!SourceMesh||MorphNames.IsEmpty())return false;
    FMeshDescription* Description=SourceMesh->GetMeshDescription(0);if(!Description)return false;
    TArray<uint8> Bytes;if(!FFileHelper::LoadFileToArray(Bytes,*DataFile))return false;
    FMemoryReader Reader(Bytes);int32 Count=0,Targets=0;Reader<<Count;Reader<<Targets;
    const int64 Stride=3+3*int64(Targets);
    if(Count<=0||Targets!=MorphNames.Num()||Bytes.Num()!=8+int64(Count)*Stride*4)return false;
    TArray<float> Data;Data.SetNumUninitialized(int64(Count)*Stride);
    Reader.Serialize(Data.GetData(),Data.Num()*int64(sizeof(float)));Bytes.Empty();
    const auto& Ref=SourceMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Base=Ref.FindBoneIndex(TEXT("base")),XB=Ref.FindBoneIndex(TEXT("roottoe_00")),YB=Ref.FindBoneIndex(TEXT("roottoe_02"));
    if(Base==INDEX_NONE||XB==INDEX_NONE||YB==INDEX_NONE)return false;
    const FVector X=(Frames[XB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    const FVector Y=(Frames[YB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X*10000.),FMath::RoundToInt(P.Y*10000.),FMath::RoundToInt(P.Z*10000.));};
    auto Position=[&](int32 Row){const float* V=Data.GetData()+Row*Stride;return FVector(V[0],V[1],V[2]);};
    TMap<FIntVector,int32> Rows;Rows.Reserve(Count);
    for(int32 I=0;I<Count;++I)Rows.Add(Key(Position(I)),I);
    SourceMesh->Modify();FSkeletalMeshAttributes Attributes(*Description);
    // This duplicate retains all V13 topology, UVs and repaired skin weights.
    // Replace its death shapes to avoid carrying both production generations.
    for(const FName Name:Attributes.GetMorphTargetNames())
        if(Name.ToString().StartsWith(TEXT("M14_Death")))Attributes.UnregisterMorphTargetAttribute(Name);
    TArray<TVertexAttributesRef<FVector3f>> Deltas;
    for(const FName Name:MorphNames)
    {
        Attributes.RegisterMorphTargetAttribute(Name,false);
        Deltas.Add(Attributes.GetVertexMorphPositionDelta(Name));
    }
    const auto Positions=Attributes.GetVertexPositions();int32 Missing=0;
    for(const FVertexID Vertex:Description->Vertices().GetElementIDs())
    {
        const FVector Original(Positions[Vertex]);
        const FVector P=FVector(Original.Dot(X),Original.Dot(Y),Original.Z)*.01;
        const FIntVector K=Key(P);const int32* Exact=Rows.Find(K);
        int32 Row=Exact?*Exact:INDEX_NONE;
        double Best=Exact?FVector::DistSquared(P,Position(Row)):FMath::Square(.00016);
        if(Best>1.e-12)
            for(int32 I=-1;I<=1;++I)for(int32 J=-1;J<=1;++J)for(int32 Z=-1;Z<=1;++Z)
                if(const int32* Candidate=Rows.Find(K+FIntVector(I,J,Z)))
                {
                    const double Dist=FVector::DistSquared(P,Position(*Candidate));
                    if(Dist<Best){Best=Dist;Row=*Candidate;}
                }
        if(Row==INDEX_NONE||Best>FMath::Square(.00016)){++Missing;continue;}
        const float* Values=Data.GetData()+Row*Stride+3;
        for(int32 J=0;J<Targets;++J)
        {
            const float* D=Values+J*3;
            Deltas[J][Vertex]=FVector3f((X*D[0]+Y*D[1]+FVector::UpVector*D[2])*100.);
        }
    }
    UE_LOG(LogTemp,Display,TEXT("M14_SOFT_DEATH targets=%d vertices=%d missing=%d"),Targets,Description->Vertices().Num(),Missing);
    if(Missing||!SourceMesh->CommitMeshDescription(0))return false;
    SourceMesh->PostEditChange();SourceMesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}
