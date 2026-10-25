#if WITH_EDITOR
#include "FPSPlayerBodyAnimInstance.h"
#include "../Production/WarhammerHeavyMotion.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace FPSHammerSprintDiagnosis
{
// Explicit, read-only graph sampling for the user's sprint-attack review.
// Reconstructs the current executor's clocks/stride; does not run gameplay,
// save packages, alter live actors or claim to exercise collision/networking.
static void Run(const TArray<FString>& Args)
{
    FString Text;TSharedPtr<FJsonObject> Config;
    if(Args.IsEmpty()||!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config)||!Config)return;
    const auto Pack=[](const FTransform& T)
    {
        TArray<TSharedPtr<FJsonValue>> V;const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
        for(double X:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})V.Add(MakeShared<FJsonValueNumber>(X));
        return MakeShared<FJsonValueArray>(V);
    };
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("HammerSprintDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();
    auto Report=MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("scope"),TEXT("Actual native body graph; reconstructed sprint clock and capsule travel; no gameplay, collision or network test"));
    Report->SetNumberField(TEXT("fps"),60);Report->SetNumberField(TEXT("stride_cm"),100);
    TArray<TSharedPtr<FJsonValue>> Variants;
    for(const FString Variant:{FString(TEXT("jason")),FString(TEXT("kaitlin"))})
    {
        const auto VariantConfig=Variant==TEXT("jason")?Config:Config->GetObjectField(TEXT("body_variants"))->GetObjectField(Variant);
        auto* Asset=LoadObject<USkeletalMesh>(nullptr,*VariantConfig->GetStringField(TEXT("body_mesh")));if(!Asset)continue;
        TMap<FName,TObjectPtr<UAnimSequence>> Clips;
        const auto LoadClips=[&](const TSharedPtr<FJsonObject>& Source)
        {
            for(const auto& Pair:Source->GetObjectField(TEXT("clips"))->Values)
            {
                const FString Key(*Pair.Key);
                if(Key.StartsWith(TEXT("Warhammer."))||Key.StartsWith(TEXT("Unarmed."))||Key.StartsWith(TEXT("Crouch."))||
                    Key==TEXT("Jump")||Key==TEXT("Fall")||Key==TEXT("Land"))
                    if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Clips.Add(*Pair.Key,Clip);
            }
        };
        LoadClips(Config);if(VariantConfig!=Config)LoadClips(VariantConfig);
        FAssetCompilingManager::Get().FinishAllCompilation();
        auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("variant"),Variant);Item->SetStringField(TEXT("mesh"),Asset->GetPathName());
        const auto& Ref=Asset->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
        TArray<TSharedPtr<FJsonValue>> Names,Reference,ClipRows;
        for(int32 I=0;I<Ref.GetNum();++I)
        {
            if(const int32 Parent=Ref.GetParentIndex(I);Parent!=INDEX_NONE)Bind[I]=Bind[I]*Bind[Parent];
            Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(I).ToString()));Reference.Add(Pack(Bind[I]));
        }
        Item->SetArrayField(TEXT("names"),Names);Item->SetArrayField(TEXT("reference_cs"),Reference);
        for(const FName Key:{FName(TEXT("Warhammer.FullBody.SprintLift")),FName(TEXT("Warhammer.FullBody.SprintSlam"))})
            if(const auto* Clip=Clips.FindRef(Key).Get())
            {
                auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("role"),Key.ToString());Row->SetStringField(TEXT("asset"),Clip->GetPathName());
                Row->SetNumberField(TEXT("length"),Clip->GetPlayLength());TArray<TSharedPtr<FJsonValue>> Markers;
                for(const auto& M:Clip->AuthoredSyncMarkers)
                {auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("name"),M.MarkerName.ToString());R->SetNumberField(TEXT("time"),M.Time);Markers.Add(MakeShared<FJsonValueObject>(R));}
                Row->SetArrayField(TEXT("markers"),Markers);ClipRows.Add(MakeShared<FJsonValueObject>(Row));
            }
        Item->SetArrayField(TEXT("clips"),ClipRows);
        TArray<TSharedPtr<FJsonValue>> Cases;
        for(int32 Case=0;Case<4;++Case)
        {
            const float Rate=Case==2?2.f:1.f;
            const bool Air=Case==3;
            const float Lift=WarhammerSprint::LiftSeconds/Rate,End=Lift+WarhammerHeavy::RealDuration(Rate);
            auto* Body=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(Body);
            Body->SetSkeletalMeshAsset(Asset);Body->SetDisablePostProcessBlueprint(true);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;Body->RegisterComponentWithWorld(World);
            Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
            auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());Anim->Clips=Clips;
            const auto& Scale=VariantConfig->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
            auto& S=Anim->BodyState;S.Family=TEXT("Tool");S.Weapon=TEXT("warhammer");S.bHasActionProgress=true;
            S.bSprinting=true;S.ActionVariant=TEXT("WarhammerSprintReady");Anim->Speed=600.f;
            constexpr float Dt=1.f/60.f;
            const auto Tick=[&](){Anim->Clock+=Dt;Body->TickAnimation(Dt,false);Body->RefreshBoneTransforms();};
            for(int32 I=0;I<(Case==1?75:60);++I)Tick();
            const float Start=Anim->Clock;
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("case"),Case);Row->SetNumberField(TEXT("rate"),Rate);Row->SetBoolField(TEXT("airborne"),Air);
            Row->SetNumberField(TEXT("lift_seconds"),Lift);Row->SetNumberField(TEXT("contact_seconds"),Lift+WarhammerHeavy::Contact/Rate);
            TArray<TSharedPtr<FJsonValue>> Samples;
            float Carry=600.f,Travel=0.f,PreviousTravel=0.f;
            for(int32 Frame=0;Frame<=FMath::CeilToInt((End+.3f)/Dt);++Frame)
            {
                const float Age=Frame*Dt;
                S.bSprinting=false;S.ActionWeight=1.f;
                Anim->bFalling=Air;Anim->VerticalSpeed=Air?-120.f:0.f;
                if(Air){Carry=FMath::Max(0.f,Carry-300.f*Dt);Travel+=Carry*Dt;}
                else Travel=100.f*FMath::SmoothStep(0.f,Lift,Age);
                // The body now measures swept travel on owner and observers.
                Anim->Speed=Air?Carry:FMath::Max(0.f,(Travel-PreviousTravel)/Dt);
                PreviousTravel=Travel;
                if(Age<Lift)
                {
                    S.Action=EFPSBodyAction::Charge;S.ActionVariant=TEXT("WarhammerSprintLift");
                    S.ActionDuration=Lift;S.ActionProgressRate=1.f/Lift;
                    S.ActionProgress=Age/Lift;S.ActionStartedAt=Start;
                }
                else if(Age<End)
                {
                    const float Source=WarhammerHeavy::SourceTime(Age-Lift,Rate);
                    const float MotionRate=Source>=WarhammerHeavy::Contact&&Source<=WarhammerHeavy::HoldEnd?1.f:Rate;
                    S.Action=EFPSBodyAction::HeavyStrike;S.ActionVariant=TEXT("WarhammerSprintSlam");
                    S.ActionDuration=WarhammerHeavy::Duration/MotionRate;S.ActionProgressRate=MotionRate/WarhammerHeavy::Duration;
                    S.ActionProgress=Source/WarhammerHeavy::Duration;S.ActionStartedAt=Anim->Clock-Source/MotionRate;
                }
                else {S.Action=EFPSBodyAction::None;S.ActionVariant=TEXT("warhammer");S.ActionProgress=0.f;S.ActionProgressRate=0.f;}
                S.ContactFraction=WarhammerHeavy::Contact/WarhammerHeavy::Duration;
                S.ReleaseFraction=(WarhammerHeavy::Contact+.12f)/WarhammerHeavy::Duration;
                S.PresentationSampledAt=Anim->Clock+Dt;
                Tick();
                auto Sample=MakeShared<FJsonObject>(),Bones=MakeShared<FJsonObject>();
                Sample->SetNumberField(TEXT("time"),Age);Sample->SetNumberField(TEXT("travel"),Travel);Sample->SetNumberField(TEXT("anim_speed"),Anim->Speed);
                Sample->SetStringField(TEXT("phase"),S.ActionVariant.ToString());Sample->SetNumberField(TEXT("progress"),S.ActionProgress);
                const auto& Pose=Body->GetComponentSpaceTransforms();
                for(const FName Bone:{FName(TEXT("pelvis")),FName(TEXT("spine_05")),FName(TEXT("thigh_l")),FName(TEXT("thigh_r")),
                    FName(TEXT("calf_l")),FName(TEXT("calf_r")),FName(TEXT("foot_l")),FName(TEXT("foot_r")),FName(TEXT("ball_l")),FName(TEXT("ball_r")),FName(TEXT("hand_r"))})
                    if(const int32 I=Ref.FindBoneIndex(Bone);I!=INDEX_NONE)Bones->SetField(Bone.ToString(),Pack(Pose[I]));
                Sample->SetObjectField(TEXT("bones"),Bones);
                if(Case==0&&Frame%2==0)
                {TArray<TSharedPtr<FJsonValue>> Full;for(const auto& T:Pose)Full.Add(Pack(T));Sample->SetArrayField(TEXT("pose_cs"),Full);}
                Samples.Add(MakeShared<FJsonValueObject>(Sample));
            }
            Row->SetArrayField(TEXT("samples"),Samples);Cases.Add(MakeShared<FJsonValueObject>(Row));Body->DestroyComponent();
        }
        Item->SetArrayField(TEXT("cases"),Cases);Variants.Add(MakeShared<FJsonValueObject>(Item));
    }
    Report->SetArrayField(TEXT("variants"),Variants);FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));
    FFileHelper::SaveStringToFile(Output,*Args[0]);World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("HAMMER_SPRINT_DIAGNOSIS %s"),*Args[0]);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseHammerSprint"),TEXT("Explicit read-only hammer sprint graph review: output JSON."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
