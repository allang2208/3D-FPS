#if WITH_EDITOR
#include "FPSPlayerBodyAnimInstance.h"
#include "../Skills/FireballHandPose.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace FPSHammerCastDiagnosis
{
// Explicit offline diagnosis of the actual world-body graph. No gameplay,
// camera, rendering, package saves or changes to a user's running character.
static void Run(const TArray<FString>& Args)
{
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config)||!Config)return;
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));if(!Asset)return;
    TMap<FName,TObjectPtr<UAnimSequence>> Clips;
    for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
    {
        const FString Key(*Pair.Key);
        if(Key.StartsWith(TEXT("Warhammer."))||Key.StartsWith(TEXT("Unarmed."))||Key.StartsWith(TEXT("Crouch.")))
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Clips.Add(*Pair.Key,Clip);
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("HammerCastDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();
    const auto& Ref=Asset->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(const int32 P=Ref.GetParentIndex(I);P!=INDEX_NONE)Bind[I]=Bind[I]*Bind[P];
    const int32 U=Ref.FindBoneIndex(TEXT("upperarm_l")),E=Ref.FindBoneIndex(TEXT("lowerarm_l")),H=Ref.FindBoneIndex(TEXT("hand_l"));
    const int32 C=Ref.FindBoneIndex(TEXT("spine_05")),Index=Ref.FindBoneIndex(TEXT("index_01_l")),Middle=Ref.FindBoneIndex(TEXT("middle_01_l")),Pinky=Ref.FindBoneIndex(TEXT("pinky_01_l"));
    const FVector Origin=Bind[H].GetLocation();
    const FQuat Palm=FRotationMatrix::MakeFromXZ(Bind[Middle].GetLocation()-Origin,
        (Bind[Index].GetLocation()-Origin)^(Bind[Pinky].GetLocation()-Origin)).ToQuat();
    const FQuat Correction=Palm.Inverse()*Bind[H].GetRotation();
    FFireballHandPose HandPose;HandPose.Load();
    auto Report=MakeShared<FJsonObject>();Report->SetStringField(TEXT("kind"),TEXT("offline_native_graph_with_synthetic_camera_contacts"));
    Report->SetStringField(TEXT("body_mesh"),Asset->GetPathName());
    TArray<TSharedPtr<FJsonValue>> Cases;
    const auto Pack=[](const FTransform& T)
    {
        TArray<TSharedPtr<FJsonValue>> V;const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
        for(double X:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})V.Add(MakeShared<FJsonValueNumber>(X));
        return MakeShared<FJsonValueArray>(V);
    };
    for(int32 Case=0;Case<5;++Case)
    {
        auto* Body=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(Body);
        Body->SetSkeletalMeshAsset(Asset);Body->SetDisablePostProcessBlueprint(true);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;Body->RegisterComponentWithWorld(World);
        Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
        auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());Anim->Clips=Clips;
        const auto& Scale=Config->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
        auto& State=Anim->BodyState;State.Family=TEXT("Tool");State.Weapon=TEXT("warhammer");State.bHasActionProgress=true;
        State.AimPitch=Case==3?-55.f:Case==4?55.f:0.f;State.bCrouched=Case==2;
        Anim->Speed=Case==1?180.f:0.f;Anim->Direction=0.f;
        const auto Tick=[&](){Anim->Clock+=1.f/60.f;Body->TickAnimation(1.f/60.f,false);Body->RefreshBoneTransforms();};
        for(int32 I=0;I<60;++I)Tick();
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("case"),Case);Row->SetNumberField(TEXT("pitch"),State.AimPitch);
        Row->SetNumberField(TEXT("speed"),Anim->Speed);Row->SetBoolField(TEXT("crouched"),State.bCrouched);
        TArray<TSharedPtr<FJsonValue>> Samples;
        for(const FName Phase:{FName(TEXT("Gather")),FName(TEXT("Hold")),FName(TEXT("Ready")),FName(TEXT("Release")),FName(TEXT("Recover"))})
        {
            State.Action=EFPSBodyAction::Cast;State.ActionVariant=Phase;
            for(int32 Frame=0;Frame<=30;++Frame)
            {
                State.ActionProgress=Phase==TEXT("Hold")?1.f:Frame/30.f;
                State.ReleaseFraction=Phase==TEXT("Release")?.48f+.52f*FMath::Clamp(State.ActionProgress*3.f,0.f,1.f):Phase==TEXT("Ready")?.48f:0.f;
                const FQuat View=FQuat(FVector::UpVector,PI*.5)*FRotator(State.AimPitch,0.f,0.f).Quaternion();
                Anim->ActionWristMask=2;
                const FVector Point=FMath::Lerp(HandPose.GatherWrist,HandPose.ReleaseWrist,State.ReleaseFraction);
                Anim->ActionHands[1]=FTransform(View*HandPose.PalmFrame(State.ReleaseFraction)*Correction,
                    FVector(0,0,State.bCrouched?120:160)+View.RotateVector(Point));
                Tick();
                if(Frame%5!=0)continue;
                const auto& Pose=Body->GetComponentSpaceTransforms();const FQuat Chest=Pose[C].GetRotation()*Bind[C].GetRotation().Inverse();
                auto Sample=MakeShared<FJsonObject>(),Poses=MakeShared<FJsonObject>();
                Sample->SetStringField(TEXT("phase"),Phase.ToString());Sample->SetNumberField(TEXT("progress"),State.ActionProgress);
                Sample->SetNumberField(TEXT("wrist_front_cm"),Chest.UnrotateVector(Pose[H].GetLocation()-Pose[U].GetLocation()).Y);
                Sample->SetNumberField(TEXT("elbow_front_cm"),Chest.UnrotateVector(Pose[E].GetLocation()-Pose[U].GetLocation()).Y);
                Sample->SetNumberField(TEXT("upper_length_cm"),FVector::Distance(Pose[U].GetLocation(),Pose[E].GetLocation()));
                Sample->SetNumberField(TEXT("lower_length_cm"),FVector::Distance(Pose[E].GetLocation(),Pose[H].GetLocation()));
                for(int32 B=0;B<Ref.GetNum();++B)Poses->SetField(Ref.GetBoneName(B).ToString(),Pack(Pose[B]));
                Sample->SetObjectField(TEXT("component_pose"),Poses);Samples.Add(MakeShared<FJsonValueObject>(Sample));
            }
        }
        Row->SetArrayField(TEXT("samples"),Samples);Cases.Add(MakeShared<FJsonValueObject>(Row));Body->DestroyComponent();
    }
    Report->SetArrayField(TEXT("cases"),Cases);FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));
    const FString Path=Args.IsEmpty()?FPaths::ProjectSavedDir()/TEXT("HammerCastDiagnosis.json"):Args[0];
    FFileHelper::SaveStringToFile(Output,*Path);World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("HAMMER_CAST_DIAGNOSIS %s"),*Path);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseHammerCast"),TEXT("Explicit offline hammer cast diagnosis: [output file]."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
