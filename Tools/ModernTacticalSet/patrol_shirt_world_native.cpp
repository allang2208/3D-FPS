#include "RefitShoulderCommandlet.h"
#include "AssetCompilingManager.h"
#include "Engine/SkeletalMesh.h"
#include "Interfaces/ITargetPlatformManagerModule.h"
#include "LODUtilities.h"
#include "MeshDescription.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Modules/ModuleManager.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "SkeletalMeshAttributes.h"
#include "UObject/SavePackage.h"

IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, ShoulderFit, "ShoulderFit");

namespace {
constexpr int32 Angles=96, Levels=37;
const TCHAR* Names[]={TEXT("pelvis"),TEXT("spine_01"),TEXT("spine_02"),TEXT("spine_03"),TEXT("thigh_l"),TEXT("thigh_r"),TEXT("thigh_twist_01_l"),TEXT("thigh_twist_01_r"),
    TEXT("thigh_fwd_l"), TEXT("thigh_fwd_r"), TEXT("thigh_bck_l"), TEXT("thigh_bck_r"), TEXT("thigh_in_l"), TEXT("thigh_in_r"), TEXT("thigh_out_l"), TEXT("thigh_out_r"), TEXT("thigh_fwd_lwr_l"), TEXT("thigh_fwd_lwr_r"), TEXT("thigh_bck_lwr_l"), TEXT("thigh_bck_lwr_r"), TEXT("thigh_twistCor_01_l"), TEXT("thigh_twistCor_01_r"), TEXT("thigh_twistCor_02_l"), TEXT("thigh_twistCor_02_r")};
struct FGrid {
    int32 Channels=10;
    TArray<float> Values;
    float Sample(const FVector3f P,int32 Channel) const {
        const float Angle=FMath::Atan2(P.Y-.8f,P.X);
        const float T=(Angle<0?Angle+2*PI:Angle)*Angles/(2*PI);
        const int32 TI=FMath::FloorToInt(T);
        const float H=FMath::Clamp((P.Z-92.f)*2,0.f,float(Levels-1));
        const int32 HI=FMath::Min(FMath::FloorToInt(H),Levels-2);
        const auto At=[&](int32 Z,int32 A){return Values[(Z*Angles+A%Angles)*Channels+Channel];};
        return FMath::Lerp(FMath::Lerp(At(HI,TI),At(HI,TI+1),T-TI),FMath::Lerp(At(HI+1,TI),At(HI+1,TI+1),T-TI),H-HI);
    }
    FVector3f Deformed(FVector3f P) const {
        const FVector3f Radial(P.X,P.Y-.8f,0);
        return P+Radial.GetSafeNormal()*Sample(P,0);
    }
};
int Fit(FMeshDescription& Description,const FGrid& Grid,const FReferenceSkeleton& Skeleton) {
    FSkeletalMeshAttributes Attr(Description);
    auto Position=Attr.GetVertexPositions();
    auto Normals=Attr.GetVertexInstanceNormals();
    auto Tangents=Attr.GetVertexInstanceTangents();
    auto Weights=Attr.GetVertexSkinWeights();
    auto Slots=Attr.GetPolygonGroupMaterialSlotNames();
    TSet<FPolygonGroupID> Fabric;
    for(auto Group:Description.PolygonGroups().GetElementIDs())
        if(Slots[Group].ToString().StartsWith(TEXT("PS_"))) Fabric.Add(Group);
    // GeometryScript can number section groups before setting their material
    // slot names. The sewn garment occupies the first seven slots in the base.
    if(Fabric.IsEmpty()) for(auto Group:Description.PolygonGroups().GetElementIDs())
        if(Group.GetValue()<7) Fabric.Add(Group);
    int32 BoneIds[UE_ARRAY_COUNT(Names)];
    for(int32 I=0;I<Grid.Channels-2;++I) BoneIds[I]=Skeleton.FindBoneIndex(Names[I]);
    int32 Changed=0;
    for(auto V:Description.Vertices().GetElementIDs()) {
        const FVector3f P=Position[V];
        if(P.Z<91.f || P.Z>=110.f || FMath::Abs(P.X)>21.f) continue;
        const auto Neighbors=Description.GetVertexConnectedTriangles(V);
        if(Neighbors.IsEmpty()||!Fabric.Contains(Description.GetTrianglePolygonGroup(Neighbors[0]))) continue;
        const FVector3f New=Grid.Deformed(P);
        const float Amount=Grid.Sample(P,1);
        if(!New.Equals(P,0.000005f)) {
            for(auto Corner:Description.GetVertexVertexInstanceIDs(V)) {
                const FVector3f Normal=Normals[Corner];
                const FVector3f T=Tangents[Corner];
                if(Normal.IsNearlyZero() || T.IsNearlyZero())continue;
                const FVector3f B=FVector3f::CrossProduct(Normal,T).GetSafeNormal();
                const FVector3f A1=Grid.Deformed(P+T*.025f)-Grid.Deformed(P-T*.025f);
                const FVector3f A2=Grid.Deformed(P+B*.025f)-Grid.Deformed(P-B*.025f);
                Tangents[Corner]=A1.GetSafeNormal();Normals[Corner]=FVector3f::CrossProduct(A1,A2).GetSafeNormal();
            }
            Position[V]=New;
        }
        if(Amount>.0001f && Weights.IsValid()) {
            using namespace UE::AnimationCore;
            TMap<int32,float> Mix;
            for(auto W:Weights.Get(V)) Mix.Add(W.GetBoneIndex(),(1-Amount)*W.GetWeight());
            for(int32 I=0;I<Grid.Channels-2;++I) if(BoneIds[I]!=INDEX_NONE)
                Mix.FindOrAdd(BoneIds[I])+=Amount*Grid.Sample(P,I+2);
            TArray<FBoneWeight> Result;
            for(auto Pair:Mix) if(Pair.Value>.0001f)
                Result.Emplace(static_cast<FBoneIndexType>(Pair.Key),FMath::Clamp(Pair.Value,0.f,1.f));
            Weights.Set(V,Result,FBoneWeightsSettings().SetMaxWeightCount(8));
        }
        ++Changed;
    }
    return Changed;
}
}

URefitShoulderCommandlet::URefitShoulderCommandlet(){IsClient=false;IsServer=false;IsEditor=true;LogToConsole=true;}
int32 URefitShoulderCommandlet::Main(const FString& Params) {
    FString Work,List;
    if(!FParse::Value(*Params,TEXT("Work="),Work)||!FParse::Value(*Params,TEXT("List="),List)) return 2;
    TArray<FString> Lines;
    if(!FFileHelper::LoadFileToStringArray(Lines,*List)) return 3;
    for(const auto& Line:Lines) {
        TArray<FString> Fields;Line.ParseIntoArray(Fields,TEXT("|"),true);
        if(Fields.Num()!=3) return 4;
        const FString& Base=Fields[0];const FString& Dest=Fields[1];const FString& Key=Fields[2];
        const FString Prefix=TEXT("/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/PatrolShirtR2/Wear/");
        if(!Base.StartsWith(Prefix)||!Dest.StartsWith(Prefix)||Base==Dest||Key.Len()!=16) return 5;
        const FString Filename=FPackageName::LongPackageNameToFilename(Dest,FPackageName::GetAssetPackageExtension());
        TArray<uint8> Bytes;
        if(!FFileHelper::LoadFileToArray(Bytes,*(Work/TEXT("Fits")/(Key+TEXT(".bin"))))) return 6;
        FGrid Grid;
        const int32 Plane=sizeof(float)*Levels*Angles;
        Grid.Channels=Bytes.Num()/Plane;
        if(Bytes.Num()!=Plane*Grid.Channels || (Grid.Channels!=10 && Grid.Channels!=UE_ARRAY_COUNT(Names)+2))return 6;
        Grid.Values.SetNumUninitialized(Grid.Channels*Levels*Angles);
        FMemory::Memcpy(Grid.Values.GetData(),Bytes.GetData(),Bytes.Num());
        USkeletalMesh* Donor=LoadObject<USkeletalMesh>(nullptr,*Base);
        if(!Donor) return 7;
        FAssetCompilingManager::Get().FinishAllCompilation();
        const FString Name=FPackageName::GetLongPackageAssetName(Dest);
        const bool Exists=FPaths::FileExists(Filename);
        UPackage* Package=Exists ? LoadPackage(nullptr,*Dest,LOAD_None) : CreatePackage(*Dest);
        if(!Package)return 8;
        if(Exists)Package->FullyLoad();
        USkeletalMesh* Mesh=Exists ? LoadObject<USkeletalMesh>(Package,*Name) : DuplicateObject<USkeletalMesh>(Donor,Package,*Name);
        if(!Mesh)return 8;
        Mesh->SetFlags(RF_Public|RF_Standalone);
        if(Exists && FParse::Param(*Params,TEXT("RestoreRigDependencies"))) {
            // All sewn LODs were already saved. Resolve the native post-
            // process class in the FullBodyIK host before writing the package.
            Mesh->SetPostProcessAnimBlueprint(Donor->GetPostProcessAnimBlueprint());
        } else {
            const auto* SourceDescription=Donor->GetMeshDescription(0);
            if(!SourceDescription)return 8;
            auto* Desc=Exists ? Mesh->CreateMeshDescription(0,FMeshDescription(*SourceDescription)) : Mesh->GetMeshDescription(0);
            if(!Desc || Fit(*Desc,Grid,Mesh->GetRefSkeleton())==0) return 8;
            USkeletalMesh::FCommitMeshDescriptionParams Commit;Commit.bForceUpdate=true;
            if(!Mesh->CommitMeshDescription(0,Commit)) return 9;
            Mesh->InvalidateDeriveDataCacheGUID();
            Mesh->Build();
            FAssetCompilingManager::Get().FinishAllCompilation();
            if(!FLODUtilities::RegenerateLOD(Mesh,GetTargetPlatformManagerRef().GetRunningTargetPlatform(),3,true,false))return 10;
        }
        FAssetCompilingManager::Get().FinishAllCompilation();
        const auto* Lod=Mesh->GetResourceForRendering();
        if(!Lod || Lod->LODRenderData.Num()!=3) return 11;
        TArray<FString> Counts;
        for(const auto& Level:Lod->LODRenderData) {
            int32 Triangles=0;for(const auto& Section:Level.RenderSections)Triangles+=Section.NumTriangles;
            Counts.Add(FString::FromInt(Triangles));
        }
        FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;
        if(!UPackage::SavePackage(Package,Mesh,*Filename,Args))return 12;
        if(!FFileHelper::SaveStringToFile(FString::Join(Counts,TEXT(" ")),*(Work/TEXT("Fits")/(Key+TEXT(".saved")))))return 13;
        UE_LOG(LogTemp,Display,TEXT("PATROL_WAIST_SAVED %s %s"),*Dest,*FString::Join(Counts,TEXT(" ")));
        Mesh->ClearFlags(RF_Standalone);Mesh=nullptr;Package=nullptr;Donor=nullptr;
        CollectGarbage(RF_NoFlags);
    }
    return 0;
}
