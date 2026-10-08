#include "BoundCongregateRigReviewCommandlet.h"
#include "BoundCongregate.h"
#include "BoundCongregateAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "ClothingAsset.h"
#include "ClothingSimulationInstance.h"
#include "Utils/ClothingMeshUtils.h"
#include "ClothingSimulationFactory.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

int32 UBoundCongregateRigReviewCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("MovementSpeed")))
    {
        extern int32 ReviewBoundCongregateMovementSpeed();
        return ReviewBoundCongregateMovementSpeed();
    }
    if(FParse::Param(*Params,TEXT("MeleeV17")))
    {
        extern int32 ReviewBoundCongregateMeleeV17();
        return ReviewBoundCongregateMeleeV17();
    }
    if(FParse::Param(*Params,TEXT("WhipV4")))
    {
        extern int32 ReviewBoundCongregateWhipV4();
        return ReviewBoundCongregateWhipV4();
    }
    if(FParse::Param(*Params,TEXT("TentacleOnly")))
    {
        extern int32 ReviewBoundCongregateTentacle();
        return ReviewBoundCongregateTentacle();
    }
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(true).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CongregateRigReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 1;
    UClass* Type=LoadClass<ABoundCongregate>(nullptr,TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    if(!Type){World->DestroyWorld(false);return 1;}
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Ground=World->SpawnActor<AActor>(AActor::StaticClass(),FVector(0,0,-50),FRotator::ZeroRotator,Spawn);
    auto* Box=NewObject<UBoxComponent>(Ground);Ground->SetRootComponent(Box);Box->SetBoxExtent(FVector(5000,5000,50));
    Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Box->SetWorldLocation(FVector(0,0,-50));
    FString Report=TEXT("Scope: actual animation proxy, compressed clips and floor traces at 30/60/120 fps; actual cloth solver at 60 fps. Isolated world, no BeginPlay, AI, player map or saves.\n");
    int32 Failed=0;
    for(int32 Fps:{30,60,120})
    {
        auto* Monster=World->SpawnActor<ABoundCongregate>(Type,FVector(0,0,225),FRotator::ZeroRotator,Spawn);
        auto* Mesh=Monster->GetMesh();auto* Move=Monster->GetCharacterMovement();
        const bool ReviewCloth=Fps==60;
        Move->SetMovementMode(MOVE_Walking);Mesh->bEnableUpdateRateOptimizations=false;Mesh->bDisableClothSimulation=!ReviewCloth;
        Mesh->InitAnim(true);auto* Anim=Cast<UBoundCongregateAnimInstance>(Mesh->GetAnimInstance());
        if(!Anim){++Failed;Monster->Destroy();continue;}
        if(ReviewCloth)
        {
            TArray<UClothingAssetBase*> Used;Mesh->GetSkeletalMeshAsset()->GetClothingAssetsInUse(Used);
            Report+=FString::Printf(TEXT("cloth_setup assets=%d used=%d instances=%d predicted_lod=%d\n"),Mesh->GetSkeletalMeshAsset()->GetMeshClothingAssets().Num(),Used.Num(),Mesh->GetClothingSimulationInstances().Num(),Mesh->GetPredictedLODLevel());
            for(const auto& Asset:Mesh->GetSkeletalMeshAsset()->GetMeshClothingAssets())
            {
                const auto* Cloth=Cast<UClothingAssetCommon>(Asset.Get());const auto* Factory=UClothingSimulationFactory::GetClothingSimulationFactory(Asset.Get());
                Report+=FString::Printf(TEXT("cloth_asset=%s outer=%s valid=%d lods=%d mapped=%d factory=%s\n"),*Asset->GetName(),*Asset->GetOuter()->GetName(),Asset->IsValid(),Cloth?Cloth->LodData.Num():-1,Cloth&&Cloth->LodMap.Num()?Cloth->LodMap[0]:-99,*GetNameSafe(Factory));
            }
            if(const auto* Render=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering())for(const auto& LOD:Render->LODRenderData)for(const auto& S:LOD.RenderSections)
                Report+=FString::Printf(TEXT("cloth_section mat=%d disabled=%d guid=%s lod=%d index=%d mapped=%d\n"),S.MaterialIndex,S.bDisabled,*S.ClothingData.AssetGuid.ToString(),S.ClothingData.AssetLodIndex,S.CorrespondClothAssetIndex,S.HasClothingData());
        }
        const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
        TArray<FTransform> Previous;TArray<double> MaxStep,MaxAngle;MaxStep.Init(0,Ref.GetNum());MaxAngle.Init(0,Ref.GetNum());
        TArray<int32> MaxFrame;MaxFrame.Init(0,Ref.GetNum());
        const float Dt=1.f/Fps;double MaxFoot=0;int32 Hits=0;
        double ClothDeviation[4]={},ClothExcess[4]={},ClothPinnedError[4]={},ClothBackstopError[4]={};
        int32 ClothSamples[4]={},ClothWorstFrame[4]={};bool ClothFinite=true;
        for(int32 Frame=0;Frame<18*Fps;++Frame)
        {
            const float T=Frame*Dt;
            // Idle, accelerate, sustained crawl, decelerate, both turns, crawl,
            // then stop: the same transitions that previously reacquired locks.
            const float Speed=T<2?0:T<3?(T-2)*60:T<7?60:T<8?(8-T)*60:T<12?0:T<16?60:0;
            const float YawRate=T>=8&&T<10?14:T>=10&&T<12?-14:0;
            auto Rotation=Monster->GetActorRotation();Rotation.Yaw+=YawRate*Dt;Monster->SetActorRotation(Rotation);
            Move->Velocity=Monster->GetActorForwardVector()*Speed;
            Monster->SetActorLocation(Monster->GetActorLocation()+Move->Velocity*Dt);
            ++GFrameCounter;Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();
            const auto& Current=Mesh->GetComponentSpaceTransforms();
            if(Current.Num()!=Ref.GetNum()){++Failed;break;}
            if(Previous.Num()==Current.Num())for(int32 Bone=0;Bone<Current.Num();++Bone)
            {
                const double Step=FVector::Distance(Current[Bone].GetLocation(),Previous[Bone].GetLocation());
                const double Angle=FMath::RadiansToDegrees(Current[Bone].GetRotation().AngularDistance(Previous[Bone].GetRotation()));
                if(Step>MaxStep[Bone]){MaxStep[Bone]=Step;MaxFrame[Bone]=Frame;}
                MaxAngle[Bone]=FMath::Max(MaxAngle[Bone],Angle);
                if(Current[Bone].ContainsNaN())++Failed;
                if(Ref.GetBoneName(Bone).ToString().EndsWith(TEXT("_foot")))MaxFoot=FMath::Max(MaxFoot,Step);
            }
            Previous=Current;
            if(ReviewCloth)
            {
                // Run the component's real simulation instances serially. There
                // is no parallel cloth tick or scene/world tick in this fixture.
                TMap<int32,FClothSimulData> Data;
                for(auto& Simulation:Mesh->GetClothingSimulationInstances())
                {
                    Simulation.FillContextAndPrepareTick(Mesh,Dt,false);
                    Simulation.Simulate();Simulation.AppendSimulationData(Data,Mesh,nullptr);
                }
                TArray<FMatrix44f> SkinMatrices;SkinMatrices.SetNum(Current.Num());
                const auto& Inverse=Mesh->GetSkeletalMeshAsset()->GetRefBasesInvMatrix();
                for(int32 Bone=0;Bone<Current.Num();++Bone)SkinMatrices[Bone]=Inverse[Bone]*FMatrix44f(Current[Bone].ToMatrixWithScale());
                const auto& Assets=Mesh->GetSkeletalMeshAsset()->GetMeshClothingAssets();
                for(const auto& Pair:Data)
                {
                    if(Pair.Key<0||Pair.Key>=4||!Assets.IsValidIndex(Pair.Key)){ClothFinite=false;continue;}
                    const auto* Cloth=Cast<UClothingAssetCommon>(Assets[Pair.Key]);
                    if(!Cloth||Cloth->LodData.IsEmpty()){ClothFinite=false;continue;}
                    const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
                    const auto* Limits=Physical.FindWeightMap(EWeightMapTargetCommon::MaxDistance);
                    const auto* BackstopDistance=Physical.FindWeightMap(EWeightMapTargetCommon::BackstopDistance);
                    const auto* BackstopRadius=Physical.FindWeightMap(EWeightMapTargetCommon::BackstopRadius);
                    TArray<FVector3f> Skinned,Normals;
                    ClothingMeshUtils::SkinPhysicsMesh(Cloth->UsedBoneIndices,Physical,FTransform::Identity,SkinMatrices.GetData(),SkinMatrices.Num(),Skinned,Normals);
                    if(!Limits||!BackstopDistance||!BackstopRadius||Pair.Value.Positions.Num()!=Skinned.Num()){ClothFinite=false;continue;}
                    ++ClothSamples[Pair.Key];
                    for(int32 V=0;V<Skinned.Num();++V)
                    {
                        const FVector Position=Pair.Value.ComponentRelativeTransform.TransformPosition(FVector(Pair.Value.Positions[V]));
                        if(Position.ContainsNaN()){ClothFinite=false;continue;}
                        const double Difference=FVector::Distance(Position,FVector(Skinned[V]));
                        ClothDeviation[Pair.Key]=FMath::Max(ClothDeviation[Pair.Key],Difference);
                        if(Difference-(*Limits)[V]>ClothExcess[Pair.Key]){ClothExcess[Pair.Key]=Difference-(*Limits)[V];ClothWorstFrame[Pair.Key]=Frame;}
                        if((*Limits)[V]==0)ClothPinnedError[Pair.Key]=FMath::Max(ClothPinnedError[Pair.Key],Difference);
                        const FVector Center=FVector(Skinned[V])-FVector(Normals[V])*((*BackstopRadius)[V]+(*BackstopDistance)[V]);
                        ClothBackstopError[Pair.Key]=FMath::Max(ClothBackstopError[Pair.Key],(*BackstopRadius)[V]-FVector::Distance(Position,Center));
                    }
                }
            }
            FHitResult Hit;
            if(World->LineTraceSingleByChannel(Hit,FVector(0,0,100),FVector(0,0,-100),ECC_Visibility))++Hits;
        }
        const bool Pass=Hits==18*Fps&&MaxFoot<12.*60./Fps;
        if(!Pass)++Failed;
        Report+=FString::Printf(TEXT("%s fps=%d frames=%d ground_hits=%d max_foot_step_cm=%.5f\n"),Pass?TEXT("PASS"):TEXT("FAIL"),Fps,18*Fps,Hits,MaxFoot);
        for(int32 Bone=0;Bone<Ref.GetNum();++Bone)
            Report+=FString::Printf(TEXT("bone=%s max_step_cm=%.5f max_angle_deg=%.5f at_frame=%d\n"),*Ref.GetBoneName(Bone).ToString(),MaxStep[Bone],MaxAngle[Bone],MaxFrame[Bone]);
        if(ReviewCloth)for(int32 C=0;C<4;++C)
        {
            const bool ClothPass=ClothFinite&&ClothSamples[C]==18*Fps&&ClothExcess[C]<.5&&ClothPinnedError[C]<.1&&ClothBackstopError[C]<.1;
            if(!ClothPass)++Failed;
            Report+=FString::Printf(TEXT("%s cloth=%d frames=%d finite=%d max_skin_offset_cm=%.5f max_limit_excess_cm=%.5f pinned_error_cm=%.5f worst_frame=%d\n"),ClothPass?TEXT("PASS"):TEXT("FAIL"),C,ClothSamples[C],ClothFinite,ClothDeviation[C],ClothExcess[C],ClothPinnedError[C],ClothWorstFrame[C]);
            Report+=FString::Printf(TEXT("cloth=%d max_backstop_penetration_cm=%.5f\n"),C,ClothBackstopError[C]);
        }
        Monster->Destroy();
    }
    Report+=FString::Printf(TEXT("RESULT failed=%d\n"),Failed);
    FFileHelper::SaveStringToFile(Report,*(FPaths::ProjectDir()/TEXT("SourceAssets/BoundCongregateMeshy20261006/RigRepairV3/runtime_rig_review.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("CONGREGATE_RIG_REVIEW failed=%d"),Failed);return Failed?1:0;
}
