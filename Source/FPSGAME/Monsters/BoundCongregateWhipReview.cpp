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

// User-requested root-fold and whip-wave diagnosis. No AI, player or saves.
int32 ReviewBoundCongregateWhipV4()
{
#if WITH_EDITOR
    const FString Dir=FPaths::ProjectDir()/TEXT("SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4");
    auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CongregateWhipV4Review"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    UClass* Type=LoadClass<ABoundCongregate>(nullptr,TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    if(!World||!Type)return 1;
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Monster=World->SpawnActor<ABoundCongregate>(Type,FVector(0,0,225),FRotator::ZeroRotator,Spawn);
    auto* Mesh=Monster->GetMesh();auto* Asset=Mesh->GetSkeletalMeshAsset();const auto& Ref=Asset->GetRefSkeleton();
    Mesh->bDisableClothSimulation=true;Mesh->bEnableUpdateRateOptimizations=false;
    Monster->GetCharacterMovement()->SetMovementMode(MOVE_Flying);Mesh->InitAnim(true);
    const auto& LOD=Asset->GetImportedModel()->LODModels[0];
    auto Reference=Ref.GetRefBonePose();
    for(int32 I=0;I<Reference.Num();++I)if(Ref.GetParentIndex(I)>=0)Reference[I]*=Reference[Ref.GetParentIndex(I)];
    TArray<FMatrix> Inverse;for(const auto& T:Reference)Inverse.Add(T.ToMatrixWithScale().Inverse());
    int32 Leak=0,OldLeak=0,Organ=0;
    for(const auto& S:LOD.Sections)
    {
        const bool IsOrgan=Asset->GetMaterials()[S.MaterialIndex].ImportedMaterialSlotName==TEXT("BC_AttackTentacle");
        for(const auto& V:S.SoftVertices)
        {
            bool Attack=false,Old=false;
            for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J])
            {const FString N=Ref.GetBoneName(S.BoneMap[V.InfluenceBones[J]]).ToString();Attack|=N.StartsWith(TEXT("attack_tentacle_"));Old|=N.StartsWith(TEXT("curl_"))||N.StartsWith(TEXT("feeler_"));}
            if(Attack&&!IsOrgan)++Leak;if(Old)++OldLeak;if(IsOrgan)++Organ;
        }
    }
    const int32 TipBone=Ref.FindBoneIndex(TEXT("attack_tentacle_56")),ProxBone=Ref.FindBoneIndex(TEXT("attack_tentacle_11")),BodyBone=Ref.FindBoneIndex(TEXT("body"));
    const float IdleEnd=1.f,WindEnd=IdleEnd+Monster->TentacleWindupSeconds,StrikeEnd=WindEnd+Monster->TentacleStrikeSeconds;
    const float WrapEnd=StrikeEnd+Monster->TentacleWrapSeconds,DragEnd=WrapEnd+1.2f,End=DragEnd+Monster->TentacleRecoverSeconds;
    constexpr float Dt=1.f/60.f;const int32 Last=FMath::CeilToInt(End/Dt);
    TArray<FTransform> Previous;double MaxStep=0,LengthError=0,TipSpeed=0,ProxSpeed=0,TipPeak=0,ProxPeak=0,WindupBack=0,ContactError=0;
    bool Finite=true;int32 Folded=0,RootTriangles=0,Captures=0;
    FString Poses=TEXT("{\"scope\":\"actual imported V4 skeletal mesh and animation proxy\",\"poses\":[");
    for(int32 Frame=0;Frame<=Last;++Frame)
    {
        const float T=Frame*Dt;float Start=0;auto State=EBoundCongregateState::Idle;
        if(T>=IdleEnd){State=EBoundCongregateState::TentacleWindup;Start=IdleEnd;}
        if(T>=WindEnd){State=EBoundCongregateState::TentacleStrike;Start=WindEnd;}
        if(T>=StrikeEnd){State=EBoundCongregateState::TentacleWrap;Start=StrikeEnd;}
        if(T>=WrapEnd){State=EBoundCongregateState::TentacleDrag;Start=WrapEnd;}
        if(T>=DragEnd){State=EBoundCongregateState::TentacleRecover;Start=DragEnd;}
        Monster->NetState.State=State;Monster->NetState.StartedAt=World->GetTimeSeconds()-(T-Start);
        Monster->NetState.TentacleAim=FVector(340,0,96);Monster->NetState.TentacleRadius=48;
        Monster->NetState.ReleasedWeight=Monster->NetState.ReleasedStrike=Monster->NetState.ReleasedWrap=1;
        ++GFrameCounter;Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();
        const auto& Pose=Mesh->GetComponentSpaceTransforms();TArray<FMatrix> Deltas;
        for(int32 B=0;B<Pose.Num();++B)
        {
            Finite&=!Pose[B].ContainsNaN();Deltas.Add(Inverse[B]*Pose[B].ToMatrixWithScale());
            if(!Ref.GetBoneName(B).ToString().StartsWith(TEXT("attack_tentacle_")))continue;
            const int32 Parent=Ref.GetParentIndex(B);
            LengthError=FMath::Max(LengthError,FMath::Abs(FVector::Distance(Pose[B].GetLocation(),Pose[Parent].GetLocation())-FVector::Distance(Reference[B].GetLocation(),Reference[Parent].GetLocation())));
            if(Previous.Num())MaxStep=FMath::Max(MaxStep,FVector::Distance(Pose[B].GetLocation(),Previous[B].GetLocation()));
        }
        const FVector Tip=Mesh->GetSocketLocation(TEXT("attack_tentacle_56"));
        if(State==EBoundCongregateState::TentacleWindup)WindupBack=FMath::Min(WindupBack,double(Tip.X-Monster->GetActorLocation().X));
        if(State==EBoundCongregateState::TentacleStrike&&Previous.Num())
        {
            const double A=FVector::Distance(Pose[TipBone].GetLocation(),Previous[TipBone].GetLocation())/Dt;
            const double B=FVector::Distance(Pose[ProxBone].GetLocation(),Previous[ProxBone].GetLocation())/Dt;
            if(A>TipSpeed){TipSpeed=A;TipPeak=T-WindEnd;}if(B>ProxSpeed){ProxSpeed=B;ProxPeak=T-WindEnd;}
            ContactError=FVector::Distance(Tip,Monster->NetState.TentacleAim);
        }
        // Detect the actual failure: triangles around the fixed attachment
        // turning inside out relative to their body's normal while breathing.
        int32 ThisFold=0,ThisRoot=0;
        for(const auto& S:LOD.Sections)
        {
            const auto Name=Asset->GetMaterials()[S.MaterialIndex].ImportedMaterialSlotName.ToString();
            if(Name!=TEXT("BC_Flesh")&&Name!=TEXT("BC_AttackTentacle"))continue;
            auto Skin=[&](const FSoftSkinVertex& V)
            {
                FVector P=FVector::ZeroVector;float Sum=0;
                for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J])
                {const float W=V.InfluenceWeights[J];P+=FVector(Deltas[S.BoneMap[V.InfluenceBones[J]]].TransformPosition(FVector(V.Position)))*W;Sum+=W;}
                return P/FMath::Max(1.f,Sum);
            };
            for(uint32 Triangle=0;Triangle<S.NumTriangles;++Triangle)
            {
                const auto& A=S.SoftVertices[LOD.IndexBuffer[S.BaseIndex+Triangle*3]-S.BaseVertexIndex];
                const auto& B=S.SoftVertices[LOD.IndexBuffer[S.BaseIndex+Triangle*3+1]-S.BaseVertexIndex];
                const auto& C=S.SoftVertices[LOD.IndexBuffer[S.BaseIndex+Triangle*3+2]-S.BaseVertexIndex];
                const FVector Center=(FVector(A.Position)+FVector(B.Position)+FVector(C.Position))/3;
                if(Center.X<52||Center.X>116||Center.Z<164||Center.Z>176||FMath::Abs(Center.Y+14)>33)continue;
                const FVector N=FVector::CrossProduct(FVector(B.Position-A.Position),FVector(C.Position-A.Position));
                if(N.SizeSquared()<.0001)continue;
                const FVector NewN=FVector::CrossProduct(Skin(B)-Skin(A),Skin(C)-Skin(A));
                ++ThisRoot;if(FVector::DotProduct(NewN,Deltas[BodyBone].TransformVector(N))<0)++ThisFold;
            }
        }
        RootTriangles=FMath::Max(RootTriangles,ThisRoot);Folded=FMath::Max(Folded,ThisFold);
        if(Captures++)Poses+=TEXT(",");
        Poses+=FString::Printf(TEXT("{\"frame\":%d,\"time\":%.6f,\"state\":%d,\"bones\":["),Frame,T,int32(State));
        for(int32 B=0;B<Pose.Num();++B)
        {
            if(B)Poses+=TEXT(",");Poses+=FString::Printf(TEXT("{\"name\":\"%s\",\"delta\":["),*Ref.GetBoneName(B).ToString());
            for(int32 R=0;R<4;++R)for(int32 C=0;C<4;++C){if(R||C)Poses+=TEXT(",");Poses+=FString::Printf(TEXT("%.9g"),Deltas[B].M[R][C]);}
            Poses+=TEXT("]}");
        }
        Poses+=TEXT("]}");Previous=Pose;
    }
    Poses+=TEXT("]}");FFileHelper::SaveStringToFile(Poses,*(Dir/TEXT("ue_attack_poses.json")));
    const FString Report=FString::Printf(TEXT("{\"mesh\":\"%s\",\"frames\":%d,\"attack_weights_outside_organ\":%d,\"legacy_weights\":%d,\"organ_vertices\":%d,\"finite\":%s,\"root_triangles\":%d,\"max_folded_root_triangles\":%d,\"max_bone_step_cm\":%.6f,\"max_bone_length_error_cm\":%.9g,\"windup_tip_back_cm\":%.4f,\"strike_tip_error_cm\":%.4f,\"proximal_peak_seconds\":%.4f,\"tip_peak_seconds\":%.4f,\"tip_peak_cm_s\":%.4f,\"gameplay_tested\":false}"),*Asset->GetPathName(),Last+1,Leak,OldLeak,Organ,Finite?TEXT("true"):TEXT("false"),RootTriangles,Folded,MaxStep,LengthError,WindupBack,ContactError,ProxPeak,TipPeak,TipSpeed);
    FFileHelper::SaveStringToFile(Report,*(Dir/TEXT("ue_deformation_review.json")));
    Monster->Destroy();World->DestroyWorld(false);
    return !Finite||Leak||OldLeak||!Organ||!RootTriangles||Folded||LengthError>.05||MaxStep>150||WindupBack>-150||ContactError>80||TipPeak<ProxPeak+.025?1:0;
#else
    return 1;
#endif
}
