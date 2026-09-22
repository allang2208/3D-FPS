#include "WitchRebuiltMonster.h"
#include "WitchRebuiltClothingAsset.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "ClothingAssetFactory.h"
#include "ClothingAsset.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
TArray<FVector3f> DrapeMappingNormals(const FClothPhysicalMeshData& Physical)
{
    TArray<FVector3f> Normals; Normals.Init(FVector3f::ZeroVector,Physical.Vertices.Num());
    for (int32 T=0; T<Physical.Indices.Num(); T+=3)
    {
        const int32 A=Physical.Indices[T],B=Physical.Indices[T+1],C=Physical.Indices[T+2];
        FVector3f N=FVector3f::CrossProduct(Physical.Vertices[C]-Physical.Vertices[A],Physical.Vertices[B]-Physical.Vertices[A]);
        if (N.Normalize()) { Normals[A]+=N; Normals[B]+=N; Normals[C]+=N; }
    }
    for (auto& N:Normals) if (!N.Normalize()) N=FVector3f::XAxisVector;
    return Normals;
}

FVector ReconstructDrapePoint(const FVector4f& B,const FVector* P,const FVector* N)
{
    return B.X*(P[0]-B.W*N[0])+B.Y*(P[1]-B.W*N[1])+B.Z*(P[2]-B.W*N[2]);
}

// Invert the same interpolated-normal prism used by the cloth vertex shader.
// Reject extrapolating roots instead of accepting a huge signed barycentric pair.
bool FitDrapePoint(const FVector& Target,const FVector* P,const FVector* N,FVector4f& Result,bool bPosition)
{
    const FVector Closest=FMath::ClosestPointOnTriangleToPoint(Target,P[0],P[1],P[2]);
    const FVector Bary=FMath::ComputeBaryCentric2D(Closest,P[0],P[1],P[2]);
    double U=Bary.Y,V=Bary.Z;
    const FVector InitialNormal=(1-U-V)*N[0]+U*N[1]+V*N[2];
    double H=-(Target-Closest).Dot(InitialNormal)/FMath::Max(1.e-8,InitialNormal.SizeSquared());
    for (int32 Iteration=0; Iteration<16; ++Iteration)
    {
        const FVector Normal=N[0]+U*(N[1]-N[0])+V*(N[2]-N[0]);
        const FVector Current=P[0]+U*(P[1]-P[0])+V*(P[2]-P[0])-H*Normal;
        const FVector Error=Target-Current;
        if (Error.SizeSquared()<1.e-8) break;
        const FVector DU=P[1]-P[0]-H*(N[1]-N[0]),DV=P[2]-P[0]-H*(N[2]-N[0]),DH=-Normal;
        const double Determinant=DU.Dot(DV.Cross(DH));
        if (FMath::Abs(Determinant)<1.e-9) return false;
        U+=Error.Dot(DV.Cross(DH))/Determinant;
        V+=DU.Dot(Error.Cross(DH))/Determinant;
        H+=DU.Dot(DV.Cross(Error))/Determinant;
        if (!FMath::IsFinite(U) || !FMath::IsFinite(V) || !FMath::IsFinite(H) || FMath::Abs(H)>30.) return false;
    }
    Result=FVector4f(1-U-V,U,V,H);
    const float Limit=bPosition?1.25f:8.f;
    if (FMath::Max3(FMath::Abs(Result.X),FMath::Abs(Result.Y),FMath::Abs(Result.Z))>Limit ||
        (bPosition && FMath::Min3(Result.X,Result.Y,Result.Z)<-.25f)) return false;
    return FVector::DistSquared(ReconstructDrapePoint(Result,P,N),Target)<.0004;
}

void StabilizeDrapeMapping(FSkelMeshSection& Section,const UClothingAssetCommon* Cloth)
{
    const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
    const auto Normals=DrapeMappingNormals(Physical);
    const auto* MaxDistances=Physical.FindWeightMap(EWeightMapTargetCommon::MaxDistance);
    auto& Mapping=Section.ClothMappingDataLODs[0];
    if (Mapping.Num()!=Section.SoftVertices.Num()) return; // This authoring pipeline uses single influence records.
    int32 Repaired=0,Fallback=0;
    for (int32 I=0; I<Mapping.Num(); ++I)
    {
        auto& M=Mapping[I];
        if (M.SourceMeshVertIndices[3]==0xffff) continue;
        const FVector Target(Section.SoftVertices[I].Position);
        FVector P[3],N[3];
        for (int32 J=0; J<3; ++J) { P[J]=FVector(Physical.Vertices[M.SourceMeshVertIndices[J]]); N[J]=FVector(Normals[M.SourceMeshVertIndices[J]]); }
        const auto& B=M.PositionBaryCoordsAndDist;
        if (FMath::Max3(FMath::Abs(B.X),FMath::Abs(B.Y),FMath::Abs(B.Z))<=1.25f &&
            FMath::Min3(B.X,B.Y,B.Z)>=-.25f && FVector::DistSquared(ReconstructDrapePoint(B,P,N),Target)<.0004) continue;
        TArray<TPair<double,int32>> Nearest; Nearest.Reserve(33);
        for (int32 T=0; T<Physical.Indices.Num(); T+=3)
        {
            const FVector A(Physical.Vertices[Physical.Indices[T]]),C(Physical.Vertices[Physical.Indices[T+1]]),D(Physical.Vertices[Physical.Indices[T+2]]);
            if ((C-A).Cross(D-A).SizeSquared()<1.e-8) continue;
            const double Distance=FVector::DistSquared(Target,FMath::ClosestPointOnTriangleToPoint(Target,A,C,D));
            if (Nearest.Num()==32 && Distance>=Nearest.Last().Key) continue;
            Nearest.Emplace(Distance,T);
            for (int32 K=Nearest.Num()-1; K>0 && Nearest[K].Key<Nearest[K-1].Key; --K) Swap(Nearest[K],Nearest[K-1]);
            if (Nearest.Num()>32) Nearest.Pop(EAllowShrinking::No);
        }
        bool Fitted=false;
        for (const auto& Candidate:Nearest)
        {
            for (int32 J=0; J<3; ++J) { const int32 Index=Physical.Indices[Candidate.Value+J]; P[J]=FVector(Physical.Vertices[Index]); N[J]=FVector(Normals[Index]); }
            FMeshToMeshVertData Replacement=M;
            if (!FitDrapePoint(Target,P,N,Replacement.PositionBaryCoordsAndDist,true) ||
                !FitDrapePoint(Target+FVector(Section.SoftVertices[I].TangentZ),P,N,Replacement.NormalBaryCoordsAndDist,false) ||
                !FitDrapePoint(Target+FVector(Section.SoftVertices[I].TangentX),P,N,Replacement.TangentBaryCoordsAndDist,false)) continue;
            float SkinFraction=0.f;
            for (int32 J=0; J<3; ++J)
            {
                Replacement.SourceMeshVertIndices[J]=Physical.Indices[Candidate.Value+J];
                if (MaxDistances && (*MaxDistances)[Replacement.SourceMeshVertIndices[J]]<=0.f)
                    SkinFraction+=FMath::Clamp(Replacement.PositionBaryCoordsAndDist[J],0.f,1.f);
            }
            Replacement.SourceMeshVertIndices[3]=FMath::Clamp(FMath::RoundToInt(SkinFraction*65535.f),0,65535);
            M=Replacement; Fitted=true; ++Repaired; break;
        }
        // Only vertices for which no nearby prism reproduces the authored point
        // use their existing skin. Never clamp coefficients and distort the rest mesh.
        if (!Fitted) { M.SourceMeshVertIndices[3]=0xffff; ++Fallback; }
    }
    UE_LOG(LogTemp,Display,TEXT("WITCH_DRAPE05 %s mapping_repaired=%d local_skin_fallback=%d total=%d"),*Cloth->GetName(),Repaired,Fallback,Mapping.Num());
}

// Read the installed render-to-simulation data, which is not exposed by editor Python.
// Invoked explicitly by the Witch authoring script; never starts a simulation.
void DescribeWitchDrapeMapping()
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Monsters/WitchRebuilt/SK_WitchRebuilt.SK_WitchRebuilt"));
    if (!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty()) return;
    TArray<FString> Lines;
    const auto& LOD=Mesh->GetImportedModel()->LODModels[0];
    for (int32 SectionIndex=0; SectionIndex<LOD.Sections.Num(); ++SectionIndex)
    {
        const auto& Section=LOD.Sections[SectionIndex];
        if (!Mesh->GetMeshClothingAssets().IsValidIndex(Section.CorrespondClothAssetIndex) || Section.ClothMappingDataLODs.IsEmpty()) continue;
        const auto* Cloth=Cast<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[Section.CorrespondClothAssetIndex]);
        if (!Cloth || Cloth->LodData.IsEmpty()) continue;
        const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
        // Match ClothMeshDesc's equal-face averaged normals without bringing its
        // internal Chaos spatial acceleration templates into the game module.
        TArray<FVector3f> MappingNormals; MappingNormals.Init(FVector3f::ZeroVector,Physical.Vertices.Num());
        for (int32 T=0; T<Physical.Indices.Num(); T+=3)
        {
            const int32 A=Physical.Indices[T],B=Physical.Indices[T+1],C=Physical.Indices[T+2];
            FVector3f N=FVector3f::CrossProduct(Physical.Vertices[C]-Physical.Vertices[A],Physical.Vertices[B]-Physical.Vertices[A]);
            if (N.Normalize()) { MappingNormals[A]+=N; MappingNormals[B]+=N; MappingNormals[C]+=N; }
        }
        for (auto& N:MappingNormals) if (!N.Normalize()) N=FVector3f::XAxisVector;
        const auto& Mapping=Section.ClothMappingDataLODs[0];
        float MaxBary=0,MaxOffset=0,MaxReconstructionError=0;
        int32 Outside=0,Extreme=0,Invalid=0;
        TArray<TPair<float,int32>> Ranked;
        const int32 Influences=Section.SoftVertices.IsEmpty()?1:Mapping.Num()/Section.SoftVertices.Num();
        for (int32 I=0; I<Mapping.Num(); ++I)
        {
            const auto& M=Mapping[I]; const auto& B=M.PositionBaryCoordsAndDist;
            if (M.Weight<=0.f || M.SourceMeshVertIndices[3]==0xffff) continue;
            const float Magnitude=FMath::Max3(FMath::Abs(B.X),FMath::Abs(B.Y),FMath::Abs(B.Z));
            MaxBary=FMath::Max(MaxBary,Magnitude); MaxOffset=FMath::Max(MaxOffset,FMath::Abs(B.W));
            Outside+=FMath::Min3(B.X,B.Y,B.Z)<-.01f; Extreme+=Magnitude>2.f;
            bool Valid=true; FVector3f Reconstructed=FVector3f::ZeroVector;
            for (int32 J=0; J<3; ++J)
            {
                const int32 V=M.SourceMeshVertIndices[J];
                if (!Physical.Vertices.IsValidIndex(V)) { Valid=false; break; }
                Reconstructed+=B[J]*(Physical.Vertices[V]-B.W*MappingNormals[V]);
            }
            Invalid+=!Valid;
            if (Valid && Influences>0 && Section.SoftVertices.IsValidIndex(I/Influences))
                MaxReconstructionError=FMath::Max(MaxReconstructionError,FVector3f::Distance(Reconstructed,Section.SoftVertices[I/Influences].Position));
            Ranked.Emplace(Magnitude,I);
        }
        Lines.Add(FString::Printf(TEXT("section=%d cloth=%s vertices=%d mappings=%d max_abs_bary=%.9g outside=%d over_2=%d invalid=%d max_offset_cm=%.6f reference_error_cm=%.6f"),
            SectionIndex,*Cloth->GetName(),Section.SoftVertices.Num(),Mapping.Num(),MaxBary,Outside,Extreme,Invalid,MaxOffset,MaxReconstructionError));
        Ranked.Sort([](const auto& A,const auto& B){return A.Key>B.Key;});
        for (int32 R=0; R<FMath::Min(12,Ranked.Num()); ++R)
        {
            const int32 I=Ranked[R].Value; const auto& M=Mapping[I];
            const FVector3f P=Section.SoftVertices[I/FMath::Max(1,Influences)].Position;
            Lines.Add(FString::Printf(TEXT("  vertex=%d rest=(%.4f,%.4f,%.4f) bary=(%.9g,%.9g,%.9g) offset=%.6f source=(%d,%d,%d) blend=%d weight=%.6f"),
                I/FMath::Max(1,Influences),P.X,P.Y,P.Z,M.PositionBaryCoordsAndDist.X,M.PositionBaryCoordsAndDist.Y,M.PositionBaryCoordsAndDist.Z,M.PositionBaryCoordsAndDist.W,
                M.SourceMeshVertIndices[0],M.SourceMeshVertIndices[1],M.SourceMeshVertIndices[2],M.SourceMeshVertIndices[3],M.Weight));
        }
    }
    FFileHelper::SaveStringArrayToFile(Lines,*(FPaths::ProjectSavedDir()/TEXT("WitchRebuilt-DrapeMapping.txt")));
    UE_LOG(LogTemp,Display,TEXT("WITCH_DRAPE_MAPPING wrote %d lines to Saved/WitchRebuilt-DrapeMapping.txt"),Lines.Num());
}
FAutoConsoleCommand WitchDrapeMappingCommand(TEXT("WitchRebuilt.DescribeDrapeMapping"),
    TEXT("Write the installed Witch cloth binding data; does not run a simulation."),FConsoleCommandDelegate::CreateStatic(&DescribeWitchDrapeMapping));
}

TArray<TPair<FText,FText>> UWitchRebuiltClothingAsset::GetStats() const
{
    // The engine's private override is not DLL-exported; keep editor statistics
    // available when the cloth asset is subclassed in a project module.
    TArray<TPair<FText,FText>> Stats;
    for (int32 Index=0; Index<LodData.Num(); ++Index)
    {
        const auto& Mesh=LodData[Index].PhysicalMeshData;
        Stats.Emplace(FText::Format(NSLOCTEXT("WitchDrape","Lod","LOD {0}"),FText::AsNumber(Index)),FText{});
        Stats.Emplace(NSLOCTEXT("WitchDrape","DynamicVertices","Simul Verts"),FText::AsNumber(Mesh.Vertices.Num()-Mesh.NumFixedVerts));
        Stats.Emplace(NSLOCTEXT("WitchDrape","FixedVertices","Fixed Verts"),FText::AsNumber(Mesh.NumFixedVerts));
        Stats.Emplace(NSLOCTEXT("WitchDrape","Triangles","Sim Triangles"),FText::AsNumber(Mesh.Indices.Num()/3));
        Stats.Emplace(NSLOCTEXT("WitchDrape","BoneWeights","Bone Weights"),FText::AsNumber(Mesh.MaxBoneWeights));
    }
    return Stats;
}

void UWitchRebuiltClothingAsset::InitializeSimulationFrom(UClothingAssetCommon* Extracted)
{
    AssetGuid=FGuid::NewGuid();
    LodData=MoveTemp(Extracted->LodData);
    UsedBoneNames=MoveTemp(Extracted->UsedBoneNames);
    UsedBoneIndices=MoveTemp(Extracted->UsedBoneIndices);
    ReferenceBoneIndex=Extracted->ReferenceBoneIndex;
    PhysicsAsset=Extracted->PhysicsAsset;
}

bool UWitchRebuiltClothingAsset::BindToSkeletalMesh(USkeletalMesh* InSkelMesh,int32 InMeshLodIndex,int32 InSectionIndex,int32 InAssetLodIndex)
{
    const bool Bound=Super::BindToSkeletalMesh(InSkelMesh,InMeshLodIndex,InSectionIndex,InAssetLodIndex);
    if (Bound && InMeshLodIndex==0 && InAssetLodIndex==0)
        StabilizeDrapeMapping(InSkelMesh->GetImportedModel()->LODModels[InMeshLodIndex].Sections[InSectionIndex],this);
    return Bound;
}
#endif

bool AWitchRebuiltMonster::BuildDrape(USkeletalMesh* SourceMesh)
{
#if WITH_EDITOR
    if (!SourceMesh || !SourceMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/WitchRebuilt/"))) return false;
    auto* Model=SourceMesh->GetImportedModel();
    if (!Model || Model->LODModels.IsEmpty() || !SourceMesh->GetPhysicsAsset()) return false;
    auto Section=[SourceMesh](const TCHAR* Name)
    {
        const auto& Sections=SourceMesh->GetImportedModel()->LODModels[0].Sections;
        for (int32 I=0; I<Sections.Num(); ++I)
            if (SourceMesh->GetMaterials().IsValidIndex(Sections[I].MaterialIndex) &&
                SourceMesh->GetMaterials()[Sections[I].MaterialIndex].ImportedMaterialSlotName.ToString().Contains(Name)) return I;
        return int32(INDEX_NONE);
    };
    const TCHAR* Names[]={TEXT("WitchRebuilt_LowerDrape07"),TEXT("WitchRebuilt_UpperDrape07")};
    const TCHAR* Proxies[]={TEXT("LowerSimulationProxy"),TEXT("UpperSimulationProxy")};
    const TCHAR* Renders[]={TEXT("LowerRobe"),TEXT("UpperRobe")};
    UClothingAssetCommon* Clothes[2]={nullptr,nullptr};
    for (UClothingAssetBase* Asset : SourceMesh->GetMeshClothingAssets())
        for (int32 I=0; I<2; ++I)
            if (Asset->GetName().StartsWith(Names[I])) Clothes[I]=Cast<UClothingAssetCommon>(Asset);
    if (!Clothes[0] || !Clothes[1])
    {
        if (Section(Proxies[0])==INDEX_NONE || Section(Proxies[1])==INDEX_NONE) return false;
        const auto Previous=SourceMesh->GetMeshClothingAssets();
        for (UClothingAssetBase* Old : Previous) Old->UnbindFromSkeletalMesh(SourceMesh,0,INDEX_NONE);
        SourceMesh->SetMeshClothingAssets({});
        for (auto& S : Model->LODModels[0].Sections)
        {
            auto& User=Model->LODModels[0].UserSectionsData.FindOrAdd(S.OriginalDataSectionIndex);
            User.CorrespondClothAssetIndex=INDEX_NONE;
            User.ClothingData.AssetGuid=FGuid(); User.ClothingData.AssetLodIndex=INDEX_NONE;
        }
        const auto& Ref=SourceMesh->GetRefSkeleton();
        TArray<FTransform> Frames=Ref.GetRefBonePose();
        for (int32 I=0; I<Frames.Num(); ++I)
            if (Ref.GetParentIndex(I)>=0) Frames[I]*=Frames[Ref.GetParentIndex(I)];
        auto Bone=[&](const TCHAR* Name) { return Frames[Ref.FindBoneIndex(Name)].GetLocation(); };
        auto* Collision=NewObject<UPhysicsAsset>(SourceMesh,
            MakeUniqueObjectName(SourceMesh,UPhysicsAsset::StaticClass(),TEXT("WitchRebuilt_ClothCollision04")),RF_Transactional);
        auto Capsule=[&](const TCHAR* Name,const TCHAR* EndName,float Radius)
        {
            const int32 B=Ref.FindBoneIndex(Name),E=Ref.FindBoneIndex(EndName);
            if (B==INDEX_NONE || E==INDEX_NONE) return;
            const FVector A=Frames[B].GetLocation(),End=Frames[E].GetLocation();
            const float Scale=Frames[B].GetScale3D().GetAbsMax();
            auto* Body=NewObject<USkeletalBodySetup>(Collision); Body->BoneName=Name;
            FKSphylElem Shape;
            Shape.Center=Frames[B].InverseTransformPosition((A+End)*.5);
            Shape.Rotation=FRotationMatrix::MakeFromZ(Frames[B].InverseTransformVectorNoScale(End-A)).Rotator();
            Shape.Radius=Radius/Scale; Shape.Length=FMath::Max(0.f,(End-A).Size()-Radius)/Scale;
            Body->AggGeom.SphylElems.Add(Shape); Collision->SkeletalBodySetups.Add(Body);
        };
        Capsule(TEXT("pelvis"),TEXT("spine_02"),11.f);
        Capsule(TEXT("spine_02"),TEXT("spine_05"),12.f);
        Capsule(TEXT("spine_05"),TEXT("neck_01"),11.f);
        Capsule(TEXT("upperarm_l"),TEXT("lowerarm_l"),4.8f); Capsule(TEXT("upperarm_r"),TEXT("lowerarm_r"),4.8f);
        Capsule(TEXT("lowerarm_l"),TEXT("hand_l"),4.f); Capsule(TEXT("lowerarm_r"),TEXT("hand_r"),4.f);
        Capsule(TEXT("thigh_l"),TEXT("calf_l"),9.5f); Capsule(TEXT("thigh_r"),TEXT("calf_r"),9.5f);
        Capsule(TEXT("calf_l"),TEXT("foot_l"),6.f); Capsule(TEXT("calf_r"),TEXT("foot_r"),6.f);
        Capsule(TEXT("foot_l"),TEXT("ball_l"),4.f); Capsule(TEXT("foot_r"),TEXT("ball_r"),4.f);
        Collision->UpdateBodySetupIndexMap(); Collision->SetPreviewMesh(SourceMesh,false);
        for (int32 Layer=0; Layer<2; ++Layer)
        {
            const bool Upper=Layer==1;
            FSkeletalMeshClothBuildParams Params;
            Params.AssetName=FString(Names[Layer])+TEXT("_Extract"); Params.LodIndex=0; Params.SourceSection=Section(Proxies[Layer]);
            Params.bRemoveFromMesh=true; Params.PhysicsAsset=Collision;
            auto* Extracted=Cast<UClothingAssetCommon>(NewObject<UClothingAssetFactory>()->CreateFromSkeletalMesh(SourceMesh,Params));
            if (!Extracted || Extracted->LodData.IsEmpty()) return false;
            auto* Cloth=NewObject<UWitchRebuiltClothingAsset>(SourceMesh,FName(Names[Layer]),RF_Transactional);
            Cloth->InitializeSimulationFrom(Extracted);
            auto& Lod=Cloth->LodData[0]; Lod.bUseMultipleInfluences=false; Lod.bSmoothTransition=true;
            Lod.PointWeightMaps.Reset();
            FPointWeightMap Distance(Lod.PhysicalMeshData.Vertices.Num());
            Distance.Name=Upper?TEXT("SharedWaist_LongitudinalCuffs_LooseCape07"):TEXT("WaistFixed_ClearanceHem07");
            Distance.bEnabled=true; Distance.CurrentTarget=static_cast<uint8>(EWeightMapTargetCommon::MaxDistance);
            int32 Pinned=0; float MaxDistance=0;
            for (int32 I=0; I<Distance.Num(); ++I)
            {
                const FVector V(Lod.PhysicalMeshData.Vertices[I]); float D=0;
                if (!Upper)
                {
                    const float Drop=Bone(TEXT("pelvis")).Z-V.Z;
                    D=Drop<7.f?0.f:FMath::Min(45.f,(Drop-7.f)*.62f);
                    // Shorter travel at the ground-facing edge limits sag below
                    // the authored clearance without binding the robe to feet.
                    D=FMath::Min(D,FMath::Lerp(24.f,45.f,FMath::Clamp((V.Z-12.f)/30.f,0.f,1.f)));
                }
                else
                {
                    // Pin collar, shoulder and cuff seams, freeing the sleeve
                    // underside, cape and hanging panels around the arms.
                    const bool Left=V.X>0;
                    const FVector Shoulder=Bone(Left?TEXT("upperarm_l"):TEXT("upperarm_r"));
                    const FVector Elbow=Bone(Left?TEXT("lowerarm_l"):TEXT("lowerarm_r"));
                    const FVector Hand=Bone(Left?TEXT("hand_l"):TEXT("hand_r"));
                    const FVector P1=FMath::ClosestPointOnSegment(V,Shoulder,Elbow);
                    const FVector P2=FMath::ClosestPointOnSegment(V,Elbow,Hand);
                    const FVector Axis=FVector::DistSquared(V,P1)<FVector::DistSquared(V,P2)?P1:P2;
                    const FVector ForearmDirection=(Hand-Elbow).GetSafeNormal();
                    const bool Cuff=(V-Hand).Dot(ForearmDirection)>-6.5f && FVector::Distance(V,P2)<14.f;
                    if ((FMath::Abs(V.X)<19.f && V.Z>138.f) ||
                        (V.Z>Shoulder.Z-2.f && FMath::Abs(V.X)<28.f) || Cuff) D=0;
                    else if (FMath::Abs(V.X)>22.f)
                    {
                        const float Below=Axis.Z-V.Z;
                        D=Below<1.5f?0.f:FMath::Clamp((Below-1.5f)*.65f,0.f,9.f);
                    }
                    else D=FMath::Clamp((138.f-V.Z)*.13f,0.f,7.f);
                    // Both sides of the waist seam share pelvis skinning. Fade
                    // into torso simulation above it, rather than two free hems.
                    if (FMath::Abs(V.X)<26.f)
                        D*=FMath::Clamp((V.Z-Bone(TEXT("pelvis")).Z-8.f)/12.f,0.f,1.f);
                }
                Distance[I]=D; Pinned+=D==0.f; MaxDistance=FMath::Max(MaxDistance,D);
            }
            Lod.PointWeightMaps.Add(MoveTemp(Distance));
            auto* Config=NewObject<UChaosClothConfig>(Cloth);
            Config->Density=.35f; Config->EdgeStiffnessWeighted={.98f,.98f}; Config->AreaStiffnessWeighted={.95f,.95f};
            Config->bUseBendingElements=true; Config->BendingStiffnessWeighted={.06f,.06f};
            Config->BucklingRatio=.5f; Config->BucklingStiffnessWeighted={.025f,.025f};
            Config->TetherStiffness={1.f,1.f}; Config->TetherScale={1.01f,1.01f}; Config->bUseGeodesicDistance=true;
            Config->AnimDriveStiffness=Upper?FChaosClothWeightedValue{.06f,.06f}:FChaosClothWeightedValue{.008f,.008f};
            Config->AnimDriveDamping={.1f,.1f}; Config->CollisionThickness=1.1f; Config->FrictionCoefficient=.2f;
            Config->DampingCoefficient=.035f; Config->LocalDampingCoefficient=.18f;
            // Dense point/face self collision on the old folded upper proxy was
            // the persistent spawn cost. Regular sleeves use body collisions;
            // the continuous skirt retains inexpensive sphere self repulsion.
            Config->bUseCCD=!Upper; Config->bUseSelfCollisions=false;
            Config->bUseSelfCollisionSpheres=!Upper; Config->SelfCollisionSphereRadius=.65f;
            Config->SelfCollisionSphereRadiusCullMultiplier=2.f; Config->SelfCollisionSphereStiffness=.8f;
            Config->LinearVelocityScale=FVector(.85); Config->AngularVelocityScale=.8f;
            Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(),Config);
            auto* Shared=NewObject<UChaosClothSharedSimConfig>(Cloth);
            Shared->IterationCount=4; Shared->MaxIterationCount=6; Shared->SubdivisionCount=1;
            Cloth->ClothConfigs.Add(Shared->GetClass()->GetFName(),Shared);
            Cloth->ApplyParameterMasks(true); Cloth->InvalidateAllCachedData(); SourceMesh->AddClothingAsset(Cloth); Clothes[Layer]=Cloth;
            UE_LOG(LogTemp,Display,TEXT("WITCH_DRAPE04 %s particles=%d pinned=%d max_distance_cm=%.2f"),
                Names[Layer],Lod.PhysicalMeshData.Vertices.Num(),Pinned,MaxDistance);
        }
    }
    FScopedSkeletalMeshPostEditChange Change(SourceMesh); SourceMesh->Modify();
    for (auto* Cloth : Clothes) Cloth->UnbindFromSkeletalMesh(SourceMesh,0,INDEX_NONE);
    SourceMesh->SetMeshClothingAssets({Clothes[0],Clothes[1]});
    for (int32 Layer=0; Layer<2; ++Layer)
    {
        const int32 Render=Section(Renders[Layer]);
        if (Render==INDEX_NONE || !Clothes[Layer]->BindToSkeletalMesh(SourceMesh,0,Render,0)) return false;
        auto& LOD=SourceMesh->GetImportedModel()->LODModels[0];
        auto& User=LOD.UserSectionsData.FindOrAdd(LOD.Sections[Render].OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex=Layer; User.ClothingData.AssetGuid=Clothes[Layer]->GetAssetGuid(); User.ClothingData.AssetLodIndex=0;
    }
    auto& LOD=SourceMesh->GetImportedModel()->LODModels[0];
    for (auto& S : LOD.Sections)
    {
        const bool Proxy=SourceMesh->GetMaterials()[S.MaterialIndex].ImportedMaterialSlotName.ToString().Contains(TEXT("SimulationProxy"));
        S.bDisabled=Proxy; LOD.UserSectionsData.FindOrAdd(S.OriginalDataSectionIndex).bDisabled=Proxy;
    }
    SourceMesh->InvalidateDeriveDataCacheGUID(); SourceMesh->MarkPackageDirty(); return true;
#else
    return false;
#endif
}
