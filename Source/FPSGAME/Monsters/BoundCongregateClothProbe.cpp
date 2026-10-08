// Opt-in background investigation for the October 8 cloth regression.
// Creates no game session and never saves or changes asset files.
#if WITH_EDITOR
#include "CoreMinimal.h"
#include "ClothingAsset.h"
#include "ClothingSimulationInstance.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"

namespace BoundCongregateClothProbe
{
void DescribeGarments(const TArray<FString>& Args)
{
    if(!IsRunningCommandlet()||Args.IsEmpty())return;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Args[0]);
    if(!Mesh||!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return;
    TArray<FString> Lines;const auto& Ref=Mesh->GetRefSkeleton();auto Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    for(int32 C=0;C<Mesh->GetMeshClothingAssets().Num();++C)
    {
        auto* Cloth=CastChecked<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[C]);const auto& P=Cloth->LodData[0].PhysicalMeshData;
        FBox Bounds(ForceInit);for(const auto& V:P.Vertices)Bounds+=FVector(V);
        int32 BadBones=0;
        for(int32 I=0;I<Cloth->UsedBoneNames.Num();++I)
            if(!Cloth->UsedBoneIndices.IsValidIndex(I)||Ref.FindBoneIndex(Cloth->UsedBoneNames[I])!=Cloth->UsedBoneIndices[I])++BadBones;
        Lines.Add(FString::Printf(TEXT("cloth=%d name=%s guid=%s physical=%d bounds=%s bone_index_mismatch=%d reference_bone=%d"),C,*Cloth->GetName(),*Cloth->GetAssetGuid().ToString(),P.Vertices.Num(),*Bounds.ToString(),BadBones,Cloth->ReferenceBoneIndex));
        if(Cloth->PhysicsAsset)for(const auto& Body:Cloth->PhysicsAsset->SkeletalBodySetups)
        {
            const int32 B=Ref.FindBoneIndex(Body->BoneName);if(B==INDEX_NONE)continue;
            for(const auto& Shape:Body->AggGeom.SphylElems)
                Lines.Add(FString::Printf(TEXT(" capsule bone=%s scale=%s radius=%.6f length=%.6f local_center=%s mesh_center=%s"),*Body->BoneName.ToString(),*Frames[B].GetScale3D().ToString(),Shape.Radius,Shape.Length,*Shape.Center.ToString(),*Frames[B].TransformPosition(Shape.Center).ToString()));
        }
    }
    for(const auto& Section:Mesh->GetImportedModel()->LODModels[0].Sections)
    {
        const FString Name=Mesh->GetMaterials()[Section.MaterialIndex].ImportedMaterialSlotName.ToString();
        if(!Mesh->GetMeshClothingAssets().IsValidIndex(Section.CorrespondClothAssetIndex))continue;
        const auto* Cloth=CastChecked<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[Section.CorrespondClothAssetIndex]);const auto& P=Cloth->LodData[0].PhysicalMeshData;
        TArray<FVector3f> N;N.Init(FVector3f::ZeroVector,P.Vertices.Num());
        for(int32 T=0;T<P.Indices.Num();T+=3)
        {const int32 A=P.Indices[T],B=P.Indices[T+1],D=P.Indices[T+2];FVector3f Normal=FVector3f::CrossProduct(P.Vertices[D]-P.Vertices[A],P.Vertices[B]-P.Vertices[A]);if(Normal.Normalize()){N[A]+=Normal;N[B]+=Normal;N[D]+=Normal;}}
        for(auto& Normal:N)if(!Normal.Normalize())Normal=FVector3f::XAxisVector;
        float MaxBary=0,MaxError=0,MaxOffset=0;int32 Invalid=0,Active=0;FBox Bounds(ForceInit);
        for(const auto& V:Section.SoftVertices)Bounds+=FVector(V.Position);
        if(!Section.ClothMappingDataLODs.IsEmpty())for(int32 I=0;I<Section.ClothMappingDataLODs[0].Num();++I)
        {
            const auto& M=Section.ClothMappingDataLODs[0][I];if(M.SourceMeshVertIndices[3]==0xffff)continue;++Active;
            const auto& B=M.PositionBaryCoordsAndDist;MaxBary=FMath::Max(MaxBary,FMath::Max3(FMath::Abs(B.X),FMath::Abs(B.Y),FMath::Abs(B.Z)));MaxOffset=FMath::Max(MaxOffset,FMath::Abs(B.W));
            FVector3f Reconstructed=FVector3f::ZeroVector;bool Valid=Section.SoftVertices.IsValidIndex(I);
            for(int32 J=0;J<3;++J){const int32 V=M.SourceMeshVertIndices[J];if(!P.Vertices.IsValidIndex(V)){Valid=false;break;}Reconstructed+=B[J]*(P.Vertices[V]-B.W*N[V]);}
            if(Valid)MaxError=FMath::Max(MaxError,FVector3f::Distance(Reconstructed,Section.SoftVertices[I].Position));else ++Invalid;
        }
        Lines.Add(FString::Printf(TEXT("section=%s cloth_index=%d guid_matches=%d bounds=%s active_mapping=%d invalid=%d max_bary=%.9g max_offset_cm=%.6f rest_error_cm=%.6f"),*Name,Section.CorrespondClothAssetIndex,Section.ClothingData.AssetGuid==Cloth->GetAssetGuid(),*Bounds.ToString(),Active,Invalid,MaxBary,MaxOffset,MaxError));
    }
    const FString File=Args.Num()>1?Args[1]:FPaths::ProjectSavedDir()/TEXT("BoundCongregate-Garments.txt");
    FFileHelper::SaveStringArrayToFile(Lines,*File);UE_LOG(LogTemp,Display,TEXT("BC_GARMENT_DATA saved %s"),*File);
}
FAutoConsoleCommand DescribeCommand(TEXT("BoundCongregate.DescribeGarments"),TEXT("Read installed bone/collision/capture data without simulating or saving assets."),FConsoleCommandWithArgsDelegate::CreateStatic(&DescribeGarments));
void Run(const TArray<FString>& Args)
{
    if (!IsRunningCommandlet()) return;
    const FString Path=Args.Num()?Args[0]:TEXT("/Game/Monsters/BoundCongregate/FullWhipV10/SK_BoundCongregate_FullWhipV10");
    USkeletalMesh* Mesh=LoadObject<USkeletalMesh>(nullptr,*Path);
    if (!Mesh) { UE_LOG(LogTemp,Error,TEXT("BC_CLOTH_PROBE missing mesh %s"),*Path); return; }
    struct FSaved
    {
        UClothingAssetCommon* Cloth; UChaosClothConfig* Config; UPhysicsAsset* Physics;
        bool CCD,Self; int32 Vertices,Dynamic,Convexes;
    };
    TArray<FSaved> Saved;TArray<FString> Lines;
    Lines.Add(TEXT("mesh,variant,cloths,vertices,dynamic,convexes,init_ms,prepare_mean_ms,simulate_mean_ms,simulate_max_ms,iterations,substeps"));
    int32 Vertices=0,Dynamic=0,Convexes=0;
    for (const auto& Base:Mesh->GetMeshClothingAssets())
    {
        auto* Cloth=CastChecked<UClothingAssetCommon>(Base);
        auto* Config=Cloth->GetClothConfig<UChaosClothConfig>();
        const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
        int32 Hulls=0;
        if(Cloth->PhysicsAsset)for(const auto& Body:Cloth->PhysicsAsset->SkeletalBodySetups)Hulls+=Body->AggGeom.ConvexElems.Num();
        Saved.Add({Cloth,Config,Cloth->PhysicsAsset,Config->bUseCCD,Config->bUseSelfCollisionSpheres,Physical.Vertices.Num(),Physical.Vertices.Num()-Physical.NumFixedVerts,Hulls});
        Vertices+=Physical.Vertices.Num();Dynamic+=Physical.Vertices.Num()-Physical.NumFixedVerts;Convexes+=Hulls;
        UE_LOG(LogTemp,Display,TEXT("BC_CLOTH_PROBE asset=%s verts=%d convex=%d ccd=%d self=%d"),*Cloth->GetName(),Physical.Vertices.Num(),Hulls,Config->bUseCCD,Config->bUseSelfCollisionSpheres);
    }
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(true).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("BoundCongregateClothProbe"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    const TArray<FString> Variants={TEXT("original"),TEXT("no_ccd"),TEXT("no_self"),TEXT("no_body_collision")};
    for(const FString& Variant:Variants)
    {
        for(auto& S:Saved)
        {
            S.Config->bUseCCD=Variant==TEXT("no_ccd")?false:S.CCD;
            S.Config->bUseSelfCollisionSpheres=Variant==TEXT("no_self")?false:S.Self;
            S.Cloth->PhysicsAsset=Variant==TEXT("no_body_collision")?nullptr:S.Physics;
        }
        auto* Owner=World->SpawnActor<AActor>();
        auto* Component=NewObject<USkeletalMeshComponent>(Owner,NAME_None,RF_Transient);
        Owner->SetRootComponent(Component);Owner->AddInstanceComponent(Component);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        Component->SetSkeletalMeshAsset(Mesh);
        Component->SetUpdateClothInEditor(true);
        const double InitStart=FPlatformTime::Seconds();
        Component->RegisterComponentWithWorld(World);
        Component->RefreshBoneTransforms();
        const double InitMs=(FPlatformTime::Seconds()-InitStart)*1000.;
        double Prepare=0,Simulate=0,Maximum=0;int32 Iterations=0,Substeps=0,Cloths=0;
        for(int32 Frame=0;Frame<24;++Frame)
        {
            // A bounded, identical motion keeps continuous collisions active.
            Component->SetWorldLocation(FVector(Frame*.5,0,2.*FMath::Sin(Frame*.12)));
            const double Start=FPlatformTime::Seconds();
            for(auto& Instance:Component->GetClothingSimulationInstances())Instance.FillContextAndPrepareTick(Component,1.f/60.f,false);
            const double Prepared=FPlatformTime::Seconds();
            for(auto& Instance:Component->GetClothingSimulationInstances())Instance.Simulate();
            const double End=FPlatformTime::Seconds();
            if(Frame>=6){Prepare+=(Prepared-Start)*1000.;Simulate+=(End-Prepared)*1000.;Maximum=FMath::Max(Maximum,(End-Prepared)*1000.);}
        }
        Dynamic=0;
        for(auto& Instance:Component->GetClothingSimulationInstances())
        {
            const auto* Sim=Instance.GetClothingSimulation();Cloths+=Sim->GetNumCloths();
            Dynamic+=Sim->GetNumDynamicParticles();
            Iterations=FMath::Max(Iterations,Sim->GetNumIterations());Substeps=FMath::Max(Substeps,Sim->GetNumSubsteps());
        }
        if(!Cloths)UE_LOG(LogTemp,Error,TEXT("BC_CLOTH_PROBE invalid: no cloth instances."));
        const FString Line=FString::Printf(TEXT("%s,%s,%d,%d,%d,%d,%.3f,%.3f,%.3f,%.3f,%d,%d"),*Mesh->GetName(),*Variant,Cloths,Vertices,Dynamic,Variant==TEXT("no_body_collision")?0:Convexes,InitMs,Prepare/18.,Simulate/18.,Maximum,Iterations,Substeps);
        Lines.Add(Line);UE_LOG(LogTemp,Display,TEXT("BC_CLOTH_PROBE %s"),*Line);
        Owner->Destroy();
    }
    for(auto& S:Saved){S.Config->bUseCCD=S.CCD;S.Config->bUseSelfCollisionSpheres=S.Self;S.Cloth->PhysicsAsset=S.Physics;}
    World->DestroyWorld(false);
    const FString File=FPaths::ProjectSavedDir()/TEXT("Profiling/BoundCongregate")/(Mesh->GetName()+TEXT("-cloth.csv"));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);FFileHelper::SaveStringArrayToFile(Lines,*File);
}
FAutoConsoleCommand Command(TEXT("BoundCongregate.ProfileCloth"),TEXT("Commandlet-only isolated Chaos cloth CPU diagnosis. Optional mesh path. Does not save assets."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
