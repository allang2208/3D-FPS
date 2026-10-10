#if WITH_EDITOR
// Explicit opt-in reproduction of the reported book-push wrist/arm conversion.
// Uses a transient preview world: no gameplay, screenshots or asset writes.
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyGrip.h"
#include "../Weapons/Spellbook/SpellbookAuthoredStrike.h"
#include "../Weapons/Spellbook/SpellbookCarryTuning.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace FPSBookPushDiagnosis
{
static TSharedPtr<FJsonValue> Pack(const FTransform& T)
{
    const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
    TArray<TSharedPtr<FJsonValue>> A;
    for(double V:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})A.Add(MakeShared<FJsonValueNumber>(V));
    return MakeShared<FJsonValueArray>(A);
}
static void Run(const TArray<FString>& Args)
{
    if(Args.IsEmpty())return;
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config)||!Config)return;
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    auto* Native=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7"));
    if(!Asset||!Native)return;
    TMap<FName,TObjectPtr<UAnimSequence>> Clips;
    for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
        if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Clips.Add(*Pair.Key,Clip);
    if(!Clips.FindRef(TEXT("Staff.BookPush")))return;
    FAssetCompilingManager::Get().FinishAllCompilation();
    FFPSBodyGripRig Rig;Rig.Initialize(Native->GetRefSkeleton(),Asset->GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
    const auto& Ref=Native->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)>=0)Bind[I]=Bind[I]*Bind[Ref.GetParentIndex(I)];
    const auto SourcePose=[&](float Time)
    {
        namespace Strike=SpellbookAuthoredStrike;namespace Grip=SpellbookAuthoredGrip;
        int32 A=0;while(A<Strike::KeyCount-2&&Time>=Strike::Times[A+1])++A;
        const float Alpha=FMath::Clamp((Time-Strike::Times[A])/(Strike::Times[A+1]-Strike::Times[A]),0.f,1.f);
        auto Pose=Ref.GetRefBonePose();
        for(int32 B=0;B<Grip::BoneCount;++B)
        {
            const int32 I=Ref.FindBoneIndex(Grip::ArmNames[B]);if(I==INDEX_NONE)continue;
            const int32 Parent=Ref.GetParentIndex(I);const FVector Scale=Parent>=0?Bind[Parent].GetScale3D():FVector::OneVector;
            const auto& From=Strike::Poses[A][B];const auto& To=Strike::Poses[A+1][B];
            Pose[I].SetLocation(FMath::Lerp(From.Position,To.Position,Alpha)/Scale);
            Pose[I].SetRotation(FQuat::Slerp(From.Rotation,To.Rotation,Alpha).GetNormalized());
        }
        for(int32 I=0;I<Pose.Num();++I)if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
        return Pose;
    };
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("BookPushDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;
    Report->SetStringField(TEXT("scope"),TEXT("Actual animation proxy, standing template camera (74+96 cm), no gameplay/rendering"));
    const auto& BodyRef=Asset->GetRefSkeleton();const int32 Left=BodyRef.FindBoneIndex(TEXT("clavicle_l"));
    auto Reference=MakeShared<FJsonObject>();
    for(int32 I=0;I<BodyRef.GetNum();++I)if(I==Left||BodyRef.BoneIsChildOf(I,Left))
        Reference->SetField(BodyRef.GetBoneName(I).ToString(),Pack(BodyRef.GetRefBonePose()[I]));
    Report->SetObjectField(TEXT("reference_local"),Reference);
    for(int32 Case=0;Case<5;++Case)
    {
        const bool Fixed=Case!=0&&Case!=2,Walking=Case==2||Case==3,Cancel=Case==4;
        auto* Actor=World->SpawnActor<AActor>();
        auto* Body=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(Body);
        Body->SetSkeletalMeshAsset(Asset);Body->SetDisablePostProcessBlueprint(true);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Body->RegisterComponentWithWorld(World);Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);
        Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
        auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());Anim->Clips=Clips;
        if(!Fixed)Anim->Clips.Remove(TEXT("Staff.BookPush"));
        const auto& Scale=Config->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
        Anim->BodyState.Family=TEXT("Staff");Anim->BodyState.Weapon=TEXT("ue_apprentice_staff");
        Anim->SpellbookEquipmentIndex=1;Anim->EquipmentGripHands=2;Rig.Transfer(SourcePose(0.f),Anim->EquipmentFingers);
        Anim->Speed=Walking?180.f:0.f;Anim->Direction=0.f;
        const float Step=1.f/120.f;
        const auto Tick=[&](){Anim->Clock+=Step;Body->TickAnimation(Step,false);Body->RefreshBoneTransforms();};
        for(int32 I=0;I<60;++I)Tick();
        auto Row=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Samples;
        Row->SetStringField(TEXT("case"),Case==0?TEXT("old_idle"):Case==1?TEXT("fixed_idle"):Case==2?TEXT("old_walk"):Case==3?TEXT("fixed_walk"):TEXT("fixed_cancel"));
        for(int32 Frame=-1;Frame<=84;++Frame)
        {
            const float Time=Frame*Step;
            const bool Active=Time>=0.f&&Time<SpellbookAuthoredStrike::Length&&(!Cancel||Time<.20f);
            auto& State=Anim->BodyState;State.Action=Active?EFPSBodyAction::GunBash:EFPSBodyAction::None;
            State.ActionVariant=Active?FName(TEXT("SpellbookPush")):NAME_None;State.Contacts.Channel=State.ActionVariant;
            State.bHasActionProgress=true;State.ActionProgress=FMath::Clamp(Time/SpellbookAuthoredStrike::Length,0.f,1.f);
            State.ContactFraction=SpellbookAuthoredStrike::Contact/SpellbookAuthoredStrike::Length;
            const auto Source=SourcePose(FMath::Clamp(Time,0.f,SpellbookAuthoredStrike::Length));
            auto Hand=Source[Rig.SourceHand];Hand.SetScale3D(FVector::OneVector);
            Anim->ActionHands[1]=Rig.Mount.Inverse()*Hand*FTransform(FRotator(0,90,0),FVector(0,0,170-SpellbookCarryTuning::LowerCm));
            Anim->ActionWristMask=Active?2:0;Anim->ActionFingerMask=2;Anim->ActionFingers=Anim->EquipmentFingers;
            if(Frame>=0)Tick();
            auto Sample=MakeShared<FJsonObject>(),Local=MakeShared<FJsonObject>(),Component=MakeShared<FJsonObject>();
            Sample->SetNumberField(TEXT("time"),Time);Sample->SetBoolField(TEXT("active"),Active);
            const auto& Pose=Body->GetComponentSpaceTransforms();
            for(int32 I=0;I<Pose.Num();++I)if(I==Left||BodyRef.BoneIsChildOf(I,Left))
            {
                const int32 Parent=BodyRef.GetParentIndex(I);const FString Name=BodyRef.GetBoneName(I).ToString();
                Local->SetField(Name,Pack(Parent>=0?Pose[I].GetRelativeTransform(Pose[Parent]):Pose[I]));
                Component->SetField(Name,Pack(Pose[I]));
            }
            Sample->SetObjectField(TEXT("local"),Local);Sample->SetObjectField(TEXT("component"),Component);
            Sample->SetField(TEXT("input_wrist"),Pack(Anim->ActionHands[1]));Samples.Add(MakeShared<FJsonValueObject>(Sample));
        }
        Row->SetArrayField(TEXT("samples"),Samples);Cases.Add(MakeShared<FJsonValueObject>(Row));Actor->Destroy();
    }
    Report->SetArrayField(TEXT("cases"),Cases);
    Text.Reset();
    FJsonSerializer::Serialize(Report,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    FFileHelper::SaveStringToFile(Text,*Args[0],FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("BOOK_PUSH_DIAGNOSIS_SAVED %s"),*Args[0]);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseBookPush"),TEXT("Opt-in book push arm reproduction: [output JSON]."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
