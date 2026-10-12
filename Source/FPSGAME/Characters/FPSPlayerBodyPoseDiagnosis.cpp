#if WITH_EDITOR
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyGrip.h"
#include "FPSPlayerBodyPoses.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace FPSBodyPoseDiagnosis
{
// Explicit carry/contact and opt-in dash-arm pose diagnosis. No gameplay or asset saves.
static void Run(const TArray<FString>& Args)
{
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config)||!Config)return;
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    auto* Donor=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms"));
    auto* Idle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"));
    if(!Asset||!Donor||!Idle)return;
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("SwordPoseDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();
    const auto MakeMesh=[&](USkeletalMesh* Mesh)
    {
        auto* C=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(C);
        C->SetSkeletalMeshAsset(Mesh);C->SetDisablePostProcessBlueprint(true);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        C->RegisterComponentWithWorld(World);return C;
    };
    auto* Source=MakeMesh(Donor);Source->PlayAnimation(Idle,false);Source->SetPosition(0.f,false);
    Source->TickAnimation(0.f,false);Source->RefreshBoneTransforms();
    const auto Rigid=[](FTransform T){T.SetScale3D(FVector::OneVector);return T;};
    FFPSBodyGripRig Rig[2];
    for(int32 I=0;I<2;++I){const FName Hand=I==0?TEXT("hand_r"):TEXT("hand_l");Rig[I].Initialize(Donor->GetRefSkeleton(),Asset->GetRefSkeleton(),Hand,Hand);}
    auto* Body=MakeMesh(Asset);Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
    auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());
    for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
        if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Anim->Clips.Add(*Pair.Key,Clip);
    const auto& Scale=Config->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
    Anim->BodyState.Family=TEXT("Melee");Anim->BodyState.Weapon=TEXT("ue_tang_dao");Anim->BodyState.AimPitch=-18.f;
    const auto& Pose=Source->GetComponentSpaceTransforms();
    const FTransform Right=Rigid(Pose[Rig[0].SourceHand]),Left=Rigid(Pose[Rig[1].SourceHand]);
    Anim->LeftGripFromRight=Rig[1].Mount.Inverse()*Left.GetRelativeTransform(Right)*Rig[0].Mount;Anim->bHasLeftGrip=true;
    const FQuat Frame=FRotator(0,90,0).Quaternion()*FRotator(-18,0,0).Quaternion()*FRotator(0,90,0).Quaternion();
    Anim->ActionHands[0]=FTransform(Frame*(Rig[0].Mount.Inverse()*Right).GetRotation(),FPSBodyPoses::SwordReady(0)*Anim->PoseScale);
    Anim->ActionHands[1]=Anim->LeftGripFromRight*Anim->ActionHands[0];Anim->ActionWristMask=3;Anim->bCoupledActionWrists=true;
    for(const auto& R:Rig)R.Transfer(Pose,Anim->EquipmentFingers);
    Anim->EquipmentGripHands=3;Anim->ActionFingers=Anim->EquipmentFingers;Anim->ActionFingerMask=3;
    for(int32 I=0;I<20;++I){Anim->Clock=I/60.f;Body->TickAnimation(1.f/60.f,false);Body->RefreshBoneTransforms();}
    auto Report=MakeShared<FJsonObject>();
    for(int32 I=0;I<2;++I)
    {
        const TCHAR* Side=I==0?TEXT("right"):TEXT("left");const FName Hand=I==0?TEXT("hand_r"):TEXT("hand_l");
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("input"),Anim->ActionHands[I].GetLocation().ToString());
        Row->SetStringField(TEXT("final"),Body->GetSocketTransform(Hand,RTS_Component).GetLocation().ToString());Report->SetObjectField(Side,Row);
    }
    Report->SetNumberField(TEXT("wrist_spacing"),FVector::Distance(Body->GetSocketLocation(TEXT("hand_r")),Body->GetSocketLocation(TEXT("hand_l"))));
    if(Args.Num()>1&&Args[1]==TEXT("dash-arm"))
    {
        auto* Clip=Anim->Clips.FindRef(TEXT("Melee.FullBody.DashOverhead")).Get();
        auto* Reference=MakeMesh(Asset);
        TArray<TSharedPtr<FJsonValue>> Samples;
        const auto Pack=[](const FTransform& T)
        {
            const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
            TArray<TSharedPtr<FJsonValue>> V;
            for(double X:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})V.Add(MakeShared<FJsonValueNumber>(X));
            return MakeShared<FJsonValueArray>(V);
        };
        if(Clip)for(float Progress:{.1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f,.9f})
        {
            float Contact=.4f,Release=.65f;
            for(const auto& Marker:Clip->AuthoredSyncMarkers)
            {
                if(Marker.MarkerName==TEXT("Contact"))Contact=Marker.Time/Clip->GetPlayLength();
                if(Marker.MarkerName==TEXT("Release"))Release=Marker.Time/Clip->GetPlayLength();
            }
            auto& State=Anim->BodyState;State.Action=EFPSBodyAction::HeavyStrike;State.ActionVariant=TEXT("DashOverhead");
            State.bHasActionProgress=true;State.ActionProgress=Progress;State.ActionWeight=1.f;
            State.ContactFraction=.25f;State.ReleaseFraction=.75f;State.ActionEntryFraction=0.f;
            const float Sample=Progress<=.25f?FMath::Lerp(0.f,Contact,Progress/.25f):
                Progress<=.75f?FMath::Lerp(Contact,Release,(Progress-.25f)/.5f):
                FMath::Lerp(Release,1.f,(Progress-.75f)/.25f);
            Reference->PlayAnimation(Clip,false);Reference->SetPosition(Sample*Clip->GetPlayLength(),false);
            Reference->TickAnimation(0.f,false);Reference->RefreshBoneTransforms();
            for(int32 I=0;I<20;++I){Anim->Clock+=1.f/60.f;Body->TickAnimation(1.f/60.f,false);Body->RefreshBoneTransforms();}
            const auto& Ref=Asset->GetRefSkeleton();const auto& A=Body->GetComponentSpaceTransforms();
            const auto& B=Reference->GetComponentSpaceTransforms();
            auto Row=MakeShared<FJsonObject>(),Actual=MakeShared<FJsonObject>(),Authored=MakeShared<FJsonObject>();
            Row->SetNumberField(TEXT("progress"),Progress);Row->SetNumberField(TEXT("sample"),Sample);
            Row->SetNumberField(TEXT("grip_roll"),Anim->GetCurveValue(TEXT("SwordGripRoll")));
            for(int32 Bone=0;Bone<Ref.GetNum();++Bone)
            {
                if(!A.IsValidIndex(Bone)||!B.IsValidIndex(Bone))continue;
                const int32 Parent=Ref.GetParentIndex(Bone);const FString Name=Ref.GetBoneName(Bone).ToString();
                Actual->SetField(Name,Pack(Parent==INDEX_NONE?A[Bone]:A[Bone].GetRelativeTransform(A[Parent])));
                Authored->SetField(Name,Pack(Parent==INDEX_NONE?B[Bone]:B[Bone].GetRelativeTransform(B[Parent])));
            }
            Row->SetObjectField(TEXT("actual_local"),Actual);Row->SetObjectField(TEXT("authored_local"),Authored);
            Samples.Add(MakeShared<FJsonValueObject>(Row));
        }
        Report->SetArrayField(TEXT("dash_samples"),Samples);
        if(Clip)Report->SetStringField(TEXT("dash_clip"),Clip->GetPathName());
    }
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));
    const FString Path=Args.IsEmpty()?FPaths::ProjectSavedDir()/TEXT("SwordPoseDiagnosis.json"):Args[0];FFileHelper::SaveStringToFile(Output,*Path);
    World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("SWORD_POSE_DIAGNOSIS %s"),*Path);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseSwordPose"),TEXT("Explicit body contact diagnosis: [output file] [dash-arm]."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
