#include "LeapStrikeAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "ProductionToolMeshComponent.h"
#include "WarhammerShockwave.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/LeapStrikeMotion.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSLeapRootMotionSource.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "Camera/CameraTypes.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Combat/CombatControlImmunity.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregate.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/HandBrainFearComponent.h"
#include "../Monsters/FleshHandMonster.h"
#include "../UI/StatusEffectsComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/PhysicsVolume.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

namespace
{
TArray<TSharedPtr<FJsonValue>> LeapVec(const FVector& V)
{return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};}
TSharedPtr<FJsonObject> LeapTransform(const FTransform& T)
{
    auto J=MakeShared<FJsonObject>();J->SetArrayField(TEXT("p"),LeapVec(T.GetLocation()));J->SetArrayField(TEXT("s"),LeapVec(T.GetScale3D()));
    const auto Q=T.GetRotation();J->SetArrayField(TEXT("q"),{MakeShared<FJsonValueNumber>(Q.W),MakeShared<FJsonValueNumber>(Q.X),MakeShared<FJsonValueNumber>(Q.Y),MakeShared<FJsonValueNumber>(Q.Z)});return J;
}
void LeapWrite(const TSharedPtr<FJsonObject>& J,const FString& Path)
{FString Text;FJsonSerializer::Serialize(J.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);}
}

int32 ULeapStrikeAuditCommandlet::Main(const FString& Params)
{
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/LeapStrike20261107/Review/Before");FParse::Value(*Params,TEXT("Out="),Out);
    IFileManager::Get().MakeDirectory(*Out,true);
    const FString Original=FCommandLine::Get(),Slot=TEXT("LeapStrikeAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("LeapStrikeAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("LeapStrikeAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.ProductionSupplyVersion=1;Seed.Stamina=150;Seed.bSprintExhausted=false;
    auto Item=Model->CreateItem(TEXT("ue_steel_warhammer"));Item.Place=1;Item.Cell=6;Seed.Items.Add(Item);
    Seed.Skills.FindOrAdd(TEXT("leapStrike")).Level=1;if(!Model->CommitState(Seed))return 2;
    auto* Floor=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Floor);
    Floor->SetRootComponent(Box);Box->SetBoxExtent(FVector(6000,6000,25));Box->SetCollisionObjectType(ECC_WorldStatic);
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponent();Floor->SetActorLocation(FVector(0,0,-25));
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);PC->bShowMouseCursor=false;
    auto* Local=NewObject<ULocalPlayer>(GEngine);GI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));PC->SetPlayer(Local);
    Model->AttachPawn(Pawn);
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();
    auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));const int32 OldDelay=Delay?Delay->GetInt():1;
    if(Delay)Delay->Set(0,ECVF_SetByCode);
    Tool->InitializeLocalTool();if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();
    if(Delay)Delay->Set(OldDelay,ECVF_SetByCode);
    auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    if(FParse::Param(*Params,TEXT("CameraOnly")))
    {
#include "LeapStrikeCameraAudit.inl"
    }
    if(FParse::Param(*Params,TEXT("BallisticOnly")))
    {
#include "LeapStrikeBallisticAudit.inl"
    }
    if(FParse::Param(*Params,TEXT("HeightOnly")))
    {
#include "LeapStrikeHeightAudit.inl"
    }
    if(FParse::Param(*Params,TEXT("LandingOnly")))
    {
#include "LeapStrikeLandingAudit.inl"
    }
    if(FParse::Param(*Params,TEXT("ControlOnly")))
    {
#include "LeapStrikeControlAudit.inl"
    }
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;
    if(!Tool->Viewmodel||!Tool->Viewmodel->GetSkeletalMeshAsset())return 3;
    Report->SetStringField(TEXT("mesh"),Tool->Viewmodel->GetSkeletalMeshAsset()->GetPathName());
    const float Rates[]={30,60,120,144,0};
    int32 Failures=0;
    for(float Rate:Rates)
    {
        Tool->CancelUse();Pawn->WeaponState=EAKMWeaponState::Idle;
        auto Fresh=Model->Snapshot();Fresh.LeapStrikeCooldown=Fresh.LeapStrikeCooldownDuration=0.f;Fresh.Stamina=150.f;Model->CommitState(Fresh);
        PC->SetControlRotation(FRotator::ZeroRotator);
        Pawn->SetActorLocation(FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.4f),false);
        Move->SetMovementMode(MOVE_Walking);Move->StopMovementImmediately();
        Pawn->UpdateCamera(0.f);Tool->SampleMotion(TEXT("Idle"),0.f);
        const FString Status=Tool->LeapStrikeStatusText(false);
        const bool Started=Tool->BeginLeapStrike();
        auto Case=MakeShared<FJsonObject>();Case->SetNumberField(TEXT("fps"),Rate);Case->SetBoolField(TEXT("started"),Started);Case->SetStringField(TEXT("status"),Status);
        Case->SetArrayField(TEXT("target"),LeapVec(Tool->LeapTarget));
        double Time=0,Launch=-1,Land=-1,End=-1;float MaxArcError=0;bool WasLaunched=false,WasLanded=false;
        TArray<TSharedPtr<FJsonValue>> Frames;
        for(int32 I=0;Started&&I<500;++I)
        {
            const float Steps[]={1.f/120.f,1.f/45.f,1.f/60.f,.055f,1.f/144.f};
            const float Dt=Rate>0?1.f/Rate:Steps[I%5];Time+=Dt;++GFrameCounter;
            World->Tick(LEVELTICK_TimeOnly,Dt);
            Move->PerformMovement(Dt);
            Pawn->UpdateCamera(Dt);
            Tool->UpdateHandPresentation(Dt);
            if(!WasLaunched&&Tool->bLeapLaunched){Launch=Time;WasLaunched=true;}
            if(!WasLanded&&Tool->bLeapLanded){Land=Time;WasLanded=true;}
            if(Tool->bLeapLaunched&&!Tool->bLeapLanded)
            {
                LeapStrike::FTrajectory Path;
                if(LeapStrike::SolveTrajectory(Tool->LeapStart,Tool->LeapTarget,Move->GetGravityZ(),Move->GetPhysicsVolume()->TerminalVelocity,Path))
                    MaxArcError=FMath::Max(MaxArcError,float(FVector::Dist(Pawn->GetActorLocation(),Path.Position(Tool->LeapStart,Tool->LeapFlightAge))));
            }
            auto Frame=MakeShared<FJsonObject>();Frame->SetNumberField(TEXT("time"),Time);Frame->SetNumberField(TEXT("age"),Tool->LeapAge);
            Frame->SetBoolField(TEXT("active"),Tool->bLeapStrike);Frame->SetBoolField(TEXT("landed"),Tool->bLeapLanded);Frame->SetNumberField(TEXT("mode"),Move->MovementMode);
            Frame->SetArrayField(TEXT("actor"),LeapVec(Pawn->GetActorLocation()));Frame->SetObjectField(TEXT("camera"),LeapTransform(Pawn->FirstPersonCamera->GetComponentTransform()));
            Frame->SetObjectField(TEXT("mesh_to_camera"),LeapTransform(Tool->Viewmodel->GetComponentTransform().GetRelativeTransform(Pawn->FirstPersonCamera->GetComponentTransform())));
            Frame->SetStringField(TEXT("clip"),GetNameSafe(Tool->CurrentMotion));Frame->SetNumberField(TEXT("pose"),Tool->Viewmodel->GetPosition());
            FVector Loc;FRotator Rot;Tool->GetCameraMotion(Loc,Rot);Frame->SetArrayField(TEXT("camera_feedback_cm"),LeapVec(Loc*.45f));
            Frame->SetArrayField(TEXT("camera_feedback_degrees"),LeapVec(FVector(Rot.Pitch,Rot.Yaw,Rot.Roll)*.45f));
            Frame->SetArrayField(TEXT("impact"),LeapVec(Tool->LeapImpactPoint));
            if(Rate==120)
            {
                auto Bones=MakeShared<FJsonObject>();const auto& Pose=Tool->Viewmodel->GetComponentSpaceTransforms();
                for(int32 B=0;B<Pose.Num();++B)Bones->SetObjectField(Tool->Viewmodel->GetBoneName(B).ToString().ToLower(),LeapTransform(Pose[B]));
                Frame->SetObjectField(TEXT("bones"),Bones);
            }
            Frames.Add(MakeShared<FJsonValueObject>(Frame));
            if(!Tool->bLeapStrike){End=Time;break;}
        }
        Case->SetNumberField(TEXT("launch_at"),Launch);Case->SetNumberField(TEXT("land_at"),Land);Case->SetNumberField(TEXT("end_at"),End);
        Case->SetNumberField(TEXT("air_seconds"),Land>=0?Land-Launch:-1);Case->SetNumberField(TEXT("max_arc_error_cm"),MaxArcError);
        Case->SetArrayField(TEXT("frames"),Frames);
        LeapWrite(Case,Out/FString::Printf(TEXT("frames-%d.json"),FMath::RoundToInt(Rate)));
        Case->RemoveField(TEXT("frames"));Cases.Add(MakeShared<FJsonValueObject>(Case));
        Failures+=!Started||Land<0;
        UE_LOG(LogTemp,Display,TEXT("LEAP_AUDIT fps=%.0f started=%d launch=%.6f land=%.6f air=%.6f arc_error=%.5f"),Rate,Started,Launch,Land,Land>=0?Land-Launch:-1,MaxArcError);
    }
    Report->SetArrayField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("failures"),Failures);LeapWrite(Report,Out/TEXT("timing.json"));
    Tool->FinishLeapStrike();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
