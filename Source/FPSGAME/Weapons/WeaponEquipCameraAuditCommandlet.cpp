#include "WeaponEquipCameraAuditCommandlet.h"
#include "WeaponActionCameraComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "M4TacticalSprintComponent.h"
#include "Camera/CameraTypes.h"
#include "HAL/IConsoleManager.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif

int32 UWeaponEquipCameraAuditCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("M249Wrist")))return RunM249WristReview(Params);
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/LMGEquipCamera20261110/Review.json");
    FParse::Value(*Params,TEXT("Out="),Out);
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;int32 Failures=0;
    const auto Record=[&](const TCHAR* Name,bool Passed,double Rotation,double Travel,double Clock=0.)
    {
        auto C=MakeShared<FJsonObject>();C->SetStringField(TEXT("case"),Name);C->SetBoolField(TEXT("passed"),Passed);
        C->SetNumberField(TEXT("max_angle_deg"),Rotation);C->SetNumberField(TEXT("max_travel_cm"),Travel);
        C->SetNumberField(TEXT("max_clock_error_s"),Clock);Cases.Add(MakeShared<FJsonValueObject>(C));Failures+=!Passed;
        UE_LOG(LogTemp,Display,TEXT("EQUIP_CAMERA %s %s angle=%.5f travel=%.5f clock=%.6f"),Passed?TEXT("PASS"):TEXT("FAIL"),Name,Rotation,Travel,Clock);
    };
    const auto Read=[](UCameraComponent* Camera)
    {FTransform T;float FOV;Camera->GetAdditiveOffset(T,FOV);return T;};
    const auto Angle=[](const FTransform& T)
    {return FMath::RadiansToDegrees(T.GetRotation().AngularDistance(FQuat::Identity));};
    auto* Camera=NewObject<UCameraComponent>();auto* Layer=NewObject<UWeaponActionCameraComponent>();
    // Actual compositor, including rapid same-clip restart and a switch to 201
    // (which intentionally contributes no authored equip camera curve).
    for(bool Restart:{false,true})
    {
        Layer->Apply(*Camera,EM4CameraAction::PKMEquip,.47f,.9f,{},.45f,{},1.f/60.f);
        const auto Before=Read(Camera);Layer->BeginEquipTransition();
        Layer->Apply(*Camera,Restart?EM4CameraAction::PKMEquip:EM4CameraAction::None,0,.9f,{},.45f,{},0.f);
        const bool Continuous=Read(Camera).Equals(Before,.00001f);
        for(int32 Frame=0;Frame<20;++Frame)Layer->Apply(*Camera,EM4CameraAction::None,0,0,{},.45f,{},1.f/60.f);
        const auto End=Read(Camera);
        Record(Restart?TEXT("restart_same_equip"):TEXT("interrupt_into_201"),Continuous&&End.Equals(FTransform::Identity,.00001f),Angle(Before),Before.GetLocation().Size());
    }
    for(int32 Frame=0;Frame<90;++Frame)Layer->UpdateSprint(1.f/60.f,true,true,1.f,1.f);
    Layer->Apply(*Camera,EM4CameraAction::None,0,0,{},.45f,{},0);
    const auto Sprint=Read(Camera);Layer->UpdateSprint(0,false,false,0,0);
    Layer->Apply(*Camera,EM4CameraAction::None,0,0,{},.45f,{},0);
    const bool SprintContinuous=Read(Camera).Equals(Sprint,.00001f);
    for(int32 Frame=0;Frame<40;++Frame){Layer->UpdateSprint(1.f/60.f,false,false,0,0);Layer->Apply(*Camera,EM4CameraAction::None,0,0,{},.45f,{},1.f/60.f);}
    Record(TEXT("sprint_switch_return"),SprintContinuous&&Read(Camera).Equals(FTransform::Identity,.00001f),Angle(Sprint),Sprint.GetLocation().Size());

    const FString Original=FCommandLine::Get(),Slot=TEXT("WeaponEquipCameraAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WeaponEquipCameraAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("WeaponEquipCameraAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);
    auto* Local=NewObject<ULocalPlayer>(GEngine);GI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));PC->SetPlayer(Local);
    Pawn->FirstPersonCamera->Activate(true);Pawn->GetCharacterMovement()->SetMovementMode(MOVE_None);
    Pawn->bWasGrounded=false;Pawn->CameraMotionScale=.45f;
    for(const TCHAR* Definition:{TEXT("ue_lmg201"),TEXT("ue_pkm_lowpoly"),TEXT("ue_m249")})
    {
        auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
        auto Item=Model->CreateItem(Definition);Item.Place=1;Item.Cell=6;Item.Magazine=30;Seed.Items.Add(Item);
        if(!Model->CommitState(Seed))return 2;
        Pawn->ActiveInventoryWeapon=Item.InstanceId;Pawn->ActiveInventoryWeaponDefinition=Definition;Pawn->bInventoryWeaponReady=true;
        Pawn->bUseM4Infima=Pawn->bUseQBZ191=Pawn->bUseASH12=Pawn->bUseM16=Pawn->bUseM1911=Pawn->bUseDanWesson715=false;
        Pawn->InitializeWeaponVisuals();
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
#endif
        if(!Pawn->EquipAnimation||!Pawn->GunplayAnimation)return 3;
        // Haste, slow handling, low/high frame rate and a 120 ms hitch. Also
        // sample the event frame with elapsed=0 and a large pre-input delta.
        for(float EquipRate:{.75f,1.f,2.5f,4.f})for(int32 FPS:{30,60,144,0})
        {
            for(int32 Frame=0;Frame<20;++Frame)Pawn->UpdateCamera(1.f/60.f);
            Pawn->FirearmEquipRate=EquipRate;Pawn->StartEquipCharge();Pawn->UpdateActionPose(.12f);
            double ClockError=FMath::Abs(Pawn->ActionElapsed-Pawn->WeaponStateElapsed),MaxAngle=0,MaxTravel=0;
            bool Finite=true;float Time=0;int32 Frame=0;const FRotator Aim=PC->GetControlRotation();
            while(Time<Pawn->EquipAnimation->GetPlayLength()/EquipRate+.5f)
            {
                const float Dt=FPS>0?1.f/FPS:(Frame%11==3?.12f:1.f/90.f);
                ++Frame;Time+=Dt;++GFrameCounter;World->Tick(LEVELTICK_TimeOnly,Dt);
                Pawn->UpdateWeaponState(Dt);Pawn->UpdateActionPose(Dt);Pawn->UpdateCamera(Dt);
                if(Pawn->WeaponState==EAKMWeaponState::Equipping)ClockError=FMath::Max(ClockError,double(FMath::Abs(Pawn->ActionElapsed-Pawn->WeaponStateElapsed)));
                const auto T=Read(Pawn->FirstPersonCamera);Finite&=!T.ContainsNaN();
                MaxAngle=FMath::Max(MaxAngle,Angle(T));MaxTravel=FMath::Max(MaxTravel,T.GetLocation().Size());
            }
            const bool Ended=Pawn->WeaponState==EAKMWeaponState::Idle&&Read(Pawn->FirstPersonCamera).Equals(FTransform::Identity,.0001f);
            const bool Passed=Finite&&Ended&&ClockError<.0001&&MaxAngle<1.f&&MaxTravel<.55f&&PC->GetControlRotation().Equals(Aim,.0001f);
            Record(*FString::Printf(TEXT("%s_rate_%.2f_fps_%d"),Definition,EquipRate,FPS),Passed,MaxAngle,MaxTravel,ClockError);
        }
    }
    if(FParse::Param(*Params,TEXT("Transitions")))
    {
#include "WeaponEquipTransitionAudit.inl"
    }
    Report->SetArrayField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetStringField(TEXT("scope"),TEXT("Native local equip clock/compositor with isolated audit profile; no rendering or network session. Optional full POV transition cases recorded separately."));
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Out),true);FFileHelper::SaveStringToFile(Text,*Out);
    // The transition fixture dispatches BeginPlay manually in a non-playing
    // commandlet world. End its components while their world still exists.
    // RouteEndPlay skips actors that did not pass InitializeActorsForPlay;
    // pair the explicit DispatchBeginPlay with EndPlay here instead.
    if(Pawn->HasActorBegunPlay())Pawn->EndPlay(EEndPlayReason::Quit);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
