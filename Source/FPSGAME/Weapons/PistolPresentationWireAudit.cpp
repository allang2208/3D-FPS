#include "ShotgunWireAudit.h"
#include "PistolDualWieldComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "DanWesson715WeaponAssets.h"
#include "FPSBallisticsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace ShotgunWire {void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role);}
namespace PistolWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("PistolPresentationWire"));}
const TCHAR* Definitions[]={TEXT("ue_m1911"),TEXT("ue_g18"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")};
struct FCase {int32 Model=0,Layout=0;bool Reload=false,Single=false,EmptySet=false,Expire=false,RunToEnd=false;float Time=.9f,Pitch=0.f;};
const TArray<FCase>& Cases()
{
    static const TArray<FCase> List=[]
    {
        TArray<FCase> R;
        for(int32 Model=0;Model<5;++Model)for(int32 Layout=0;Layout<3;++Layout)
        {
            FCase C;C.Model=Model;C.Layout=Layout;C.Pitch=Layout==1?30.f:-25.f;R.Add(C);
            C.Reload=true;C.Time=Model>=3?2.1f:.9f;R.Add(C);
        }
        for(int32 Model=2;Model<5;++Model){FCase C;C.Model=Model;C.Layout=2;C.Reload=true;C.RunToEnd=true;R.Add(C);}
        for(int32 Model=3;Model<5;++Model)for(float Time:{.7f,1.4f,2.1f,3.1f})
        {FCase C;C.Model=Model;C.Layout=2;C.Reload=true;C.Single=true;C.Time=Time;R.Add(C);}
        FCase Empty;Empty.Model=3;Empty.Layout=1;Empty.EmptySet=true;R.Add(Empty);
        FCase Expired;Expired.Model=4;Expired.Layout=2;Expired.Reload=true;Expired.Expire=true;Expired.Time=2.1f;R.Add(Expired);
        return R;
    }();
    return List;
}
FString Name(int32 Phase)
{
    const auto& C=Cases()[Phase];
    return FString::Printf(TEXT("%s/%s/%s/%.2f"),Definitions[C.Model],C.Layout==0?TEXT("right"):C.Layout==1?TEXT("left"):TEXT("dual"),
        C.EmptySet?TEXT("empty-set"):C.Expire?TEXT("expiry"):C.RunToEnd?TEXT("moving-reload-to-end"):C.Reload?(C.Single?TEXT("single-load"):TEXT("reload")):TEXT("hold"),C.Time);
}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id,int32 Phase)
{
    const auto& C=Cases()[Phase];auto S=Model->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=C.EmptySet?9:6;
    S.ActiveProductionTool.Reset();S.DungeonRun={};
    for(int32 Side=0;Side<2;++Side)
    {
        if(C.Layout!=2&&Side!=(C.Layout==1?1:0))continue;
        auto Item=Model->CreateItem(Definitions[C.Model]);Item.Place=1;Item.Cell=Side?8:6;
        Item.InstanceId=Id+(Side?TEXT("_L"):TEXT("_R"));Item.Magazine=C.Model==4?5:C.Model==3?6:C.Model==0?7:8;
        S.Items.Add(Item);
    }
    return S;
}
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {
        FPacketSimulationSettings Settings;Settings.PktLag=60;Settings.PktLoss=5;Driver->SetPacketSimulationSettings(Settings);
        UE_LOG(LogTemp,Display,TEXT("PISTOL_WIRE_NETWORK lag=%d loss=%d mode=%d"),Settings.PktLag,Settings.PktLoss,int32(World->GetNetMode()));
    }
#endif
}
bool Visible(const UStaticMeshComponent* Part){return Part&&Part->IsVisible()&&!Part->bHiddenInGame;}
}

void AShotgunWireAuditController::PosePistolPresentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Initialize)
{
    if(!Pawn)return;const auto& C=PistolWire::Cases()[Phase];
    Pawn->SetActorTickEnabled(false);auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    Move->SetComponentTickEnabled(false);Move->DisableMovement();Move->StopMovementImmediately();Move->bWantsToAim=!C.Reload;
    // The fixture freezes movement, so no autonomous movement RPC can drive
    // the authority pawn's pose. Release that timing ownership explicitly;
    // its ordinary mesh tick still evaluates the production animation graph.
    Move->Deactivate();Pawn->UpdateMeshAllowAutonomousTickPose();
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Pawn->Ballistics->SetComponentTickEnabled(false);Pawn->bIsSprinting=false;Pawn->SprintPoseFactor=0.f;
    Pawn->bIsAiming=!C.Reload;Pawn->WeaponADSFactor=C.Reload?0.f:1.f;
    if(auto* Controller=Pawn->GetController())Controller->SetControlRotation(FRotator(C.Pitch,15.f,0.f));
    Pawn->FirstPersonCamera->SetWorldRotation(FRotator(C.Pitch,15.f,0.f));
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Pawn->IsLocallyControlled())return;
    if(Initialize)
    {
        Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;Pawn->DualPistols->InterruptActions();
        Pawn->UpdateActionPose(0.f);
        if(Pawn->DualPistols->IsActive())for(int32 Side=Pawn->DualPistols->IsPair()?0:1;Side<2;++Side)Pawn->DualPistols->Pose(Side,0.f);
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
    }
    if(C.EmptySet)return;
    if(C.Layout==0)
    {
        auto* Clip=C.Reload?Pawn->ReloadAnimation.Get():Pawn->IdleAnimation.Get();if(!Clip)return;
        if(Initialize&&C.Reload)Pawn->WeaponActionStartedAt=Pawn->GetWorld()->GetTimeSeconds()-C.Time;
        Pawn->WeaponState=C.Reload?EAKMWeaponState::Reloading:EAKMWeaponState::Idle;
        Pawn->ActiveActionAnimation=C.Reload?Clip:nullptr;Pawn->ActionStartPosition=0.f;Pawn->ActionPlayRate=0.f;
        Pawn->WeaponStateDuration=Pawn->ActionDuration=Clip->GetPlayLength();
        Pawn->WeaponStateElapsed=Pawn->ActionElapsed=C.Reload?FMath::Min(C.Time,Clip->GetPlayLength()-.05f):0.f;
        Pawn->UpdateActionPose(0.f);Pawn->AKMViewmodel->TickAnimation(0.f,false);
        Pawn->AKMViewmodel->RefreshBoneTransforms();Pawn->AKMViewmodel->UpdateChildTransforms();
    }
    else for(int32 Side=C.Layout==2?0:1;Side<2;++Side)
    {
        auto& Hand=Pawn->DualPistols->Hands[Side];
        const FString Role=!C.Reload?TEXT("idle"):Hand.Revolver?(C.Single?TEXT("single_0_1"):TEXT("speed_0")):TEXT("reload");
        auto* Clip=Hand.Clips.FindRef(Role).Get();if(!Clip)continue;
        if(Initialize&&C.Reload)Pawn->DualPistols->StartAction(Side,Role,1.f);
        Hand.ActionRate=0.f;
        Hand.ReloadSpeedloader=C.Reload&&Hand.Revolver&&!C.Single;
        Hand.ReloadStart=0;Hand.ReloadCount=C.Single?1:Hand.Stats.Capacity;
        Hand.SourceLength=Hand.Revolver?(C.Single?DanWesson715WeaponAssets::SingleDuration(1,true):3.85f):1.75f;
        const auto* Fixture=Cast<AShotgunWireAuditController>(Pawn->GetController());
        const bool ObserversReady=!C.RunToEnd||(Fixture&&Fixture->bPistolObserverReady);
        const float Time=C.RunToEnd&&ObserversReady?FMath::Max(0.f,float(Pawn->GetWorld()->GetTimeSeconds()-Hand.ActionStarted)-1.f):C.RunToEnd?0.f:C.Time;
        Hand.Reloading=C.Reload&&ObserversReady&&(!C.RunToEnd||(Pawn->GetWorld()->GetTimeSeconds()-Hand.ActionStarted>=1.&&Time<Hand.SourceLength));
        Hand.Action=Hand.Reloading?Clip:nullptr;
        Hand.ActionTime=Hand.Reloading?FMath::Min(Time/Hand.SourceLength,.999f)*Clip->GetPlayLength():0.f;
        Hand.ActionBlendStarted=Pawn->GetWorld()->GetTimeSeconds()-1.;Hand.Rounds=0;Hand.Cases=Hand.Stats.Capacity;
        if(C.RunToEnd)
        {
            const float Seat=Hand.Revolver?DanWesson715WeaponAssets::Seat/3.6f*3.85f:1.05f;
            const float Eject=Hand.Revolver?DanWesson715WeaponAssets::Eject/3.6f*3.85f:.3167f;
            Hand.Rounds=Time>=Seat?Hand.Stats.Capacity:0;Hand.Cases=Time>=Eject?Hand.Rounds:Hand.Stats.Capacity;
        }
        // Hold a deterministic native source frame. The body component still
        // captures, transmits, validates, replicates and consumes it normally.
        Pawn->DualPistols->Pose(Side,0.f);Hand.Mesh->TickAnimation(0.f,false);Hand.Mesh->RefreshBoneTransforms();Hand.Mesh->UpdateChildTransforms();
    }
}

bool AShotgunWireAuditController::CheckPistolPresentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Expired,TSharedPtr<FJsonObject> Row)
{
    const auto& C=PistolWire::Cases()[Phase];auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    bool Passed=true;Row->SetStringField(TEXT("case"),PistolWire::Name(Phase));
    const auto Check=[&](const TCHAR* Key,bool Value){Row->SetBoolField(Key,Value);Passed&=Value;};
    Check(TEXT("body_present"),Body&&Body->BodyAnimation);if(!Body||!Body->BodyAnimation)return false;
    Check(TEXT("fixture_mesh_ticks_without_movement"),!Body->GetBodyMesh()->bOnlyAllowAutonomousTickPose);
    const auto& State=Body->ReplicatedState;const auto& Display=Body->DisplayState;
    const int32 Count=C.EmptySet?0:C.Layout==2?2:1;
    Check(TEXT("equipment_count"),Body->MotionBindings.Num()==Count);Row->SetNumberField(TEXT("world_guns"),Body->MotionBindings.Num());
    if(C.EmptySet)
    {
        Check(TEXT("empty_identity"),State.WeaponInstance.IsEmpty()&&State.OffhandInstance.IsEmpty()&&!State.bOffhandPistol&&!State.bDual);
        Check(TEXT("reload_stopped"),!State.LeftHand.bReloading&&!State.RightHand.bReloading);Row->SetBoolField(TEXT("passed"),Passed);return Passed;
    }
    Check(TEXT("loadout_roles"),State.bDual==(C.Layout==2)&&State.bOffhandPistol==(C.Layout!=0)&&
        State.Family==FName(C.Layout==1?TEXT("Unarmed"):TEXT("Pistol")));
    Check(TEXT("stationary_aim"),FMath::IsNearlyEqual(State.AimPitch,C.Pitch,1.f));
    Row->SetNumberField(TEXT("aim_pitch"),State.AimPitch);
    Check(TEXT("support_role"),C.Layout==2?(!Body->BodyAnimation->bHasLeftGrip&&!Body->BodyAnimation->bHasRightGrip):
        C.Layout==1?Body->BodyAnimation->bHasRightGrip:Body->BodyAnimation->bHasLeftGrip);
    const bool ExpectedReload=C.Reload&&!C.RunToEnd&&!Expired;
    double WorstContact=0.,WorstWrist=0.;bool Finite=true,Clock=true,Props=true;
    for(int32 I=0;I<Body->MotionBindings.Num();++I)
    {
        const auto& B=Body->MotionBindings[I];const int32 Side=B.Definition.AttachHand;
        const FName W=Side?TEXT("hand_l"):TEXT("hand_r"),E=Side?TEXT("lowerarm_l"):TEXT("lowerarm_r");
        Check(*FString::Printf(TEXT("rig_%d_matches"),I),Expired?!Body->HasMatchingMotionRig(I):Body->HasMatchingMotionRig(I));
        Check(*FString::Printf(TEXT("rig_%d_socket"),I),B.Mesh.IsValid()&&B.Mesh->GetAttachSocketName()==W);
        const auto Wrist=Body->GetBodyMesh()->GetSocketTransform(W,RTS_Component);
        const auto Elbow=Body->GetBodyMesh()->GetSocketTransform(E,RTS_Component);
        const auto& Skeleton=Body->GetBodyMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
        const FQuat HandBind=Skeleton.GetRefBonePose()[Skeleton.FindBoneIndex(W)].GetRotation();
        WorstWrist=FMath::Max(WorstWrist,FMath::RadiansToDegrees((Elbow.GetRotation()*HandBind).AngularDistance(Wrist.GetRotation())));
        Finite&=!Wrist.ContainsNaN()&&Wrist.GetScale3D().GetMin()>0.&&B.Mesh.IsValid();
        if(C.Layout!=2)
        {
            const auto* Anim=Body->BodyAnimation.Get();
            const bool Native=Anim->UsesNativeSinglePistolSource();
            const bool ContactRequired=!ExpectedReload||!Native||C.Model<3;
            Row->SetBoolField(TEXT("support_contact_required"),ContactRequired);
            FTransform Relation=Native?Anim->SinglePistolContact.Ready:(Side?Anim->RightGripFromLeft:Anim->LeftGripFromRight);
            if(Native&&ExpectedReload&&C.Model<3)
            {
                Check(TEXT("magazine_contact_phase"),Anim->SinglePistolContact.OperationWeight>.99f);
                Relation=Anim->SinglePistolContact.Operation;
            }
            if(ContactRequired)WorstContact=FMath::Max(WorstContact,FVector::Distance((Relation*Body->GetBodyMesh()->GetSocketTransform(W)).GetLocation(),
                Body->GetBodyMesh()->GetSocketLocation(Side?TEXT("hand_r"):TEXT("hand_l"))));
        }
        // All layouts carry a per-hand clock, including primary single. Held
        // samples last four seconds: an epoch younger than 2.5 s is still
        // following the frozen source time and would flood reliable edges.
        {
            const auto& Hand=Side?State.LeftHand:State.RightHand;
            Clock&=Hand.bReloading==ExpectedReload;
            if(ExpectedReload)Clock&=Body->ServerClock()-Hand.ReloadStartedAt>2.5f;
            if(ExpectedReload)Clock&=Hand.ReloadSourceLength>0.f&&FMath::Abs(Hand.Progress*Hand.ReloadSourceLength-C.Time)<.06f
                &&Hand.bRevolver==(C.Model>=3)&&Hand.bSpeedloaderReload==(C.Model>=3&&!C.Single);
        }
        if(C.Layout==2&&C.Model>=3)
        {
            Props&=B.Revolver.bPrepared;int32 VisibleRounds=0;for(const auto& Part:B.Revolver.IncomingRounds)VisibleRounds+=PistolWire::Visible(Part.Get());
            Row->SetNumberField(*FString::Printf(TEXT("hand_%d_incoming_rounds"),Side),VisibleRounds);
            Row->SetBoolField(*FString::Printf(TEXT("hand_%d_loader"),Side),PistolWire::Visible(B.Revolver.Loader.Get()));
            if(!ExpectedReload)Props&=VisibleRounds==0&&!PistolWire::Visible(B.Revolver.Loader.Get());
            else if(!C.Single&&C.Time==2.1f)Props&=VisibleRounds==B.Revolver.Cases.Num()&&PistolWire::Visible(B.Revolver.Loader.Get());
        }
        if(C.Layout==2&&C.Model<3&&ExpectedReload)Props&=B.bMagazineOverride&&!B.bMagazineHidden;
    }
    Row->SetNumberField(TEXT("support_error_cm"),WorstContact);Row->SetNumberField(TEXT("wrist_angle_deg"),WorstWrist);
    Row->SetNumberField(TEXT("drop_magazines"),Body->DroppedPistolMagazines.Num());Row->SetNumberField(TEXT("drop_cases"),Body->DroppedRevolverCases.Num());
    Check(TEXT("finite_transforms"),Finite);Check(TEXT("support_contact"),WorstContact<1.);
    Check(TEXT("hand_clocks"),Clock);Check(TEXT("reload_props"),Props);
    if(C.RunToEnd)Check(TEXT("observed_release"),C.Model>=3?Body->DroppedRevolverCases.Num()>0:Body->DroppedPistolMagazines.Num()>0);
    if(Expired)Check(TEXT("expired_action"),Display.Action==EFPSBodyAction::None&&!Display.LeftHand.bReloading&&!Display.RightHand.bReloading);
    Row->SetBoolField(TEXT("passed"),Passed);return Passed;
}

void AShotgunWireAuditController::SetupPistolPresentation(int32 Phase,const FString& Id,AFPSGAMECharacter* Host)
{
    if(HasAuthority()||Current==Phase||!Host)return;
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Subject||!Model||!Model->IsAudit())return;
    if(Current<0)PistolWire::Network(GetWorld());
    Model->Current=PistolWire::Seed(Model,Id,Phase);Model->CurrentPawn=Subject;Subject->ApplyColdSteelProfile(Model);
    Subject->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);
    ObserverSubject=Host;Current=Phase;Weapon=Id;Started=GetWorld()->GetRealTimeSeconds();bReported=false;
    bSent=!PistolWire::Cases()[Phase].RunToEnd;bPistolObserverReady=bSent;
    PosePistolPresentation(Subject,Phase,true);
    if(Phase==4)if(auto* PS=Subject->GetPlayerState<AColdSteelPlayerState>())
    {
        // Actual owning-client reliable RPCs under this fixture's lag/loss.
        // No damage target: both are misses and must still debit independently.
        PS->ServerRememberPistolShot(1001,Id+TEXT("_R"),6,1,Subject);
        PS->ServerRememberPistolShot(1002,Id+TEXT("_L"),6,1,Subject);
        PS->ServerRememberPistolShot(1002,Id+TEXT("_L"),6,1,Subject);
    }
    Subject->FindComponentByClass<UFPSPlayerBodyComponent>()->SetComponentTickEnabled(true);
    UE_LOG(LogTemp,Display,TEXT("PISTOL_WIRE_CLIENT_SETUP phase=%d %s"),Phase,*PistolWire::Name(Phase));
}
bool AShotgunWireAuditController::TickPistolPresentation(float Delta)
{
    if(!PistolWire::Enabled())return false;Super::Tick(Delta);
    if(HasAuthority()||!IsLocalController())return true;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(Current<0||bReported)return true;
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());
    if(!bSent)
    {
        auto* Observed=ObserverSubject?ObserverSubject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
        bool Ready=Observed&&Observed->MotionBindings.Num()==2&&
            Observed->DisplayState.WeaponInstance.StartsWith(TEXT("Host_")+Weapon);
        if(Ready)for(int32 I=0;I<Observed->MotionBindings.Num();++I)Ready&=Observed->HasMatchingMotionRig(I);
        if(!Ready)return true;
        bSent=bPistolObserverReady=true;Started=Now;
        for(auto& Hand:Subject->DualPistols->Hands)Hand.ActionStarted=Subject->GetWorld()->GetTimeSeconds();
        ServerReady(Current);
    }
    PosePistolPresentation(Subject,Current);
    if(PistolWire::Cases()[Current].Expire&&Now-Started>1.)Subject->FindComponentByClass<UFPSPlayerBodyComponent>()->SetComponentTickEnabled(false);
    if(Now-Started<(PistolWire::Cases()[Current].RunToEnd?7.:4.))return true;
    auto Row=MakeShared<FJsonObject>();const bool OK=CheckPistolPresentation(ObserverSubject,Current,false,Row);
    Row->SetNumberField(TEXT("phase"),Current);Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=OK;bReported=true;
    FString Report;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Report));ServerPistolResult(Current,Report);
    ShotgunWire::Save(Results,bAllPassed,TEXT("client"));return true;
}

void AShotgunWireAuditController::ReadyPistolPresentation(int32 Phase)
{
    if(!PistolWire::Enabled()||Phase!=Expected||Phase!=Finished||bPistolObserverReady)return;
    bPistolObserverReady=true;
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=Cast<AShotgunWireAuditController>(It->Get());PC&&PC->IsLocalController())
        {
            PC->bPistolObserverReady=true;
            if(auto* SubjectPawn=Cast<AFPSGAMECharacter>(PC->GetPawn()))
                for(auto& Hand:SubjectPawn->DualPistols->Hands)Hand.ActionStarted=GetWorld()->GetTimeSeconds();
        }
}
void AShotgunWireAuditController::ServerPistolResult_Implementation(int32 Phase,const FString& Report)
{
    if(!PistolWire::Enabled()||Phase!=Expected||Finished!=Phase)return;
    TSharedPtr<FJsonObject> Observer;const bool Parsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Report),Observer);
    auto Row=MakeShared<FJsonObject>();bool ServerOK=CheckPistolPresentation(Cast<AFPSGAMECharacter>(GetPawn()),Phase,PistolWire::Cases()[Phase].Expire,Row);
    if(Phase==4)
    {
        auto* PS=GetPlayerState<AColdSteelPlayerState>();
        const auto* Right=PS&&PS->ShadowModel?PS->ShadowModel->Equipped(6):nullptr;
        const auto* Left=PS&&PS->ShadowModel?PS->ShadowModel->Equipped(8):nullptr;
        const auto* R=Right?PS->ServerGunLedgers.Find(Right->InstanceId):nullptr;
        const auto* L=Left?PS->ServerGunLedgers.Find(Left->InstanceId):nullptr;
        const bool Paid=R&&L&&R->Magazine==6&&L->Magazine==6;
        Row->SetBoolField(TEXT("same_model_reliable_shot_debits_both_and_ignores_duplicate"),Paid);
        Row->SetNumberField(TEXT("right_server_rounds"),R?R->Magazine:-1);
        Row->SetNumberField(TEXT("left_server_rounds"),L?L->Magazine:-1);
        ServerOK&=Paid;Row->SetBoolField(TEXT("passed"),ServerOK);
    }
    bool ObserverOK=false;if(Parsed)Observer->TryGetBoolField(TEXT("passed"),ObserverOK);
    Row->SetNumberField(TEXT("phase"),Phase);Row->SetBoolField(TEXT("client_observer_passed"),ObserverOK);
    if(Parsed)Row->SetObjectField(TEXT("client_observer"),Observer);
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=ObserverOK&&ServerOK;++Finished;
    UE_LOG(LogTemp,Display,TEXT("PISTOL_WIRE_CASE phase=%d client=%d server=%d"),Phase,ObserverOK,ServerOK);
}
bool AShotgunWireAuditGameMode::TickPistolPresentation(float Delta)
{
    if(!PistolWire::Enabled())return false;Super::Tick(Delta);const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(!Guest)return true;
    auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Pawn||!PS||!Model||!Model->IsAudit())return true;
    if(!HostPawn)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())HostPawn=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    if(!HostPawn)return true;
    const int32 Total=PistolWire::Cases().Num();
    if(PresentationConnections==1&&Guest->Finished==0)Guest->Finished=Total-4;
    if(Guest->Finished>=Total||Now-Joined>650.)
    {
        bPresentationPassed&=Guest->Finished==Total&&Guest->bAllPassed;PresentationHistory.Append(Guest->Results);
        Guest->ClientFinish(Guest->Finished==Total&&Guest->bAllPassed);++PresentationConnections;
        if(PresentationConnections==1){Guest=nullptr;Prepared=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("PISTOL_WIRE_REJOIN_READY"));return true;}
        ShotgunWire::Save(PresentationHistory,bPresentationPassed,TEXT("listen_host"));ExitAt=Now+3.;return true;
    }
    if(Prepared!=Guest->Finished)
    {
        if(Prepared==INDEX_NONE)PistolWire::Network(GetWorld());
        Prepared=Guest->Finished;Weapon=FGuid::NewGuid().ToString();Guest->Expected=Prepared;
        Guest->bPistolObserverReady=false;
        if(auto* HostPC=Cast<AShotgunWireAuditController>(HostPawn->GetController()))HostPC->bPistolObserverReady=!PistolWire::Cases()[Prepared].RunToEnd;
        const auto Seed=PistolWire::Seed(Model,Weapon,Prepared);
        if(!PS->ShadowModel)PS->ShadowModel=Model->CreateShadowModel(Seed);else PS->ShadowModel->Current=Seed;
        PS->ShadowModel->CurrentPawn=Pawn;Pawn->NetShadowProfile=PS->ShadowModel;Pawn->ApplyColdSteelProfile(PS->ShadowModel);
        Model->Current=PistolWire::Seed(Model,TEXT("Host_")+Weapon,Prepared);Model->CurrentPawn=HostPawn;HostPawn->ApplyColdSteelProfile(Model);
        Pawn->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);HostPawn->SetActorLocationAndRotation(FVector(0,1000,500),FRotator::ZeroRotator);
        AShotgunWireAuditController::PosePistolPresentation(Pawn,Prepared,true);
        AShotgunWireAuditController::PosePistolPresentation(HostPawn,Prepared,true);
        for(auto* C:{Pawn,HostPawn.Get()})if(auto* B=C->FindComponentByClass<UFPSPlayerBodyComponent>())
        {B->SetComponentTickEnabled(true);B->DisplayState=C->IsLocallyControlled()?B->SampleLocalState():B->SampleRemoteAuthorityState();B->CaptureEquipment();}
        LastSetup=-10;
    }
    AShotgunWireAuditController::PosePistolPresentation(Pawn,Prepared);
    AShotgunWireAuditController::PosePistolPresentation(HostPawn,Prepared);
    if(Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetup(Prepared,Weapon,HostPawn);}
    return true;
}
