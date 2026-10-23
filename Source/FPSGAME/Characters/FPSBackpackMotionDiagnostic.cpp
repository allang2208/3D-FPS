#if WITH_EDITOR
#include "FPSBackpackMotionComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

int32 RunBackpackMotionDiagnostic(const FString& Params)
{
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config))return 2;
    const bool OtherPacks=FParse::Param(*Params,TEXT("OtherPacks"));
    TSharedPtr<FJsonObject> Candidates;
    if(OtherPacks && (!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()/TEXT("SourceAssets/BackpackMotion20261022/response_profiles_r2.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Candidates)))return 2;
    TSharedPtr<FJsonObject> Baseline;
    if(OtherPacks && (!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()/TEXT("SourceAssets/BackpackMotion20261022/response_before_r2.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Baseline)))return 2;
    const TArray<FString> Items=OtherPacks
        ? TArray<FString>{TEXT("ue_portable_backpack"),TEXT("ue_mountain_backpack"),TEXT("ue_expedition_backpack")}
        : TArray<FString>{TEXT("ue_simple_sling_bag")};
    auto* BodyAsset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    if(!BodyAsset)return 2;
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).RequiresHitProxies(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("BackpackMotionDiagnostic"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;
    for(const FString& Item:Items)
    {
    const auto Outfit=Config->GetObjectField(TEXT("outfits"))->GetObjectField(Item);
    auto* StrapAsset=LoadObject<USkeletalMesh>(nullptr,*Outfit->GetStringField(TEXT("world_mesh")));
    if(!StrapAsset){World->DestroyWorld(false);return 2;}
    const TArray<int32> Rates=OtherPacks?TArray<int32>{30,60}:TArray<int32>{60};
    for(int32 Fps:Rates)for(const FName Family:{FName("Unarmed"),FName("Rifle")})
    for(int32 Scenario=0;Scenario<(OtherPacks?3:2);++Scenario)for(bool Revised:{false,true})
    {
        const bool Sprint=Scenario==1;
        auto* Pawn=World->SpawnActor<ACharacter>();auto* Body=Pawn->GetMesh();
        Body->SetSkeletalMeshAsset(BodyAsset);Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);
        Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
        auto* Anim=Cast<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());if(!Anim)return 2;
        const auto& Scale=Config->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
        for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
            if(FString(*Pair.Key).StartsWith(TEXT("Unarmed."))||FString(*Pair.Key).StartsWith(TEXT("Rifle."))||FString(*Pair.Key).StartsWith(TEXT("Crouch.")))
                if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Anim->Clips.Add(FName(*Pair.Key),Clip);
        Anim->BodyState.Family=Family;Anim->BodyState.bSprinting=Sprint;Anim->Speed=Sprint?800.f:450.f;
        Anim->InitializeAnimation();
        auto* Strap=NewObject<USkeletalMeshComponent>(Pawn);Pawn->AddInstanceComponent(Strap);
        Strap->SetSkeletalMeshAsset(StrapAsset);Strap->SetupAttachment(Body);Strap->RegisterComponent();Strap->SetLeaderPoseComponent(Body);
        auto* Motion=NewObject<UFPSBackpackMotionComponent>(Pawn);Pawn->AddInstanceComponent(Motion);Motion->RegisterComponent();
        auto Values=MakeShared<FJsonObject>(*Outfit->GetObjectField(TEXT("backpack_motion")));
        if(OtherPacks)
        {
            if(Revised)for(const auto& Pair:Candidates->GetObjectField(Item)->Values)Values->SetField(FString(*Pair.Key),Pair.Value);
            else Values=MakeShared<FJsonObject>(*Baseline->GetObjectField(Item));
        }
        else
        {
            Values->SetNumberField(TEXT("frequency_hz"),Revised?3.:3.8);Values->SetNumberField(TEXT("damping"),Revised?.78:.9);
            Values->SetNumberField(TEXT("max_angle_degrees"),Revised?3.2:2.4);Values->SetNumberField(TEXT("max_bounce_cm"),Revised?.5:.3);
            Values->SetNumberField(TEXT("response_scale"),Revised?3.:1.);
        }
        auto Setup=MakeShared<FJsonObject>(*Outfit);Setup->SetObjectField(TEXT("backpack_motion"),Values);
        if(!OtherPacks&&!Revised){Setup->RemoveField(TEXT("hanging_pack"));Setup->RemoveField(TEXT("hanging_pack_by_shirt"));}
        Motion->Configure(Body,Strap,Setup);
        UStaticMeshComponent* Pouch=nullptr;FTransform Rest;
        if(Outfit->HasField(TEXT("rigid_pack")))
        {
            const auto Rigid=Outfit->GetObjectField(TEXT("rigid_pack"));
            auto* PouchAsset=LoadObject<UStaticMesh>(nullptr,*Rigid->GetStringField(TEXT("mesh")));
            if(!PouchAsset){World->DestroyWorld(false);return 2;}
            Pouch=NewObject<UStaticMeshComponent>(Pawn);Pawn->AddInstanceComponent(Pouch);Pouch->SetStaticMesh(PouchAsset);
            Pouch->SetupAttachment(Body,TEXT("spine_03"));Pouch->RegisterComponent();
            const auto& L=Rigid->GetArrayField(TEXT("location"));const auto& Q=Rigid->GetArrayField(TEXT("rotation_quat"));
            Motion->AttachRigidBody(Pouch,FTransform(FQuat(Q[0]->AsNumber(),Q[1]->AsNumber(),Q[2]->AsNumber(),Q[3]->AsNumber()),FVector(L[0]->AsNumber(),L[1]->AsNumber(),L[2]->AsNumber())));
            Rest=Pouch->GetRelativeTransform();
        }
        double PeakAngle=0,PeakRigidAngle=0,PeakRigidOffset=0,PeakVertex=0,ForwardAdvance=0;
        FBox Torso(ForceInit),CenterTravel(ForceInit);FVector Location=FVector::ZeroVector;
        const float Dt=1.f/Fps;const int32 Frames=(Scenario==2?6:4)*Fps;
        for(int32 Frame=0;Frame<Frames;++Frame)
        {
            const float Time=Frame*Dt;
            float Speed=Sprint?800.f:450.f,Heading=0.f;
            if(Scenario==2)
            {
                Speed*=FMath::Clamp(Time/.5f,0.f,1.f)*FMath::Clamp((4.f-Time)/.5f,0.f,1.f);
                Heading=FMath::Clamp((Time-2.f)/.75f,0.f,1.f)*90.f;
            }
            Anim->Speed=Speed;
            const FQuat HeadingRotation(FVector::UpVector,FMath::DegreesToRadians(Heading));
            const FVector Velocity=HeadingRotation.RotateVector(FVector(0,Speed,0));Location+=Velocity*Dt;
            Pawn->SetActorLocationAndRotation(Location,HeadingRotation);Pawn->GetCharacterMovement()->Velocity=Velocity;
            Anim->Clock=Frame*Dt;Body->TickAnimation(Dt,false);Body->RefreshBoneTransforms();
            Motion->TickComponent(Dt,LEVELTICK_All,nullptr);
            if(Frame>Fps)
            {
                PeakAngle=FMath::Max(PeakAngle,Motion->Angles.GetAbsMax());
                if(Pouch)
                {
                    PeakRigidAngle=FMath::Max(PeakRigidAngle,double(FMath::RadiansToDegrees(Rest.GetRotation().AngularDistance(Pouch->GetRelativeRotation().Quaternion()))));
                    PeakRigidOffset=FMath::Max(PeakRigidOffset,FVector::Distance(Rest.GetLocation(),Pouch->GetRelativeLocation()));
                }
                // Evaluate exactly the current material field delivered to the
                // render component, in torso-local centimetres. The eight corners
                // bound the affine full-weight field; strap weight is in [0,1].
                const FTransform TorsoFrame=Motion->InverseBind*Body->GetBoneTransform(Motion->Spine);
                const auto& Data=Strap->GetCustomPrimitiveData().Data;
                if(Data.Num()<30){World->DestroyWorld(false);return 2;}
                const FVector Pivot(Data[0],Data[1],Data[2]),X(Data[3],Data[4],Data[5]),Y(Data[6],Data[7],Data[8]),Z(Data[9],Data[10],Data[11]),Shift(Data[12],Data[13],Data[14]);
                for(int32 I=0;I<9;++I)
                {
                    const FVector Point=I==8?(Motion->BoundsMin+Motion->BoundsMax)*.5:
                        FVector((I&1)?Motion->BoundsMax.X:Motion->BoundsMin.X,(I&2)?Motion->BoundsMax.Y:Motion->BoundsMin.Y,(I&4)?Motion->BoundsMax.Z:Motion->BoundsMin.Z);
                    const FVector Q=TorsoFrame.TransformPosition(Point)-Pivot;
                    const FVector Delta=TorsoFrame.InverseTransformVectorNoScale(FVector(FVector::DotProduct(X,Q),FVector::DotProduct(Y,Q),FVector::DotProduct(Z,Q))+Shift);
                    PeakVertex=FMath::Max(PeakVertex,Delta.Size());ForwardAdvance=FMath::Max(ForwardAdvance,Delta.Y);
                    if(I==8)CenterTravel+=Delta;
                }
                Torso+=Body->GetBoneTransform(Motion->Spine).GetLocation()-Pawn->GetActorLocation();
            }
        }
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Family.ToString());Row->SetBoolField(TEXT("sprint"),Sprint);
        Row->SetStringField(TEXT("item"),Item);Row->SetNumberField(TEXT("fps"),Fps);
        Row->SetStringField(TEXT("presentation_mode"),Motion->Hanging.Enabled?TEXT("gravity_contact"):TEXT("bounded_inertia"));
        Row->SetStringField(TEXT("scenario"),Scenario==2?TEXT("turn_stop"):Sprint?TEXT("sprint"):TEXT("walk"));
        Row->SetBoolField(TEXT("revised"),Revised);Row->SetBoolField(TEXT("tick_enabled"),Motion->IsComponentTickEnabled());
        Row->SetNumberField(TEXT("peak_spring_angle_deg"),PeakAngle);Row->SetNumberField(TEXT("peak_rigid_angle_deg"),PeakRigidAngle);
        Row->SetNumberField(TEXT("peak_rigid_relative_offset_cm"),PeakRigidOffset);Row->SetStringField(TEXT("torso_range_cm"),Torso.GetSize().ToString());
        Row->SetStringField(TEXT("center_travel_range_cm"),CenterTravel.GetSize().ToString());
        Row->SetNumberField(TEXT("peak_full_weight_wpo_cm"),PeakVertex);Row->SetNumberField(TEXT("max_forward_advance_cm"),ForwardAdvance);
        Row->SetNumberField(TEXT("final_axis_angle_deg"),Motion->Angles.GetAbsMax());Row->SetNumberField(TEXT("final_offset_cm"),Motion->Offset.Size());
        Row->SetNumberField(TEXT("strap_primitive_data_floats"),Strap->GetCustomPrimitiveData().Data.Num());Rows.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("BACKPACK_MOTION %s %s fps=%d scenario=%d revised=%d spring=%.3f wpo=%.3f"),*Item,*Family.ToString(),Fps,Scenario,Revised,PeakAngle,PeakVertex);
        Motion->Clear();Pawn->Destroy();
    }
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("cases"),Rows);
    Report->SetStringField(TEXT("scope"),TEXT("Native full-body animation graph and backpack component, isolated ACharacter, manual pose/tick stepping; current material field output, no gameplay/profile subsystem, no rendered appearance acceptance"));
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    const auto Dir=FPaths::ProjectSavedDir()/(OtherPacks?TEXT("BackpackMotionDiagnosis20261022"):TEXT("SlingMotionDiagnosis20261022"));IFileManager::Get().MakeDirectory(*Dir,true);
    FFileHelper::SaveStringToFile(Json,*(Dir/TEXT("native_response.json")));World->DestroyWorld(false);return 0;
}
#endif
