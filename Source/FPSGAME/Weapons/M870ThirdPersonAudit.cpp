#include "ShotgunAttachmentAuditCommandlet.h"
#include "M870WeaponAssets.h"
#include "M870FurnitureAssets.h"
#include "TacticalDeviceComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Characters/FPSBodyRifleHold.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/NameAsStringProxyArchive.h"

// Explicit, isolated regression scope. No profile save, map play, screenshot,
// damage or ammo operation. RPC implementations are invoked without sockets.
int32 UShotgunAttachmentAuditCommandlet::RunM870PresentationAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=M870Presentation_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("M870PresentationAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit())return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool Pass,const TCHAR* Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),Pass);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("M870_PRESENTATION %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Base=Model->Snapshot();Base.Items.Reset();Base.ActiveWeaponSlot=6;Base.ActiveProductionTool.Reset();Base.DungeonRun={};
    auto Item=Model->CreateItem(M870WeaponAssets::Definition);Item.Place=1;Item.Cell=6;Item.Magazine=7;Base.Items={Item};Model->Current=Base;
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Pawn);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pawn->DispatchBeginPlay();
    Model->CurrentPawn=Pawn;Pawn->ApplyColdSteelProfile(Model);Pawn->WeaponState=EAKMWeaponState::Idle;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!Body->BodyAnimation||!Pawn->IdleAnimation||!Pawn->FireAnimation)return 2;
    Pawn->SetGunsmithTactical(TEXT("laser"),FString());Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
    Check(Body->BodyAnimation->RifleHold.bValid&&Body->BodyAnimation->bHasLeftGrip,TEXT("owner M870 has calibrated shoulder and two-hand grip"));
    Check(Body->MotionBindings.Num()==1,TEXT("single M870 world rig"));
    if(Body->MotionBindings.Num()!=1)return 2;
    const auto Definition=Body->MotionBindings[0].Definition;
    auto* Weapon=Body->MotionBindings[0].Mesh.Get();
    const FTransform Root=Weapon->GetSocketTransform(TEXT("WPN_root"),RTS_Component);
    const FVector Sight=(Weapon->GetSocketLocation(TEXT("WPN_FrontSight"))-Weapon->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    const auto Hold=Body->BodyAnimation->RifleHold;
    const FVector Fitted=Weapon->GetAttachParent()->GetSocketQuaternion(TEXT("hand_r")).RotateVector(Hold.BarrelInHand.GetForwardVector());
    Check(FVector::DotProduct(Sight,Fitted)>.9999,TEXT("measured M870 barrel agrees with hold axis"));
    for(const TCHAR* Id:{TEXT("skeleton"),TEXT("core_stock"),TEXT("qr_performance"),TEXT("tactical_telescopic"),TEXT("legendary_adjustable_tactical_stock")})
    {
        auto D=Definition;D.Parts.Reset();auto& Part=D.Parts.AddDefaulted_GetRef();
        // CaptureWeapon stores an object path from the loaded component, not
        // the package-only string accepted by the furniture loader.
        auto* Stock=LoadObject<UStaticMesh>(nullptr,*M870FurnitureAssets::MeshPath(Id));
        Part.Mesh=Stock;Part.Socket=TEXT("WPN_root");
        Part.RelativeTransform=Root.Inverse();
        const auto H=BuildFPSBodyRifleHold(*Weapon,D);
        UE_LOG(LogTemp,Display,TEXT("M870_STOCK %s contact=%s factory=%s"),Id,*H.StockInHand.ToString(),*Hold.StockInHand.ToString());
        Check(Stock&&H.bValid&&!H.StockInHand.ContainsNaN()&&!H.StockInHand.Equals(Hold.StockInHand,.01),
            *FString::Printf(TEXT("replacement stock %s has measured shoulder contact"),Id));
    }

    auto* Source=Pawn->AKMViewmodel.Get();Source->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    const auto Sample=[&](UAnimSequence* Clip,float Time,bool Pump)
    {
        Source->PlayAnimation(Clip,false);Source->SetPlayRate(0.f);Source->SetPosition(Time,false);Source->TickAnimation(0.f,false);Source->RefreshBoneTransforms();Source->UpdateChildTransforms();
        Pawn->ActiveActionAnimation=Pump?Pawn->FireAnimation.Get():nullptr;Pawn->ActionDuration=.9f;Pawn->LastShotWorldTime=World->GetTimeSeconds();
        auto S=Body->SampleLocalState();Body->CaptureMotion(S);return S;
    };
    const auto Idle=Sample(Pawn->IdleAnimation,0.f,false),Pump=Sample(Pawn->FireAnimation,.35f,true);
    Check(Idle.Contacts.HasSupportGrip&&Pump.Contacts.HasSupportGrip&&Pump.Contacts.Wrists==0
        &&FVector::Distance(Idle.Contacts.SupportGrip.GetLocation(),Pump.Contacts.SupportGrip.GetLocation())>5.f,
        TEXT("pump moves support grip while body still owns wrists"));
    Check(Pump.Contacts.Channel==TEXT("Pump")&&Pump.Action==EFPSBodyAction::None,TEXT("pump network channel preserves gameplay Idle"));
    Check(Pawn->IsWeaponBusy()&&!Pawn->IsWeaponBusyForAim(),TEXT("pump locks fire while preserving ADS and laser aim gate"));
    auto Sent=Pump.Contacts;TArray<uint8> Bytes;bool Saved=false,Loaded=false;
    {FMemoryWriter Memory(Bytes);FNameAsStringProxyArchive Archive(Memory);Sent.NetSerialize(Archive,nullptr,Saved);}
    FFPSBodyMotionSample Received;
    {FMemoryReader Memory(Bytes);FNameAsStringProxyArchive Archive(Memory);Received.NetSerialize(Archive,nullptr,Loaded);}
    Check(Saved&&Loaded&&Received.IsSane()&&Received.Channel==TEXT("Pump")&&Received.HasSupportGrip
        &&Received.SupportGrip.GetLocation().Equals(Sent.SupportGrip.GetLocation(),.02)
        &&Received.Rigs.Num()==Sent.Rigs.Num()&&Received.Rigs[0].Schema==Sent.Rigs[0].Schema,
        TEXT("production NetSerialize roundtrip retains pump grip and rig identity"));
    Body->DisplayState=Pump;Body->DisplayState.LastShotAt=Body->ServerClock()-.35f;
    Body->PreviousLocalPresentation=Body->DisplayState;Body->bHasLocalPresentation=true;Body->PresentationSendCountdown=0.f;
    Body->SendBodyPresentation(.016f);
    Check(FMath::IsNearlyEqual(Body->PresentationSendCountdown,.04f),TEXT("listen-host pump keeps 25 Hz beyond initial recoil"));
    Body->DisplayState=Pump;Body->ApplyMotion(.016f);
    Check(Body->HasMatchingMotionRig(0)&&Body->BodyAnimation->LeftGripFromRight.Equals(Pump.Contacts.SupportGrip,.001),TEXT("matching pump drives the support hand"));
    Body->DisplayState.WeaponInstance=TEXT("different-copy-of-M870");Body->ApplyMotion(.016f);
    Check(!Body->HasMatchingMotionRig(0)&&Body->BodyAnimation->LeftGripFromRight.Equals(Body->BaseSupportGrip,.001),TEXT("same-schema different gun cannot inherit old pump"));
    Body->DisplayState=Pump;Body->DisplayState.Contacts.Rigs[0].Schema^=1;Body->ApplyMotion(.016f);
    Check(!Body->HasMatchingMotionRig(0)&&Body->BodyAnimation->LeftGripFromRight.Equals(Body->BaseSupportGrip,.001),TEXT("out-of-order equipment schema rejects support grip"));
    Body->DisplayState=Pump;Body->ApplyMotion(.016f);Body->RebuildWeapons(Body->LocalWeapons);
    Check(!Body->bMotionSampleValid&&!Body->SmoothedContacts.HasSupportGrip,TEXT("equipment rebuild clears previous grip interpolation"));

    auto* RemotePC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,500),FRotator::ZeroRotator);
    PS->SetOwner(RemotePC);RemotePC->SetPlayerState(PS);RemotePC->Possess(Remote);Remote->SetPlayerState(PS);
    auto* Shadow=Model->CreateShadowModel(Base);PS->ShadowModel=Shadow;Remote->NetShadowProfile=Shadow;Shadow->CurrentPawn=Remote;
    Remote->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Remote->DispatchBeginPlay();Remote->ApplyColdSteelProfile(Shadow);
    Remote->SetGunsmithTactical(TEXT("laser"),FString());
    auto* RemoteBody=Remote->FindComponentByClass<UFPSPlayerBodyComponent>();
    RemoteBody->DisplayState=RemoteBody->SampleRemoteAuthorityState();RemoteBody->CaptureEquipment();
    Check(!Remote->IsLocallyControlled()&&RemoteBody->BodyAnimation&&RemoteBody->BodyAnimation->RifleHold.bValid,TEXT("remote authority builds calibrated M870"));
    RemotePC->SetControlRotation(FRotator(32.f,18.f,0));
    auto* Move=Cast<UFPSCharacterMovementComponent>(Remote->GetCharacterMovement());Move->bWantsToAim=true;
    auto Incoming=Pump;Incoming.Contacts=Received;Incoming.AimPitch=-60.f;Incoming.bAiming=false;
    Incoming.PresentationSampledAt=RemoteBody->ServerClock();RemoteBody->AcceptBodyPresentation(Incoming,10);
    Check(RemoteBody->ReplicatedState.Contacts.Channel==TEXT("Pump")&&RemoteBody->ReplicatedState.Contacts.HasSupportGrip
        &&FMath::IsNearlyEqual(RemoteBody->ReplicatedState.AimPitch,32.f)&&RemoteBody->ReplicatedState.bAiming,
        TEXT("authority relays pump but derives aim from controller and movement"));
    RemoteBody->ApplyMotion(1.f);
    Check(RemoteBody->HasMatchingMotionRig(0)&&RemoteBody->BodyAnimation->LeftGripFromRight.GetLocation().Equals(Received.SupportGrip.GetLocation(),.02),
        TEXT("remote world rig consumes owner support and mechanical sample together"));
    auto Old=Incoming;Old.Contacts=Idle.Contacts;RemoteBody->AcceptBodyPresentation(Old,9);
    Check(RemoteBody->ReceivedPresentationSequence==10&&RemoteBody->ReplicatedState.Contacts.Channel==TEXT("Pump"),TEXT("older snapshot cannot rewind accepted pump"));
    auto Wrong=Incoming;Wrong.WeaponInstance=TEXT("old-gun");RemoteBody->AcceptBodyPresentation(Wrong,11);
    Check(!RemoteBody->ReplicatedState.Contacts.HasSupportGrip,TEXT("authority rejects old weapon contacts"));
    RemoteBody->AcceptBodyPresentation(Incoming,12);
    RemoteBody->LastPresentationReceivedAt=RemoteBody->ServerClock()-.61f;
    Check(!RemoteBody->SampleRemoteAuthorityState().Contacts.HasSupportGrip,TEXT("missing end or owner timeout clears pump contacts"));
    int32 LaserPart=INDEX_NONE;
    for(int32 I=0;I<RemoteBody->LocalWeapons[0].Parts.Num();++I)
        if(RemoteBody->LocalWeapons[0].Parts[I].TacticalKind==TEXT("laser")){LaserPart=I;break;}
    Check(LaserPart!=INDEX_NONE,TEXT("remote M870 manifest has real laser part"));
    if(LaserPart!=INDEX_NONE)
    {
        auto LaserState=RemoteBody->SampleRemoteAuthorityState();auto& L=LaserState.Lasers.AddDefaulted_GetRef();
        L.PartIndex=LaserPart;L.Schema=RemoteBody->LocalWeapons[0].MotionSchema;
        L.End=Remote->GetActorLocation()+FVector(1000,0,0);L.Normal=FVector(-1,0,0);L.bDot=true;
        RemoteBody->SanitizeLaserPresentation(LaserState);
        Check(LaserState.Lasers.Num()==1,TEXT("authority accepts matching owner laser endpoint"));
        RemoteBody->DisplayState=LaserState;RemoteBody->DisplayState.PresentationSampledAt=RemoteBody->ServerClock();FFPSBodyLaserSample Out;
        Check(RemoteBody->ResolveLaserSample(0,LaserPart,RemoteBody->LocalWeapons[0].MotionSchema,Out)
            &&FVector(Out.End).Equals(Remote->GetActorLocation()+FVector(1000,0,0),.02),TEXT("observer uses owner endpoint without retracing aim"));
        RemoteBody->DisplayState.PresentationSampledAt-=.61f;
        Check(!RemoteBody->ResolveLaserSample(0,LaserPart,RemoteBody->LocalWeapons[0].MotionSchema,Out),TEXT("stale laser sample turns off"));
        auto WrongLaser=LaserState;WrongLaser.Lasers[0].Schema^=1;RemoteBody->SanitizeLaserPresentation(WrongLaser);
        Check(WrongLaser.Lasers.IsEmpty(),TEXT("wrong laser layout rejected"));
        WrongLaser=LaserState;WrongLaser.WeaponInstance=TEXT("old-gun");RemoteBody->SanitizeLaserPresentation(WrongLaser);
        Check(WrongLaser.Lasers.IsEmpty(),TEXT("old gun laser rejected"));
    }
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("checks"),Rows.Num());Result->SetNumberField(TEXT("failures"),Failures);Result->SetArrayField(TEXT("results"),Rows);
    Result->SetStringField(TEXT("mode"),TEXT("isolated real assets, contact NetSerialize, authority/observer entrypoints; no socket transport or rendered acceptance"));
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    const FString Path=FPaths::ProjectSavedDir()/TEXT("M870ThirdPersonReview20261018/result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    Model->CurrentPawn.Reset();Shadow->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {
        It->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);
        for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);
    }
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
