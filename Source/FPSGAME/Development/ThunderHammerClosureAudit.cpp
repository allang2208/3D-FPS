#include "ThunderHammerClosureAudit.h"
#include "KukriCombatWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/M4GunsmithWidget.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ThunderHammerThrown.h"
#include "../Production/ThunderHammerCallIntent.h"
#include "../Production/WarhammerShockwave.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraActor.h"
#include "Engine/StaticMeshActor.h"
#include "AudioMixerBlueprintLibrary.h"
#include "DynamicRHI.h"
#include "RenderTimer.h"
#include "UnrealClient.h"
#include "HAL/FileManager.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/Layout/SScrollBox.h"

namespace ThunderClosure
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("ThunderHammerClosureAudit"));}
FString CaptureDir(){FString P;FParse::Value(FCommandLine::Get(),TEXT("ThunderClosureCapture="),P);return P;}
bool Visual(){return !CaptureDir().IsEmpty();}
bool HostInput(){return FParse::Param(FCommandLine::Get(),TEXT("ThunderClosureHostInput"));}
bool LocalScenario(){return Visual()||HostInput()||FParse::Param(FCommandLine::Get(),TEXT("ThunderClosureStandalone"));}
int32 FinalPhase(){return HostInput()?15:LocalScenario()?13:24;}
TSet<FString> Captured;
TArray<FString> Frames;
bool Recording=false;
TWeakObjectPtr<UM4GunsmithWidget> Workbench;
TWeakObjectPtr<ACameraActor> ObserverCamera;
TWeakObjectPtr<APawn> ObserverTarget;
TWeakObjectPtr<APlayerState> ObserverPlayer;
double ObserverGroundAt=-1.,ObserverShotAt=-1.;
int32 ObserverShot=0;
double ProbeAt=-10.;
void ShowSpecialOptions(const TSharedRef<SWidget>& Widget,bool CenterPair=false)
{
    if(Widget->GetType()==TEXT("SScrollBox"))
    {
        const auto Scroll=StaticCastSharedRef<SScrollBox>(Widget);
        if(Scroll->GetOrientation()==Orient_Horizontal)
        {if(CenterPair)Scroll->SetScrollOffset(FMath::Max(0.f,Scroll->GetScrollOffset()-180.f));else Scroll->ScrollToEnd();}
    }
    if(auto* Children=Widget->GetChildren())
        for(int32 Index=0;Index<Children->Num();++Index)ShowSpecialOptions(Children->GetChildAt(Index),CenterPair);
}
void Capture(const FString& Name,bool UI=false)
{
    if(!Visual()||Captured.Contains(Name))return;Captured.Add(Name);
    FScreenshotRequest::RequestScreenshot(CaptureDir()/Name+TEXT(".png"),UI,false);
}
int32 Phase=0;
bool Passed=true,WaitingReconnect=false;
FGuid Identity;
TArray<TSharedPtr<FJsonValue>> Rows;
const TCHAR* Names[]={TEXT("heavy_seat_apply_save_upload"),TEXT("light_seat_apply_save_upload"),TEXT("laminated_seat_apply_save_upload"),
    TEXT("jilei_apply_save_upload"),TEXT("static_grip_apply_save_upload"),TEXT("coil_grip_apply_save_upload"),
    TEXT("tap_before_threshold"),TEXT("partial_hold_cancel"),TEXT("release_first_full_frame"),TEXT("release_first_full_frame_high_jitter"),
    TEXT("cancel_repress_same_frame"),TEXT("guanlei_apply_save_upload"),TEXT("throw_real_input"),TEXT("late_join_ground_hammer"),
    TEXT("unequip_actual_inventory_upload"),TEXT("equip_actual_inventory_upload"),TEXT("death_respawn_ground_hammer"),
    TEXT("jilei_before_death"),TEXT("death_respawn_charging"),TEXT("guanlei_before_reconnect"),TEXT("disconnect_ground_hammer"),
    TEXT("same_saved_profile_reconnect"),TEXT("throw_before_server_travel"),TEXT("server_travel_profile_and_cleanup")};
FString Seat(int32 P)
{
    if(P==0)return TEXT("reinforced_block");if(P==1)return TEXT("ribbed_light");if(P==2)return TEXT("laminated_damper");
    return P>=11&&P!=17&&P!=18?TEXT("guan_lei_seat"):TEXT("ji_lei_seat");
}
bool InstallCase(int32 P){return P<=5||P==11||P==17||P==19;}
void Network(UWorld* W,bool High=false)
{
#if DO_ENABLE_NET_TEST
    if(auto* D=W->GetNetDriver())
    {
        FPacketSimulationSettings S;S.PktLag=High?180:60;S.PktLagVariance=High?80:20;S.PktLoss=3;D->SetPacketSimulationSettings(S);
        UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_NETWORK mode=%d lag=%d variance=%d loss=%d"),int32(W->GetNetMode()),D->PacketSimulationSettings.PktLag,D->PacketSimulationSettings.PktLagVariance,D->PacketSimulationSettings.PktLoss);
    }
#endif
}
void Save(UWorld* W)
{
    auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),Passed&&Phase==FinalPhase());R->SetNumberField(TEXT("completed"),Rows.Num());
    R->SetNumberField(TEXT("next_phase"),Phase);R->SetArrayField(TEXT("cases"),Rows);R->SetNumberField(TEXT("net_mode"),W->GetNetMode());
    R->SetStringField(TEXT("profile_id"),Identity.ToString());R->SetStringField(TEXT("scope"),TEXT("real gunsmith Apply, durable save/reload, profile chunk upload, FirePressed/FireInputReleased, damage/respawn, late join, same profile process restart, ServerTravel; no rendered acceptance"));
    if(LocalScenario())R->SetStringField(TEXT("scope"),TEXT("standalone real gunsmith Apply, save/reload and input; no network upload or lifecycle coverage; image/audio evidence separate"));
    if(HostInput())R->SetStringField(TEXT("scope"),TEXT("listen host real input and save/reload, remote late-join grounded hammer, actual recall and rendered observer; two processes, no reconnect/travel coverage in this capture"));
    FString Path,Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));
    if(FParse::Value(FCommandLine::Get(),TEXT("ThunderClosureOutput="),Path))FFileHelper::SaveStringToFile(Text,*Path);
    if(Visual())FFileHelper::SaveStringArrayToFile(Frames,*(CaptureDir()/TEXT("frames.csv")));
}
void Result(UWorld* W,bool OK,const FString& Detail)
{
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),HostInput()&&Phase==14?TEXT("host_recall_remote_presentation"):Names[Phase]);R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("detail"),Detail);
    Rows.Add(MakeShared<FJsonValueObject>(R));Passed&=OK;
    UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_CASE phase=%d pass=%d %s"),Phase,OK,*Detail);++Phase;Save(W);
}
}
void AThunderHammerClosureController::ServerHello_Implementation(bool Observer)
{if(ThunderClosure::Enabled()){Hello=true;IsObserver=Observer;UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_HELLO observer=%d local=%d solo=%d"),Observer,IsLocalController(),ThunderClosure::LocalScenario());}}
void AThunderHammerClosureController::ClientExit_Implementation()
{if(ThunderClosure::Enabled()){GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->SaveNow();ExitAt=GetWorld()->GetRealTimeSeconds()+(HasAuthority()?3.:1.);}}
void AThunderHammerClosureController::ServerObserved_Implementation(bool Ground,bool Seat)
{if(ThunderClosure::Enabled()){ObservedGround|=Ground;ObservedSeat|=Seat;}}
void AThunderHammerClosureController::ServerDone_Implementation(int32 P,bool OK,const FString& Message)
{if(ThunderClosure::Enabled()&&P==ThunderClosure::Phase){Done=true;ClientOK=OK;Detail=Message;}}
void AThunderHammerClosureController::ClientPhase_Implementation(int32 P)
{
    if(!ThunderClosure::Enabled()||P==Current||!Attached.IsValid())return;
    InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));
    Current=P;Started=GetWorld()->GetRealTimeSeconds();Pressed=Released=Sent=SawCharge=SawOrdinarySwing=InstallAttempted=false;InputCount=0;InstalledAt=-1.;
    UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_PHASE phase=%d local=%d solo=%d"),P,IsLocalController(),ThunderClosure::LocalScenario());
    ThunderClosure::Network(GetWorld(),P==9);
}
void AThunderHammerClosureController::Tick(float Delta)
{
    Super::Tick(Delta);if(!ThunderClosure::Enabled()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());if(!M||!M->IsAudit()||!P||!G)return;
    const bool Observer=FParse::Param(FCommandLine::Get(),TEXT("ThunderClosureObserver"));
    if(!Seeded)
    {
        if(!M->FindItem(TEXT("closure_thor"))&&!FParse::Param(FCommandLine::Get(),TEXT("ThunderClosureRejoin")))
        {
            auto S=M->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.DungeonRun={};S.Health=100;S.Mana=100;S.Stamina=150;
            auto I=M->CreateItem(TEXT("ue_thunder_god_hammer"));I.InstanceId=TEXT("closure_thor");I.Place=1;I.Cell=6;S.Items.Add(I);
            auto O=M->CreateItem(TEXT("ue_m1911"));O.InstanceId=TEXT("closure_other");O.Place=1;O.Cell=9;S.Items.Add(O);
            if(!M->CommitState(S))return;
        }
        Seeded=true;ServerHello(Observer);ThunderClosure::Network(GetWorld());
    }
    if(Attached.Get()!=P)
    {
        M->AttachPawn(P);P->ApplyColdSteelProfile(M);Attached=P;
        P->SetActorLocation(FVector(HasAuthority()?-600.f:0.f,Observer?400.f:0.f,100));
        P->GetCharacterMovement()->StopMovementImmediately();P->GetCharacterMovement()->DisableMovement();
        SetControlRotation(FRotator(-10,0,0));
    }
    if(Observer)
    {
        FString ObserverDir;FParse::Value(FCommandLine::Get(),TEXT("ThunderObserverCapture="),ObserverDir);
        for(TActorIterator<AThunderHammerThrown> It(GetWorld());It;++It)if(It->IsGrounded()&&!ObservedGround)
        {
            TArray<UStaticMeshComponent*> Meshes;It->GetComponents(Meshes);
            for(const auto* Mesh:Meshes)if(Mesh->GetStaticMesh()&&Mesh->GetStaticMesh()->GetName()==TEXT("SM_ThunderGodHammer_head_mount_guan_lei_seat_V13"))
            {
                ObservedGround=true;ThunderClosure::ObserverGroundAt=Now;ThunderClosure::ObserverTarget=Cast<APawn>(It->GetOwner());
                if(auto* Target=ThunderClosure::ObserverTarget.Get())ThunderClosure::ObserverPlayer=Target->GetPlayerState();
                if(ObserverDir.IsEmpty())ServerObserved(true,true);
                else
                {
                    IFileManager::Get().MakeDirectory(*ObserverDir,true);
                    auto* Camera=GetWorld()->SpawnActor<ACameraActor>();ThunderClosure::ObserverCamera=Camera;
                    Camera->GetCameraComponent()->SetFieldOfView(50.f);
                    Camera->SetActorLocation(It->GetActorLocation()+FVector(-120,-150,65));
                    Camera->SetActorRotation((It->GetActorLocation()+FVector(0,0,15)-Camera->GetActorLocation()).Rotation());SetViewTarget(Camera);
                    auto* Sun=NewObject<UDirectionalLightComponent>(Camera);Camera->AddInstanceComponent(Sun);Sun->SetMobility(EComponentMobility::Movable);Sun->SetIntensity(4.f);Sun->RegisterComponent();Sun->SetWorldRotation(FRotator(-40,30,0));
                    auto* Sky=NewObject<USkyLightComponent>(Camera);Camera->AddInstanceComponent(Sky);Sky->SetMobility(EComponentMobility::Movable);Sky->SetIntensity(1.f);Sky->RegisterComponent();
                    auto* Floor=GetWorld()->SpawnActor<AStaticMeshActor>();Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
                    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Floor->SetActorEnableCollision(false);
                    Floor->SetActorLocation(FVector(0,0,-10));Floor->SetActorScale3D(FVector(200,200,.2));
                }
                break;
            }
        }
        if(!ObserverDir.IsEmpty()&&ThunderClosure::ObserverCamera.IsValid())
        {
            if(Now-ThunderClosure::ObserverGroundAt>8.)
            {
                if(!ObservedSeat){ObservedSeat=true;ServerObserved(true,true);}
                if(auto* State=ThunderClosure::ObserverPlayer.Get())ThunderClosure::ObserverTarget=State->GetPawn();
                if(auto* Target=ThunderClosure::ObserverTarget.Get())
                {
                    auto* Camera=ThunderClosure::ObserverCamera.Get();Camera->SetActorLocation(Target->GetActorLocation()+FVector(200,-230,60));
                    Camera->SetActorRotation((Target->GetActorLocation()+FVector(0,0,30)-Camera->GetActorLocation()).Rotation());
                }
            }
            if(Now-ThunderClosure::ObserverGroundAt>3.&&Now-ThunderClosure::ObserverShotAt>1.)
            {
                ThunderClosure::ObserverShotAt=Now;
                FScreenshotRequest::RequestScreenshot(ObserverDir/FString::Printf(TEXT("remote_%03d.png"),ThunderClosure::ObserverShot++),false,false);
            }
        }
        return;
    }
    if((HasAuthority()&&!ThunderClosure::LocalScenario())||Current<0||Sent)return;
    auto* T=P->FindComponentByClass<UProductionToolComponent>();if(!T)return;
    const double Age=Now-Started;
    const bool Visual=ThunderClosure::Visual();
    if(Visual)
    {
        if(ThunderClosure::Frames.IsEmpty())ThunderClosure::Frames.Add(TEXT("phase,age,delta_ms,game_ms,render_ms,gpu_ms,available_physical_mb"));
        ThunderClosure::Frames.Add(FString::Printf(TEXT("%d,%.4f,%.4f,%.4f,%.4f,%.4f,%llu"),InstalledAt<0&&Current==0?-1:Current,Age,Delta*1000.,
            FPlatformTime::ToMilliseconds(GGameThreadTime),FPlatformTime::ToMilliseconds(GRenderThreadTime),FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)),FPlatformMemory::GetStats().AvailablePhysical/(1024*1024)));
    }
    auto ReportCase=[&](bool OK,const FString& Message){Sent=true;ServerDone(Current,OK,Message);};
    if(ThunderClosure::InstallCase(Current))
    {
        if(Age<(Visual?10.:2.))return;
        if(Visual&&Current==0&&InstalledAt<0)ThunderClosure::Capture(TEXT("factory_idle"));
        const FString Slot=Current==4||Current==5?TEXT("grip"):TEXT("head_mount");
        const FString Part=Current==4?TEXT("static_field_grip"):Current==5?TEXT("coil_grip"):ThunderClosure::Seat(Current);
        if(!InstallAttempted){InstallAttempted=G->Begin(TEXT("closure_thor"))&&G->Select(Slot,Part);}
        if(InstalledAt>=0.)
        {
            if(Now-InstalledAt<(Visual?10.:.1))return;
            if(Visual)
            {
                ThunderClosure::Capture(FString::Printf(TEXT("seat_or_grip_%02d"),Current));
                if(Now-InstalledAt<10.3)return;
                if(!ThunderClosure::Workbench.IsValid())
                {
                    G->Begin(TEXT("closure_thor"));
                    auto* Panel=CreateWidget<UM4GunsmithWidget>(this,UM4GunsmithWidget::StaticClass());
                    ThunderClosure::Workbench=Panel;Panel->AddToViewport(60);Panel->SelectCategory(Slot);
                    if(Current==4||Current==5)ThunderClosure::ShowSpecialOptions(Panel->TakeWidget());
                }
                if(Current==4&&Now-InstalledAt>14.&&!ThunderClosure::Captured.Contains(TEXT("static_pair_scroll")))
                {ThunderClosure::Captured.Add(TEXT("static_pair_scroll"));ThunderClosure::ShowSpecialOptions(ThunderClosure::Workbench->TakeWidget(),true);}
                if(Now-InstalledAt<15.)return;
                ThunderClosure::Capture(FString::Printf(TEXT("workbench_%02d"),Current),true);
                if(Now-InstalledAt<15.3)return;
                ThunderClosure::Workbench->RemoveFromParent();ThunderClosure::Workbench.Reset();G->Close();P->ApplyColdSteelProfile(M);
            }
            const auto* I=M->FindItem(TEXT("closure_thor"));ReportCase(I&&G->Installed(*I).FindRef(Slot)==Part,TEXT("gunsmith Apply + ReloadProfile: ")+Slot+TEXT("=")+Part);return;
        }
        if(InstallAttempted&&G->Apply())
        {
            G->Close();const bool Saved=M->ReloadProfile();const auto* I=M->FindItem(TEXT("closure_thor"));
            if(!Saved||!I||G->Installed(*I).FindRef(Slot)!=Part){ReportCase(false,TEXT("save reload mismatch"));return;}
            UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_LOCAL_APPLY phase=%d part=%s revision=%lld items=%d"),Current,*Part,M->Snapshot().CampfireInventoryRevision,M->Snapshot().Items.Num());
            InstalledAt=Now;return;
        }
        if(Age>30.)ReportCase(false,TEXT("gunsmith: ")+G->ApplyFeedback());return;
    }
    if(Current==14&&ThunderClosure::HostInput())
    {
        if(Age>2.&&!Pressed){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));Pressed=true;InputAt=Now;}
        if(Pressed&&!Released&&Now-InputAt>.08){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));Released=true;}
        if(Age>6.)ReportCase(!T->ThrownHammer&&T->ThunderAwayInstance.IsEmpty(),TEXT("host ordinary input recalled hammer; remote observer follows owner"));
        return;
    }
    if(Current==14||Current==15)
    {
        if(Age>1.)
        {
            int32 Cell=6;
            if(Current==14)
            {
                Cell=INDEX_NONE;
                for(int32 Candidate=0;Candidate<ColdSteelInventory::BagRows(M->Snapshot().Items)*18;++Candidate)
                    if(M->ProposeMove(TEXT("closure_thor"),0,Candidate).bValid){Cell=Candidate;break;}
            }
            const bool Moved=Cell>=0&&M->MoveItem(TEXT("closure_thor"),Current==14?0:1,Cell);
            const auto* Item=M->FindItem(TEXT("closure_thor"));
            ReportCase(Moved,FString::Printf(TEXT("MoveItem ok=%d cell=%d local_place=%d revision=%lld message=%s"),Moved,Cell,Item?Item->Place:-1,M->Snapshot().CampfireInventoryRevision,*M->ResultMessage()));
        }
        return;
    }
    if(Current==13||Current==21||Current==23)
    {
        if(Age>2.){const auto* I=M->FindItem(TEXT("closure_thor"));ReportCase(I&&G->Installed(*I).FindRef(TEXT("head_mount"))==TEXT("guan_lei_seat"),TEXT("saved current instance and seat available on client"));}return;
    }
    if(Age<2.)return;
    if(!Pressed)
    {
        if(!T->HasReadyPresentation()||T->EquipElapsed>=0.f||T->Elapsed>=0.f||T->bBluntReturningCharge)return;
        InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));Pressed=true;InputAt=GetWorld()->GetTimeSeconds();
        if(Visual&&Current==8&&!ThunderClosure::Recording){ThunderClosure::Recording=true;UAudioMixerBlueprintLibrary::StartRecordingOutput(this,30.f);}
        return;
    }
    SawCharge|=T->bThunderCallCharging;
    SawOrdinarySwing|=Released&&T->Elapsed>=0.f&&!T->bBluntHeavy;
    if(!Released&&T->bBluntCharging)InputAt=T->BluntChargeStartedAt;
    const double Held=GetWorld()->GetTimeSeconds()-InputAt;
    if(Visual&&(Current==6||Current==7||Current==8||Current==9||Current==12))
    {
        const float Times[]={.06f,.16f,.24f,.34f,.6f,1.f,1.5f,2.f,3.f,4.f};
        for(int32 N=0;N<UE_ARRAY_COUNT(Times);++N)if(Held>=Times[N])
        {const FString Name=FString::Printf(TEXT("action_%02d_%02d"),Current,N);if(!ThunderClosure::Captured.Contains(Name)){ThunderClosure::Capture(Name);break;}}
    }
    if(Current==18)
    {
        if(Held>.6&&!Sent)
        {
            const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();
            ReportCase(T->bThunderCallCharging,FString::Printf(TEXT("charging=%d pawn=%s attack=%u usable=%d equipped=%d call_seat=%d health=%.2f stamina=%.2f mana=%.2f actor_tick=%d input=%d"),
                T->bThunderCallCharging,*P->GetName(),T->BluntAttackId,T->CanUse(),T->IsEquipped(),T->bThunderCallSeat,Health?Health->Health:-1.f,M->Stamina(),M->Mana(),P->IsActorTickEnabled(),P->InputEnabled()));
        }
        return;
    }
    if(Current==10&&InputCount==0&&Held>.30)
    {
        T->CancelUse();InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));InputAt=GetWorld()->GetTimeSeconds();++InputCount;return;
    }
    // Screenshot readback can delay the following input-processing frame.
    // Keep the visual tap well inside the click window; the NullRHI network
    // scenario retains its original boundary timing without readback stalls.
    const float ReleaseAt=Current==6?(Visual?.08f:ThunderHammerCallIntent::PendingSeconds(T->BluntChargeSeconds)-.06f):
        Current==7?.32f:Current==10?.06f:Visual&&Current==9?8.f:T->BluntChargeSeconds;
    if(!Released&&(Current!=10||InputCount>0)&&Held>=ReleaseAt)
    {
        InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));Released=true;
        UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_INPUT phase=%d held=%.6f full=%.6f attack=%u charge=%d"),Current,Held,T->BluntChargeSeconds,T->BluntAttackId,SawCharge);
    }
    if(Released&&Held>ReleaseAt+3.)
    {
        if(Visual&&Current==9&&ThunderClosure::Recording){ThunderClosure::Recording=false;UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("JiLeiRuntimeCurrent"),ThunderClosure::CaptureDir()+TEXT("/"));}
        ReportCase(Current==6?!SawCharge&&SawOrdinarySwing:Current==10?SawOrdinarySwing:Current==7?SawCharge:!T->bBluntCharging,
            FString::Printf(TEXT("FirePressed/FireInputReleased held=%.4f full=%.4f attack=%u saw_charge=%d returning=%d"),ReleaseAt,T->BluntChargeSeconds,T->BluntAttackId,SawCharge,T->bBluntReturningCharge));
    }
}
AThunderHammerClosureGameMode::AThunderHammerClosureGameMode()
{PlayerControllerClass=AThunderHammerClosureController::StaticClass();PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void AThunderHammerClosureGameMode::BeginPlay()
{
    Super::BeginPlay();if(!ThunderClosure::Enabled())return;
    Started=GetWorld()->GetRealTimeSeconds();GetWorld()->SpawnActor<AKukriCombatWireFloor>(FVector(0,0,-20),FRotator::ZeroRotator);
    if(ThunderClosure::Visual())
    {
        FApp::SetUnfocusedVolumeMultiplier(1.f);
        IFileManager::Get().MakeDirectory(*ThunderClosure::CaptureDir(),true);
        auto* LightOwner=GetWorld()->SpawnActor<AActor>();
        for(int32 N=0;N<2;++N){auto* Sun=NewObject<UDirectionalLightComponent>(LightOwner);LightOwner->AddInstanceComponent(Sun);Sun->SetMobility(EComponentMobility::Movable);Sun->SetIntensity(N?1.5f:5.f);Sun->RegisterComponent();Sun->SetWorldRotation(FRotator(-35,N?-50:130,0));}
        auto* Sky=NewObject<USkyLightComponent>(LightOwner);LightOwner->AddInstanceComponent(Sky);Sky->SetMobility(EComponentMobility::Movable);Sky->SetIntensity(1.f);Sky->RegisterComponent();
        auto* Floor=GetWorld()->SpawnActor<AStaticMeshActor>();Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
        Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        Floor->SetActorLocation(FVector(0,0,-10));Floor->SetActorScale3D(FVector(200,200,.2));
    }
    ThunderClosure::Network(GetWorld());UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_HOST_READY phase=%d"),ThunderClosure::Phase);
}
void AThunderHammerClosureGameMode::PostLogin(APlayerController* P)
{Super::PostLogin(P);if(ThunderClosure::Enabled()&&(!P->IsLocalController()||ThunderClosure::LocalScenario()))Peers.Add(Cast<AThunderHammerClosureController>(P));if(ThunderClosure::Enabled())UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_LOGIN peers=%d local=%d solo=%d"),Peers.Num(),P->IsLocalController(),ThunderClosure::LocalScenario());}
void AThunderHammerClosureGameMode::Logout(AController* P)
{
    if(P==Guest){Disconnected=true;Guest=nullptr;UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_REJOIN_READY"));}
    Peers.Remove(Cast<AThunderHammerClosureController>(P));Super::Logout(P);
}
void AThunderHammerClosureGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!ThunderClosure::Enabled())return;using namespace ThunderClosure;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Now-ProbeAt>10.)
    {
        ProbeAt=Now;UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_PROBE phase=%d peers=%d guest=%d solo=%d pawn=%d tool=%d"),Phase,Peers.Num(),Guest!=nullptr,LocalScenario(),Guest&&Guest->GetPawn(),Guest&&Guest->GetPawn()&&Guest->GetPawn()->FindComponentByClass<UProductionToolComponent>());
        if(Guest&&Guest->GetPawn())if(auto* Tool=Guest->GetPawn()->FindComponentByClass<UProductionToolComponent>())
        {
            FString Missing;for(const auto& Motion:Tool->Motions)if(!Motion.Value)Missing+=Motion.Key.ToString()+TEXT(",");
            const auto* Arms=Cast<URuneSwordMeshComponent>(Tool->Viewmodel);
            UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_PRESENTATION kind=%s uses_arms=%d mesh=%s grip=%d ready=%d equip=%.3f action=%.3f returning=%d missing=%s"),
                *Tool->Kind,Tool->bUsesArms,*GetNameSafe(Tool->Viewmodel?Tool->Viewmodel->GetSkeletalMeshAsset():nullptr),Arms&&Arms->GetGripProfile(),Tool->HasReadyPresentation(),Tool->EquipElapsed,Tool->Elapsed,Tool->bBluntReturningCharge,*Missing);
            if(const auto* Health=Guest->GetPawn()->FindComponentByClass<UFPSCombatHealthComponent>())
                UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_AUTH_HEALTH pawn=%s hp=%.2f tick=%d"),*Guest->GetPawn()->GetName(),Health->Health,Guest->GetPawn()->IsActorTickEnabled());
        }
    }
    if(Now-Started>900.){Save(GetWorld());UE_LOG(LogTemp,Error,TEXT("THUNDER_CLOSURE_TIMEOUT phase=%d"),Phase);ExitAt=Now+1.;return;}
    for(const auto& C:Peers)if(C&&C->Hello){if(C->IsObserver)Observer=C;else Guest=C;}
    if(WaitingReconnect)
    {
        if(!Disconnected)return;
        int Count=0;for(TActorIterator<AThunderHammerThrown> It(GetWorld());It;++It)++Count;
        if(Phase==20){Result(GetWorld(),Count==0,TEXT("production Logout retired ground hammer"));return;}
        if(!Guest)return;WaitingReconnect=false;
    }
    if(!Guest)return;
    auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());
    auto* M=LocalScenario()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():PS?PS->ShadowModel.Get():nullptr;auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!M||!P||!G)return;
    auto* T=P->FindComponentByClass<UProductionToolComponent>();if(!T)return;
    if(!Identity.IsValid())Identity=M->Snapshot().NetworkProfileId;
    if(Prepared!=Phase)
    {
        Prepared=Phase;CaseAt=Now;LastSetup=-10.;Guest->Done=false;Waves.Reset();Killed=false;RequestAtStart=LocalScenario()?T->BluntAttackId:T->BluntLastServerRequestId;
        Network(GetWorld(),Phase==9);P->GetCharacterMovement()->StopMovementImmediately();P->GetCharacterMovement()->DisableMovement();
    }
    for(TActorIterator<AWarhammerShockwave> It(GetWorld());It;++It)if(It->GetOwner()==P)Waves.Add(*It);
    const auto* I=M->FindItem(TEXT("closure_thor"));
    if(Phase==13&&!LateRequested){LateRequested=true;UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_LATE_READY"));}
    if((Phase==16&&T->ThrownHammer&&T->ThrownHammer->IsGrounded())||(Phase==18&&Guest->Done&&Guest->ClientOK))
    {
        if(!Killed){DyingPawn=P;Killed=true;P->FindComponentByClass<UFPSCombatHealthComponent>()->ApplySurvivalDamage(100000.f);UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_LETHAL phase=%d"),Phase);}
    }
    if(Now-LastSetup>1.){LastSetup=Now;Guest->ClientPhase(Phase);}
    bool OK=false,Ready=Guest->Done;
    if(InstallCase(Phase))
    {
        const FString Slot=Phase==4||Phase==5?TEXT("grip"):TEXT("head_mount");
        const FString Part=Phase==4?TEXT("static_field_grip"):Phase==5?TEXT("coil_grip"):Seat(Phase);
        OK=I&&G->Installed(*I).FindRef(Slot)==Part;Ready&=OK||Now-CaseAt>35.;
        if(Ready&&!OK)UE_LOG(LogTemp,Error,TEXT("THUNDER_CLOSURE_SHADOW_MISMATCH item=%d installed=%s revision=%lld"),I!=nullptr,I?*G->Installed(*I).FindRef(Slot):TEXT("missing"),M->Snapshot().CampfireInventoryRevision);
    }
    else if(Phase==6||Phase==10)OK=!T->bThunderCallCharging&&!T->bBluntServerCharging&&Waves.Num()==0&&int32((LocalScenario()?T->BluntAttackId:T->BluntLastServerRequestId)-RequestAtStart)>0;
    else if(Phase==7)OK=!T->bThunderCallCharging&&!T->bBluntServerCharging&&Waves.Num()==0;
    else if(Phase==8||Phase==9)OK=Waves.Num()>0&&!T->bThunderCallCharging;
    else if(Phase==12||Phase==20||Phase==22)OK=T->ThrownHammer&&T->ThrownHammer->IsGrounded();
    else if(Phase==13){OK=Observer&&Observer->ObservedGround&&Observer->ObservedSeat;Ready&=OK;}
    else if(Phase==14&&HostInput())OK=!T->ThrownHammer&&T->ThunderAwayInstance.IsEmpty();
    else if(Phase==14){OK=I&&I->Place==0&&!T->ThrownHammer;Ready&=OK||Now-CaseAt>25.;}
    else if(Phase==15){OK=I&&I->Place==1;Ready&=OK||Now-CaseAt>25.;}
    else if(Phase==16||Phase==18){Ready=Killed&&P!=DyingPawn.Get()&&M->RuntimePawn()==P;OK=Ready&&!T->ThrownHammer&&!T->bThunderCallCharging&&P->FindComponentByClass<UFPSCombatHealthComponent>()->Health>0;}
    else if(Phase==21||Phase==23)
    {
        int Count=0;for(TActorIterator<AThunderHammerThrown> It(GetWorld());It;++It)++Count;
        OK=M->Snapshot().NetworkProfileId==Identity&&I&&G->Installed(*I).FindRef(TEXT("head_mount"))==TEXT("guan_lei_seat")&&Count==0;
    }
    if(Ready||Now-CaseAt>(HostInput()&&Phase==13?180.:60.))
    {
        const bool PassedCase=Ready&&OK&&(Phase==16||Phase==18||Guest->ClientOK);
        const FString Detail=Guest->Detail+FString::Printf(TEXT("; shadow=%s waves=%d authority=%d ready=%d item_place=%d thrown=%d"),*M->Snapshot().NetworkProfileId.ToString(),Waves.Num(),OK,Ready,I?I->Place:-1,IsValid(T->ThrownHammer));
        if(Phase==20&&PassedCase){WaitingReconnect=true;Disconnected=false;Guest->ClientExit();return;}
        const int Finished=Phase;Result(GetWorld(),PassedCase,Detail);
        if(LocalScenario()&&Phase==FinalPhase())
        {Guest->ClientExit();if(Observer)Observer->ClientExit();ExitAt=Now+3.;
            if(HostInput()){UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_FINISHED pass=%d"),Passed);}
            else {UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_LOCAL_FINISHED pass=%d"),Passed);}return;}
        if(!PassedCase){Guest->ClientExit();if(Observer)Observer->ClientExit();ExitAt=Now+3.;UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_FINISHED failed=%d"),Finished);return;}
        if(Finished==22){if(Observer)Observer->ClientExit();GetWorld()->ServerTravel(TEXT("/Engine/Maps/Entry?game=/Script/FPSGAME.ThunderHammerClosureGameMode"));return;}
        if(Phase==24){Guest->ClientExit();if(Observer)Observer->ClientExit();ExitAt=Now+3.;UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_FINISHED pass=%d"),Passed);}
    }
}
