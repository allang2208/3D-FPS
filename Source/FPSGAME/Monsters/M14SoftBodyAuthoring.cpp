#include "M14SoftBodyDeath.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "Animation/Skeleton.h"
#include "MeshDescription.h"
#include "SkeletalMeshAttributes.h"
#include "Misc/FileHelper.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/BufferArchive.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#endif

bool UM14SoftBodyData::BuildCorpse(USkeletalMesh* Mesh,USkeleton* CorpseSkeleton,UM14SoftBodyData* Data,const FString& CageFile,const FString& EmbeddingFile)
{
#if WITH_EDITOR
    if(!Mesh||!Data||!CorpseSkeleton)return false;
    FMeshDescription* Description=Mesh->GetMeshDescription(0);if(!Description)return false;
    FString Text;TSharedPtr<FJsonObject> Json;
    if(!FFileHelper::LoadFileToString(Text,*CageFile)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json))return false;
    TArray<uint8> Bytes;if(!FFileHelper::LoadFileToArray(Bytes,*EmbeddingFile))return false;
    FMemoryReader Reader(Bytes);int32 Count=0,Width=0;Reader<<Count<<Width;
    if(Count<=0||Width!=13||Bytes.Num()!=8+int64(Count)*52)return false;
    Mesh->SetSkeleton(CorpseSkeleton);
    const auto& Ref=Mesh->GetRefSkeleton();Data->SourceRefFrames=Ref.GetRefBonePose();
    Data->SourceBoneNames.Reset();
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        Data->SourceBoneNames.Add(Ref.GetBoneName(I));
        if(Ref.GetParentIndex(I)>=0)Data->SourceRefFrames[I]*=Data->SourceRefFrames[Ref.GetParentIndex(I)];
    }
    FString Coordinates;Json->TryGetStringField(TEXT("coordinates"),Coordinates);
    const bool MeshCoordinates=Coordinates==TEXT("mesh_m");
    const int32 Base=MeshCoordinates?0:Ref.FindBoneIndex(TEXT("base")),XB=Ref.FindBoneIndex(TEXT("roottoe_00")),YB=Ref.FindBoneIndex(TEXT("roottoe_02"));
    if(Base==INDEX_NONE||(!MeshCoordinates&&(XB==INDEX_NONE||YB==INDEX_NONE)))return false;
    const auto Frames=Data->SourceRefFrames;
    const FVector X=MeshCoordinates?FVector::ForwardVector:(Frames[XB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    const FVector Y=MeshCoordinates?FVector::RightVector:(Frames[YB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    auto ToMesh=[&](const FVector& P){return 100.*(X*P.X+Y*P.Y+FVector::UpVector*P.Z);};
    auto Vec=[](const TArray<TSharedPtr<FJsonValue>>& V){return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());};
    Data->Nodes.Reset();Data->Edges.Reset();Data->Tets.Reset();Data->Hardware.Reset();
    Data->SoftNodeCount=int32(Json->GetNumberField(TEXT("soft_node_count")));
    Data->SpacingCm=float(Json->GetNumberField(TEXT("spacing_m"))*100.);
    for(const auto& V:Json->GetArrayField(TEXT("nodes")))
    {FM14SoftNode N;N.Rest=ToMesh(Vec(V->AsArray()));Data->Nodes.Add(N);}
    TSet<uint64> EdgeKeys;
    auto AddEdge=[&](int32 A,int32 B,uint8 Kind)
    {
        if(A==B)return;
        const uint64 Key=(uint64(FMath::Min(A,B))<<32)|uint32(FMath::Max(A,B));
        if(EdgeKeys.Contains(Key))return;EdgeKeys.Add(Key);
        FM14SoftEdge E;E.A=A;E.B=B;E.Kind=Kind;Data->Edges.Add(E);
    };
    for(const auto& V:Json->GetArrayField(TEXT("tetrahedra")))
    {
        FM14SoftTet T;for(const auto& I:V->AsArray())T.Nodes.Add(int32(I->AsNumber()));
        if(T.Nodes.Num()!=4)return false;
        for(int32 I=0;I<4;++I)for(int32 J=I+1;J<4;++J)AddEdge(T.Nodes[I],T.Nodes[J],0);
        Data->Tets.Add(T);
    }
    const TArray<TSharedPtr<FJsonValue>>* Reinforced=nullptr;
    if(Json->TryGetArrayField(TEXT("reinforced_edges"),Reinforced))
    {
        TSet<uint64> Keys;
        for(const auto& V:*Reinforced)
        {
            const auto& Pair=V->AsArray();const int32 A=int32(Pair[0]->AsNumber()),B=int32(Pair[1]->AsNumber());
            Keys.Add((uint64(FMath::Min(A,B))<<32)|uint32(FMath::Max(A,B)));
        }
        for(auto& E:Data->Edges)
            if(Keys.Contains((uint64(FMath::Min(E.A,E.B))<<32)|uint32(FMath::Max(E.A,E.B))))E.Kind=3;
    }
    for(const auto& V:Json->GetArrayField(TEXT("hardware")))
    {
        const auto H=V->AsObject();FM14RigidPatch Patch;Patch.Center=ToMesh(Vec(H->GetArrayField(TEXT("center"))));
        for(const auto& I:H->GetArrayField(TEXT("nodes")))Patch.Nodes.Add(int32(I->AsNumber()));
        const auto& Anchors=H->GetArrayField(TEXT("anchors"));
        for(int32 I=0;I<4;++I)
        {
            for(int32 J=I+1;J<4;++J)AddEdge(Patch.Nodes[I],Patch.Nodes[J],1);
            // Short local tethers join metal to nearby tissue; no distant chain binding.
            AddEdge(Patch.Nodes[I],int32(Anchors[I]->AsNumber()),2);
        }
        Data->Hardware.Add(Patch);
    }
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X*10000.),FMath::RoundToInt(P.Y*10000.),FMath::RoundToInt(P.Z*10000.));};
    struct FEmbedding{float V[13];};TMap<FIntVector,FEmbedding> Records;Records.Reserve(Count);
    for(int32 I=0;I<Count;++I){FEmbedding R;Reader.Serialize(R.V,52);Records.Add(Key(FVector(R.V[0],R.V[1],R.V[2])),R);}
    Mesh->Modify();Data->Modify();FSkeletalMeshAttributes Attributes(*Description);
    const auto Positions=Attributes.GetVertexPositions();auto Weights=Attributes.GetVertexSkinWeights();
    const int32 SourceBones=Data->SourceBoneNames.Num();
    TArray<TArray<double>> SourceSums,HardwareSums;
    SourceSums.SetNum(Data->Nodes.Num());for(auto& Sum:SourceSums)Sum.Init(0.,SourceBones);
    HardwareSums.SetNum(Data->Hardware.Num());for(auto& Sum:HardwareSums)Sum.Init(0.,SourceBones);
    TArray<FVector> SupportDirections;
    for(int32 A=-1;A<=1;++A)for(int32 B=-1;B<=1;++B)for(int32 C=-1;C<=1;++C)
        if(A||B||C)SupportDirections.Add(FVector(A,B,C).GetSafeNormal());
    TArray<TArray<double>> SupportValues;SupportValues.SetNum(Data->Hardware.Num());
    for(int32 I=0;I<Data->Hardware.Num();++I)
    {Data->Hardware[I].SupportOffsets.Init(FVector::ZeroVector,26);SupportValues[I].Init(-DBL_MAX,26);}

    FReferenceSkeleton NewRef=Mesh->GetRefSkeleton();
    {
        FReferenceSkeletonModifier Modifier(NewRef,Mesh->GetSkeleton());
        auto AddBone=[&](const FName Name,const FVector& At)
        {
            // FinalRefBoneInfo is rebuilt only when Modifier is destroyed. Its
            // GetNum() stays at the original 49 throughout this append batch.
            const int32 Index=NewRef.GetRawBoneNum();
            Modifier.Add(FMeshBoneInfo(Name,Name.ToString(),0),FTransform(FQuat::Identity,At).GetRelativeTransform(Frames[0]));
            return Index;
        };
        for(int32 I=0;I<Data->SoftNodeCount;++I)
            Data->Nodes[I].RenderBone=AddBone(FName(*FString::Printf(TEXT("soft_%04d"),I)),Data->Nodes[I].Rest);
        for(int32 I=0;I<Data->Hardware.Num();++I)
            Data->Hardware[I].RenderBone=AddBone(FName(*FString::Printf(TEXT("rigid_%02d"),I)),Data->Hardware[I].Center);
    }
    int32 Missing=0;
    for(const FVertexID Vertex:Description->Vertices().GetElementIDs())
    {
        const FVector Original(Positions[Vertex]);const FVector P=FVector(Original.Dot(X),Original.Dot(Y),Original.Z)*.01;
        const FIntVector K=Key(P);const FEmbedding* R=Records.Find(K);
        if(!R)
        {
            double Best=FMath::Square(.00016);
            for(int32 I=-1;I<=1;++I)for(int32 J=-1;J<=1;++J)for(int32 Z=-1;Z<=1;++Z)
                if(const FEmbedding* Candidate=Records.Find(K+FIntVector(I,J,Z)))
                {const double D=FVector::DistSquared(P,FVector(Candidate->V[0],Candidate->V[1],Candidate->V[2]));if(D<Best){Best=D;R=Candidate;}}
        }
        if(!R){++Missing;continue;}
        const int32 H=int32(R->V[11]);const float Blend=H>=0?FMath::Clamp(R->V[12],0.f,1.f):0.f;
        const auto Old=Weights.Get(Vertex);
        TArray<UE::AnimationCore::FBoneWeight,TInlineAllocator<8>> NewWeights;
        for(int32 J=0;J<4;++J)
        {
            const int32 N=int32(R->V[3+J]);const float W=R->V[7+J];
            if(!Data->Nodes.IsValidIndex(N)||N>=Data->SoftNodeCount)return false;
            for(const auto& B:Old)SourceSums[N][B.GetBoneIndex()]+=W*B.GetWeight();
            if(W*(1.f-Blend)>1.e-7f)NewWeights.Add(UE::AnimationCore::FBoneWeight(Data->Nodes[N].RenderBone,W*(1.f-Blend)));
        }
        if(Blend>0.f)
        {
            NewWeights.Add(UE::AnimationCore::FBoneWeight(Data->Hardware[H].RenderBone,Blend));
            if(Blend>.99f)
            {
                for(const auto& B:Old)HardwareSums[H][B.GetBoneIndex()]+=B.GetWeight();
                const FVector Offset=Original-Data->Hardware[H].Center;
                for(int32 J=0;J<26;++J)if(Offset.Dot(SupportDirections[J])>SupportValues[H][J])
                {SupportValues[H][J]=Offset.Dot(SupportDirections[J]);Data->Hardware[H].SupportOffsets[J]=Offset;}
            }
        }
        Weights.Set(Vertex,MakeArrayView(NewWeights));
    }
    if(Missing){UE_LOG(LogTemp,Error,TEXT("M14_XPBD embedding missing %d vertices"),Missing);return false;}
    // Source skin only initializes the cage. It never also drives a falling corpse.
    TArray<int32> Bound;
    for(int32 I=0;I<Data->SoftNodeCount;++I)
    {
        TArray<int32> Order;for(int32 B=0;B<SourceBones;++B)Order.Add(B);
        Order.Sort([&](int32 A,int32 B){return SourceSums[I][A]>SourceSums[I][B];});
        double Total=0.;for(int32 J=0;J<FMath::Min(8,SourceBones);++J)Total+=SourceSums[I][Order[J]];
        if(Total<=1.e-8)continue;
        for(int32 J=0;J<FMath::Min(8,SourceBones);++J)if(SourceSums[I][Order[J]]>1.e-8)
        {Data->Nodes[I].SourceBones.Add(Order[J]);Data->Nodes[I].SourceWeights.Add(float(SourceSums[I][Order[J]]/Total));}
        Bound.Add(I);
    }
    if(Bound.IsEmpty())return false;
    for(int32 I=0;I<Data->SoftNodeCount;++I)if(Data->Nodes[I].SourceBones.IsEmpty())
    {
        int32 Closest=Bound[0];double Best=DBL_MAX;
        for(int32 J:Bound){const double D=FVector::DistSquared(Data->Nodes[I].Rest,Data->Nodes[J].Rest);if(D<Best){Best=D;Closest=J;}}
        Data->Nodes[I].SourceBones=Data->Nodes[Closest].SourceBones;Data->Nodes[I].SourceWeights=Data->Nodes[Closest].SourceWeights;
    }
    // Optional anatomical stations retain a precise live-pose source even
    // where distant parts of a coiled appendage are spatially adjacent.
    const TArray<TSharedPtr<FJsonValue>>* StationWeights=nullptr;
    if(Json->TryGetArrayField(TEXT("node_source_weights"),StationWeights))
    {
        if(StationWeights->Num()!=Data->SoftNodeCount)return false;
        for(int32 I=0;I<Data->SoftNodeCount;++I)
        {
            const auto& Row=(*StationWeights)[I]->AsArray();if(Row.IsEmpty())continue;
            auto& N=Data->Nodes[I];N.SourceBones.Reset();N.SourceWeights.Reset();float Total=0.f;
            for(const auto& V:Row)
            {
                const auto& Pair=V->AsArray();if(Pair.Num()!=2)return false;
                const int32 B=int32(Pair[0]->AsNumber());const float W=float(Pair[1]->AsNumber());
                if(B<0||B>=SourceBones||W<=0.f)return false;
                N.SourceBones.Add(B);N.SourceWeights.Add(W);Total+=W;
            }
            for(float& W:N.SourceWeights)W/=Total;
        }
    }
    for(int32 I=0;I<Data->Hardware.Num();++I)
    {
        auto& H=Data->Hardware[I];int32 Best=Base;
        for(int32 B=0;B<SourceBones;++B)if(HardwareSums[I][B]>HardwareSums[I][Best])Best=B;
        H.SourceBone=Best;
        for(int32 N:H.Nodes){Data->Nodes[N].SourceBones={Best};Data->Nodes[N].SourceWeights={1.f};}
    }
    for(FName Morph:Attributes.GetMorphTargetNames())Attributes.UnregisterMorphTargetAttribute(Morph);
    Mesh->UnregisterAllMorphTarget();Mesh->SetPhysicsAsset(nullptr);Mesh->SetRefSkeleton(NewRef);Mesh->CalculateInvRefMatrices();
    if(Attributes.HasBones())
    {
        TArray<FBoneID> Existing;for(const FBoneID B:Attributes.Bones().GetElementIDs())Existing.Add(B);
        for(const FBoneID B:Existing)Attributes.DeleteBone(B);
        for(int32 I=0;I<NewRef.GetNum();++I)
        {
            const FBoneID B(I);Attributes.CreateBone(B);Attributes.GetBoneNames()[B]=NewRef.GetBoneName(I);
            Attributes.GetBoneParentIndices()[B]=NewRef.GetParentIndex(I);Attributes.GetBonePoses()[B]=NewRef.GetRefBonePose()[I];
        }
    }
    if(auto* LOD=Mesh->GetLODInfo(0))LOD->BuildSettings.BoneInfluenceLimit=8;
    if(!Mesh->CommitMeshDescription(0))return false;
    Mesh->GetSkeleton()->MergeAllBonesToBoneTree(Mesh);Mesh->GetSkeleton()->MarkPackageDirty();
    Mesh->PostEditChange();Mesh->MarkPackageDirty();Data->CorpseMesh=Mesh;Data->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("M14_XPBD authored nodes=%d tets=%d edges=%d hardware=%d"),Data->Nodes.Num(),Data->Tets.Num(),Data->Edges.Num(),Data->Hardware.Num());
    return true;
#else
    return false;
#endif
}

bool UM14SoftBodyData::ExportSurface(USkeletalMesh* Mesh,const FString& File,const TArray<FName>& OmitBranches)
{
#if WITH_EDITOR
    if(!Mesh)return false;
    auto* Description=Mesh->GetMeshDescription(0);if(!Description)return false;
    FSkeletalMeshAttributes Attributes(*Description);
    if(!OmitBranches.IsEmpty())
    {
        // HandBrain has overlapping attack-only duplicate surfaces. They are
        // hidden in its death clip and are not part of the persistent corpse.
        const auto& Ref=Mesh->GetRefSkeleton();
        const auto Weights=Attributes.GetVertexSkinWeights();
        TSet<FVertexID> Omitted;
        for(const FVertexID V:Description->Vertices().GetElementIDs())
        {
            float Total=0.f;
            for(const auto& Weight:Weights.Get(V))
                for(int32 Bone=Weight.GetBoneIndex();Bone>=0;Bone=Ref.GetParentIndex(Bone))
                    if(OmitBranches.Contains(Ref.GetBoneName(Bone))){Total+=Weight.GetWeight();break;}
            if(Total>.99f)Omitted.Add(V);
        }
        TArray<FTriangleID> Remove;
        for(const FTriangleID T:Description->Triangles().GetElementIDs())
        {
            const auto Vertices=Description->GetTriangleVertices(T);
            if(Omitted.Contains(Vertices[0])&&Omitted.Contains(Vertices[1])&&Omitted.Contains(Vertices[2]))Remove.Add(T);
        }
        Description->DeleteTriangles(Remove);
        FElementIDRemappings Remap;Description->Compact(Remap);
        if(!Mesh->CommitMeshDescription(0))return false;
        Mesh->PostEditChange();Mesh->MarkPackageDirty();
        Description=Mesh->GetMeshDescription(0);
    }
    const auto Positions=Description->GetVertexPositions();
    // Companion authoring data permits anatomical cages without guessing the
    // branch from spatial proximity (coiled tentacles often touch the torso).
    const auto& Ref=Mesh->GetRefSkeleton();auto Frames=Ref.GetRefBonePose();
    TArray<TSharedPtr<FJsonValue>> Bones,Parents,Heads,Skin;
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        if(Parent>=0)Frames[I]*=Frames[Parent];
        Bones.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(I).ToString()));
        Parents.Add(MakeShared<FJsonValueNumber>(Parent));
        const FVector P=Frames[I].GetLocation()*.01;
        Heads.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
            MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)}));
    }
    const auto Weights=FSkeletalMeshAttributes(*Description).GetVertexSkinWeights();
    FBufferArchive Bytes;
    int32 Count=Description->Vertices().Num();Bytes<<Count;
    for(const FVertexID V:Description->Vertices().GetElementIDs())
    {
        FVector3f P=Positions[V]*.01f;Bytes<<P.X<<P.Y<<P.Z;
        TArray<TSharedPtr<FJsonValue>> Row;
        for(const auto& W:Weights.Get(V))
            Row.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
                MakeShared<FJsonValueNumber>(W.GetBoneIndex()),MakeShared<FJsonValueNumber>(W.GetWeight())}));
        Skin.Add(MakeShared<FJsonValueArray>(Row));
    }
    auto SkinJson=MakeShared<FJsonObject>();SkinJson->SetArrayField(TEXT("bones"),Bones);
    SkinJson->SetArrayField(TEXT("parents"),Parents);SkinJson->SetArrayField(TEXT("heads_m"),Heads);
    SkinJson->SetArrayField(TEXT("weights"),Skin);FString SkinText;
    FJsonSerializer::Serialize(SkinJson,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&SkinText));
    return FFileHelper::SaveArrayToFile(Bytes,*File)&&FFileHelper::SaveStringToFile(SkinText,*(File+TEXT(".skin.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
#else
    return false;
#endif
}

void UM14SoftBodyData::BindToLivingMesh(USkeletalMesh* Mesh,UM14SoftBodyData* InData)
{
#if WITH_EDITOR
    if(!Mesh||!InData||!InData->CorpseMesh)return;
    Mesh->Modify();
    auto* Binding=NewObject<UMonsterSoftCorpseBinding>(Mesh,NAME_None,RF_Transactional);
    Binding->Data=InData;Mesh->AddAssetUserData(Binding);Mesh->MarkPackageDirty();
#endif
}
