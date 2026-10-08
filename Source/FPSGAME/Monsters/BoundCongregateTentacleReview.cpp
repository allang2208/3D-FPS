#include "BoundCongregate.h"
#include "BoundCongregateAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

// Explicitly requested deformation diagnosis. No map, AI, BeginPlay or saves.
int32 ReviewBoundCongregateTentacle()
{
#if WITH_EDITOR
    const FString Directory=FPaths::ProjectDir()/TEXT("SourceAssets/BoundCongregateMeshy20261006/TentacleRepairV2");
    auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CongregateTentacleReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    UClass* Type=LoadClass<ABoundCongregate>(nullptr,TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    if(!World||!Type)return 1;
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Monster=World->SpawnActor<ABoundCongregate>(Type,FVector(0,0,225),FRotator::ZeroRotator,Spawn);
    auto* Mesh=Monster->GetMesh();auto* Asset=Mesh->GetSkeletalMeshAsset();const auto& Ref=Asset->GetRefSkeleton();
    Mesh->bDisableClothSimulation=true;Mesh->bEnableUpdateRateOptimizations=false;
    Monster->GetCharacterMovement()->SetMovementMode(MOVE_Flying);Mesh->InitAnim(true);
    auto* Anim=Cast<UBoundCongregateAnimInstance>(Mesh->GetAnimInstance());if(!Anim)return 1;
    int32 Leak=0,OrganVertices=0,OldLeak=0;
    for(const auto& Section:Asset->GetImportedModel()->LODModels[0].Sections)
    {
        const bool Organ=Asset->GetMaterials()[Section.MaterialIndex].ImportedMaterialSlotName==TEXT("BC_AttackTentacle");
        for(const auto& V:Section.SoftVertices)
        {
            bool Attack=false,Old=false;
            for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J])
            {
                const FString Name=Ref.GetBoneName(Section.BoneMap[V.InfluenceBones[J]]).ToString();
                Attack|=Name.StartsWith(TEXT("attack_tentacle_"));Old|=Name.StartsWith(TEXT("curl_"))||Name.StartsWith(TEXT("feeler_"));
            }
            if(Attack&&!Organ)++Leak;if(Old)++OldLeak;if(Organ)++OrganVertices;
        }
    }
    auto Reference=Ref.GetRefBonePose();
    for(int32 I=0;I<Reference.Num();++I)if(Ref.GetParentIndex(I)>=0)Reference[I]*=Reference[Ref.GetParentIndex(I)];
    FString Poses=TEXT("{\"scope\":\"actual UE animation instance, no gameplay\",\"poses\":[");
    double MaxLengthError=0,MaxStep=0,StrikeTipError=0,WrapTipError=0;bool Finite=true;int32 Captures=0,MaxStepFrame=0;FString MaxStepBone;
    TArray<FTransform> Previous;
    constexpr float Dt=1.f/60.f;
    // Hold the target at a representative attack range, then pull toward the
    // collision stopping distance. State data drives the production anim node.
    for(int32 Frame=0;Frame<=347;++Frame)
    {
        const float T=Frame*Dt;float Start=0;
        auto State=EBoundCongregateState::TentacleWindup;
        if(T>=.75f){State=EBoundCongregateState::TentacleStrike;Start=.75f;}
        if(T>=1.23f){State=EBoundCongregateState::TentacleWrap;Start=1.23f;}
        if(T>=1.63f){State=EBoundCongregateState::TentacleDrag;Start=1.63f;}
        if(T>=5.13f){State=EBoundCongregateState::TentacleRecover;Start=5.13f;}
        Monster->NetState.State=State;Monster->NetState.StartedAt=World->GetTimeSeconds()-(T-Start);
        const float TargetX=FMath::Max(279.f,340.f-FMath::Max(0.f,T-1.63f)*65.f);
        Monster->NetState.TentacleAim=FVector(TargetX,0,96);Monster->NetState.TentacleRadius=48;
        Monster->NetState.ReleasedWeight=Monster->NetState.ReleasedStrike=Monster->NetState.ReleasedWrap=1.f;
        ++GFrameCounter;Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();
        const auto& Current=Mesh->GetComponentSpaceTransforms();
        for(int32 I=0;I<Current.Num();++I)
        {
            Finite&=!Current[I].ContainsNaN();
            if(!Ref.GetBoneName(I).ToString().StartsWith(TEXT("attack_tentacle_")))continue;
            const int32 Parent=Ref.GetParentIndex(I);
            const double Expected=FVector::Distance(Reference[I].GetLocation(),Reference[Parent].GetLocation());
            MaxLengthError=FMath::Max(MaxLengthError,FMath::Abs(FVector::Distance(Current[I].GetLocation(),Current[Parent].GetLocation())-Expected));
            if(Previous.Num()==Current.Num())
            {
                const double Step=FVector::Distance(Current[I].GetLocation(),Previous[I].GetLocation());
                if(Step>MaxStep){MaxStep=Step;MaxStepFrame=Frame;MaxStepBone=Ref.GetBoneName(I).ToString();}
            }
        }
        if(Frame==73)StrikeTipError=FVector::Distance(Mesh->GetSocketLocation(TEXT("attack_tentacle_56")),Monster->NetState.TentacleAim);
        if(Frame==140)WrapTipError=FVector::Distance(Mesh->GetSocketLocation(TEXT("attack_tentacle_56")),Monster->NetState.TentacleAim);
        if(Frame==0||Frame==22||Frame==44||Frame==60||Frame==73||Frame==98||Frame==140||Frame==290||Frame==330||Frame==347)
        {
            if(Captures++)Poses+=TEXT(",");
            Poses+=FString::Printf(TEXT("{\"frame\":%d,\"time\":%.6f,\"state\":%d,\"bones\":["),Frame,T,int32(State));
            for(int32 I=0;I<Current.Num();++I)
            {
                if(I)Poses+=TEXT(",");
                const FMatrix Delta=Reference[I].ToMatrixWithScale().Inverse()*Current[I].ToMatrixWithScale();
                Poses+=FString::Printf(TEXT("{\"name\":\"%s\",\"delta\":["),*Ref.GetBoneName(I).ToString());
                for(int32 Row=0;Row<4;++Row)for(int32 Column=0;Column<4;++Column)
                {if(Row||Column)Poses+=TEXT(",");Poses+=FString::Printf(TEXT("%.9g"),Delta.M[Row][Column]);}
                Poses+=TEXT("]}");
            }
            Poses+=TEXT("]}");
        }
        Previous=Current;
    }
    Poses+=TEXT("]}");FFileHelper::SaveStringToFile(Poses,*(Directory/TEXT("ue_attack_poses.json")));
    const FString Report=FString::Printf(TEXT("{\"scope\":\"imported weights and actual attack animation only\",\"frames\":348,\"fps\":60,\"attack_weights_outside_organ\":%d,\"legacy_organ_weights\":%d,\"organ_vertices\":%d,\"finite\":%s,\"max_bone_length_error_cm\":%.9g,\"max_bone_step_cm\":%.9g,\"strike_tip_error_cm\":%.9g,\"wrap_tip_distance_cm\":%.9g,\"gameplay_tested\":false}"),Leak,OldLeak,OrganVertices,Finite?TEXT("true"):TEXT("false"),MaxLengthError,MaxStep,StrikeTipError,WrapTipError);
    FFileHelper::SaveStringToFile(Report,*(Directory/TEXT("ue_deformation_review.json")));
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("frame=%d bone=%s step_cm=%.6f\n"),MaxStepFrame,*MaxStepBone,MaxStep),*(Directory/TEXT("step_diagnosis.txt")));
    Monster->Destroy();World->DestroyWorld(false);
    return Leak||OldLeak||!Finite||OrganVertices==0||MaxLengthError>.05||MaxStep>31.f||StrikeTipError>60.f||WrapTipError>90.f?1:0;
#else
    return 1;
#endif
}
