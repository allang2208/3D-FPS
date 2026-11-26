#include "../ShotgunWireAudit.h"
#include "BowWeaponComponent.h"
#include "BowArmsMeshComponent.h"
#include "BowFlexMeshComponent.h"
#include "BowPartComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Characters/FPSPlayerBodyAnimInstance.h"
#include "../../Characters/FPSBodyBowMotion.h"
#include "../../Characters/BowPresentationAuditContact.h"
#include "../../Movement/FPSCharacterMovementComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

#include "BowFlightWire.inl"

namespace ShotgunWire { void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role); }
namespace SparrowWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("BowSparrowWire"));}
bool Handoff(){return FParse::Param(FCommandLine::Get(),TEXT("BowHandoffWire"));}
bool Peakwatch(){return FParse::Param(FCommandLine::Get(),TEXT("PeakwatchWire"));}
int32 Cases(){return (Peakwatch()||BowFlightWire::Enabled())?2:Handoff()?14:9;}
float Zoom(bool Host,int32 Phase){return Host==(Phase==0)?3.f:6.f;}
float Pitch(int32 P){return P==1?35.f:P==2?-35.f:P==4?50.f:0.f;}
FName Clip(int32 P){return P==0||P>=9?TEXT("Idle"):P==1||P==4?TEXT("Draw"):P==3?TEXT("Release"):P==5?TEXT("LoadedIdle"):TEXT("Hold");}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id,int32 Phase)
{
    auto S=Model->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.DungeonRun={};
    const bool Mountain=BowFlightWire::Enabled()&&Phase==1;
    const bool Frontier=BowFlightWire::Frontier();
    auto Item=Model->CreateItem(Frontier?TEXT("bow_frontier_compound"):(Peakwatch()||Mountain)?TEXT("bow_woodsteel"):TEXT("bow_dark"));
    if(Peakwatch()||Mountain||Frontier)
    {
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return S;
        auto Parts=MakeShared<FJsonObject>();
        if(Mountain||Frontier||(Peakwatch()&&Phase==0))Parts->SetStringField(TEXT("string"),MountainEchoString::Option);
        if(Frontier)Parts->SetStringField(TEXT("riser"),Phase==0?TEXT("frontier_eclipse"):TEXT("frontier_aurora"));
        if(Peakwatch())Parts->SetStringField(TEXT("sight"),TEXT("highland_peakwatch_3_6x"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();
        FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    }
    if(BowFlightWire::Enabled()){S.AmmoPouch.Add(Model->AmmoDefinitionFor(Item),10);S.Stamina=100;S.Mana=100;S.CampfireInventoryRevision=0;}
    Item.InstanceId=Id;Item.Place=1;Item.Cell=6;S.Items={Item};
    if(Handoff())for(const TCHAR* Def:{TEXT("mineral_water"),TEXT("roasted_large_lamb")})
    {
        auto Food=Model->CreateItem(Def);Food.InstanceId=Def;Food.Place=0;
        if(!ColdSteelInventory::Insert(S.Items,Food))UE_LOG(LogTemp,Error,TEXT("SPARROW_FIXTURE cannot place %s"),Def);
    }
    return S;
}
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {
        FPacketSimulationSettings Settings;Settings.PktLag=60;Settings.PktLoss=5;Driver->SetPacketSimulationSettings(Settings);
        UE_LOG(LogTemp,Display,TEXT("SPARROW_PRESENTATION_NET lag_ms=%d loss_percent=%d role=%d"),Driver->PacketSimulationSettings.PktLag,Driver->PacketSimulationSettings.PktLoss,int32(World->GetNetMode()));
    }
#endif
}
}

void AShotgunWireAuditController::PoseSparrowPresentation(AFPSGAMECharacter* Subject,int32 Phase,bool Muted)
{
    if(!Subject)return;
    Subject->SetActorTickEnabled(false);Subject->GetCharacterMovement()->SetComponentTickEnabled(false);
    Subject->GetCharacterMovement()->DisableMovement();Subject->GetCharacterMovement()->StopMovementImmediately();
    // This fixture deliberately pauses CMC and therefore sends no movement
    // updates to drive the authority mesh. Let its normal component tick pose
    // run instead; production characters retain CMC's autonomous pose policy.
    if(auto* Mesh=Subject->GetMesh())Mesh->bOnlyAllowAutonomousTickPose=false;
    Subject->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Subject->bIsSprinting=false;Subject->SprintPoseFactor=0;
    if(auto* PC=Subject->GetController())PC->SetControlRotation(FRotator(SparrowWire::Pitch(Phase),0,0));
    Subject->FirstPersonCamera->SetWorldRotation(FRotator(SparrowWire::Pitch(Phase),0,0));
    // Pausing the actor also pauses ActionCamera::Apply, which normally clears
    // the startup equip offset. Otherwise the host's cached POV stays 7 degrees
    // below the pinned aim even after the component rotation is synchronized.
    Subject->FirstPersonCamera->ClearAdditiveOffset();
    if(auto* Move=Cast<UFPSCharacterMovementComponent>(Subject->GetCharacterMovement()))Move->bWantsToAim=true;
    auto* Body=Subject->FindComponentByClass<UFPSPlayerBodyComponent>();if(Body)Body->SetComponentTickEnabled(!Muted);
    auto* Bow=Subject->FindComponentByClass<UBowWeaponComponent>();if(!Bow)return;
    Bow->SetComponentTickEnabled(false);
    if(!Subject->IsLocallyControlled()||!Bow->bPresentationReady)return;
    if(SparrowWire::Peakwatch())
    {
        Bow->bSteadyHeld=true;Bow->AimProgress=1.f;
        const float TargetZoom=SparrowWire::Zoom(Subject->HasAuthority(),Phase);
        Bow->AdjustScopeMagnification(TargetZoom-Bow->ScopeMagnification());
        Bow->DisplayedOpticalMagnification=Bow->ScopeMagnification();
        Bow->UpdateScopeRing();
    }
    if(SparrowWire::Handoff()&&Phase>=9)
    {
        auto* Use=Subject->FindComponentByClass<UFPSPotionUseComponent>();if(!Use||!Use->Bottle)return;
        const FName Definition=Phase==9?TEXT("mineral_water"):TEXT("roasted_large_lamb");
        if(Phase<=11&&(!Use->IsActive()||Use->PresentationDefinition!=Definition))
        {
            Use->Finish();Bow->CastTransferAlpha=0.f;Bow->Viewmodel->CastTransfer=0.f;
            Bow->Stage=EBowStage::Ready;
            if(!Use->TryBegin(Definition.ToString(),Definition.ToString()))return;
        }
        // Pin the executor at real use-clock samples. Socket transport and the
        // observer graph run normally; this fixture does not commit inventory.
        Use->SetComponentTickEnabled(false);
        if(Phase<=11)
        {
            Use->bWaitingForBow=false;
            Use->StartTime=Subject->GetWorld()->GetTimeSeconds()-(Phase==11?Use->Motion.Duration+.13f:Use->Motion.DrinkStart);
            Use->ApplyHandPose(*Use->ActiveHands.Get());
        }
        else
        {
            if(Phase==12)
            {
                if(Use->IsActive())
                {
                    Use->StartTime=Subject->GetWorld()->GetTimeSeconds()-Use->Motion.DrinkStart;
                    Use->Cancel();
                }
                Use->BowReturnStartedAt=Subject->GetWorld()->GetTimeSeconds();
            }
            else Use->Cancel();
        }
        Use->SetComponentTickEnabled(false);
        Bow->Stage=EBowStage::Ready;Bow->bArrowNocked=false;Bow->bSteadyHeld=false;
        Bow->CastTransferAlpha=Phase==9?1.f:0.f;Bow->Viewmodel->CastTransfer=Bow->CastTransferAlpha;
        Bow->Viewmodel->ClearLeftReturn();Bow->SampleArms();Bow->UpdatePoseLayers();Bow->UpdateBowGeometry();return;
    }
    Bow->bSteadyHeld=true;Bow->bArrowNocked=Phase!=0&&Phase!=3;Bow->bNockKeepsDrawPose=true;
    Bow->HoldElapsed=.2f;Bow->Stage=EBowStage::Holding;
    if(Phase==0||Phase==5){Bow->Stage=EBowStage::Ready;Bow->Elapsed=0.f;}
    else if(Phase==1){Bow->Stage=EBowStage::Drawing;Bow->Elapsed=Bow->DrawSeconds*.5f;}
    else if(Phase==3){Bow->Stage=EBowStage::Recover;Bow->Elapsed=.12f;Bow->ReleaseFeedbackAge=.4f;}
    else if(Phase==4){Bow->Stage=EBowStage::LetDown;Bow->StageSeconds=.2f;Bow->LetDownPhase=.7f;Bow->LetDownRatio=.7f;Bow->Elapsed=.05f;}
    Bow->SampleArms();Bow->UpdatePoseLayers();Bow->UpdateBowGeometry();
}

void AShotgunWireAuditController::SetupSparrowPresentation(int32 Phase,const FString& Id,AFPSGAMECharacter* Host)
{
    if(HasAuthority()||Phase==Current||!Host)return;
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Subject||!Model||!Model->IsAudit())return;
    if(Current<0)SparrowWire::Network(GetWorld());
    Model->Current=SparrowWire::Seed(Model,Id,Phase);Model->CurrentPawn=Subject;Subject->ApplyColdSteelProfile(Model);
    Subject->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);
    ObserverSubject=Host;Current=Phase;Weapon=Id;Started=GetWorld()->GetRealTimeSeconds();SentAt=-1;bReported=false;
    if(BowFlightWire::Enabled())BowFlightWire::Reset(Subject,Phase);
    else PoseSparrowPresentation(Subject,Phase,Phase==7);
    UE_LOG(LogTemp,Display,TEXT("SPARROW_PRESENTATION_CLIENT_SETUP phase=%d"),Phase);
}

bool AShotgunWireAuditController::CheckSparrowPresentation(AFPSGAMECharacter* Subject,int32 Phase,bool Expired,TSharedPtr<FJsonObject> Row)
{
    auto* Body=Subject?Subject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;if(!Body||!Body->BodyAnimation)return false;
    const auto& State=Body->DisplayState;
    const bool Aim=FMath::IsNearlyEqual(State.AimPitch,SparrowWire::Pitch(Phase),1.f);
    const bool Pose=Expired?State.BowClip.IsNone():State.BowClip==SparrowWire::Clip(Phase);
    const bool Identity=Body->BowItemInstance==State.WeaponInstance&&!State.WeaponInstance.IsEmpty();
    if(SparrowWire::Peakwatch())
    {
        bool AuthoredGlass=false,RingFollows=false,StringMaterial=false;
        const float Expected=(SparrowWire::Zoom(Subject->GetNetMode()==NM_Client,Phase)-3.f)*-37.f;
        for(const auto& Part:Body->WorldBowParts)if(Part)
        {
            if(Part->SlotName==TEXT("string"))
            {
                if(Phase==0)
                {
                    TArray<USceneComponent*> Children;Part->GetChildrenComponents(false,Children);
                    for(auto* Child:Children)if(auto* Beam=Cast<UBowFlexMeshComponent>(Child);Beam&&Beam->GetSkinnedAsset())
                    {
                        const int32 Slot=Beam->GetMaterialIndex(TEXT("M_Highland_BeamString_Light"));
                        StringMaterial=Slot!=INDEX_NONE&&Beam->GetMaterial(Slot)&&
                            Beam->GetMaterial(Slot)->GetFName()==TEXT("M_Highland_BeamString_Light");
                        break;
                    }
                }
                else
                {
                    StringMaterial=Part->RodCount()==2;
                    for(int32 Index=0;Index<Part->RodCount();++Index)
                    {
                        const auto* Rod=Part->RodVisual(Index);
                        StringMaterial&=Rod&&Rod->GetMaterial(0)&&Rod->GetMaterial(0)->GetFName()==TEXT("M_BowString");
                    }
                }
            }
            if(Part->SlotName==TEXT("sight_zoom"))
                RingFollows=FMath::Abs(FMath::FindDeltaAngleDegrees(Part->GetRelativeRotation().Roll,Expected))<.5f;
            if(Part->SlotName!=TEXT("sight"))continue;
            auto* Mesh=Part->GetVisual();UStaticMesh* Asset=Mesh?Mesh->GetStaticMesh().Get():nullptr;
            const int32 Slot=Asset?Asset->GetMaterialIndex(TEXT("M_Peakwatch_Glass")):INDEX_NONE;
            AuthoredGlass=Slot!=INDEX_NONE&&Asset->GetMaterial(Slot)&&Mesh->GetMaterial(Slot)==Asset->GetMaterial(Slot);
        }
        const bool NoRemoteCapture=!Subject->FindComponentByClass<USceneCaptureComponent2D>();
        Row->SetNumberField(TEXT("ring_degrees"),State.BowScopeRingRoll);
        Row->SetBoolField(TEXT("authored_world_glass"),AuthoredGlass);Row->SetBoolField(TEXT("ring_follows_zoom"),RingFollows);
        Row->SetBoolField(TEXT("no_remote_capture"),NoRemoteCapture);
        Row->SetBoolField(TEXT("world_string_material"),StringMaterial);
        return Identity&&AuthoredGlass&&RingFollows&&NoRemoteCapture&&StringMaterial&&
            FMath::Abs(FMath::FindDeltaAngleDegrees(State.BowScopeRingRoll,Expected))<.5f;
    }
    const float Weight=Body->BodyAnimation->GetCurveValue(FPSBodyBowMotion::WeightCurve);
    if(SparrowWire::Handoff()&&Phase>=9)
    {
        const bool Stowing=Phase>=10&&Phase<=12,Hidden=Phase==10||Phase==12;
        bool Visibility=true;for(auto Part:Body->WorldBowParts)Visibility&=Part->bHiddenInGame==Hidden;
        const bool Data=State.bBowTwoHandConsume==Stowing&&FMath::IsNearlyEqual(State.BowCastTransfer,Phase==9?1.f:0.f,.01f)
            &&FMath::IsNearlyEqual(State.BowStowWeight,Hidden?1.f:Phase==11?.5f:0.f,.02f)
            &&(Phase<=11?State.Action==EFPSBodyAction::Consume:State.Action!=EFPSBodyAction::Consume);
        const bool Grip=Phase!=9||Body->BodyAnimation->GetCurveValue(FPSBodyBowMotion::RightHoldCurve)>.5f;
        bool Finite=true;for(const auto& T:Body->GetBodyMesh()->GetComponentSpaceTransforms())Finite&=!T.ContainsNaN();
        Row->SetBoolField(TEXT("identity"),Identity);Row->SetBoolField(TEXT("handoff"),Data);Row->SetBoolField(TEXT("visibility"),Visibility);
        Row->SetBoolField(TEXT("supporting_right_hand"),Grip);Row->SetBoolField(TEXT("finite_pose"),Finite);
        Row->SetNumberField(TEXT("transfer"),State.BowCastTransfer);Row->SetNumberField(TEXT("stow"),State.BowStowWeight);
        Row->SetNumberField(TEXT("action"),int32(State.Action));Row->SetNumberField(TEXT("native_weight"),Weight);
        return Identity&&Data&&Visibility&&Grip&&Finite&&(Hidden?Weight<.01f:Weight>.99f);
    }
    const bool Data=Expired?(State.Contacts.Channel.IsNone()&&!State.bBowArrow&&State.BowStringContact==0.f)
        :(State.Contacts.Channel==TEXT("Bow")&&State.Contacts.Fingers==3&&Body->HasMatchingMotionRig(0));
    bool Contact=true;double Error=0.;
    if(Expired)
    {
        UBowPartComponent* Riser=nullptr;UBowPartComponent* String=nullptr;
        for(auto Part:Body->WorldBowParts){if(Part->SlotName==TEXT("riser"))Riser=Part;if(Part->SlotName==TEXT("string"))String=Part;}
        Contact=Riser&&String&&!Body->bHasNativeBowHeldNock;
        if(Riser&&String)
        {
            const FVector Brace=Riser->GetComponentTransform().TransformPosition(Body->BowSettings.Brace);
            Error=FMath::Max(FVector::Distance(Brace,BowPresentationAudit::StringEnd(String->RodVisual(0))),FVector::Distance(Brace,BowPresentationAudit::StringEnd(String->RodVisual(1))));
            Contact&=Error<.05;
        }
    }
    if(State.BowStringContact>0.f)
    {
        UBowPartComponent* String=nullptr;for(auto Part:Body->WorldBowParts)if(Part&&Part->SlotName==TEXT("string"))String=Part;
        if(!String)Contact=false;
        else
        {
            const FVector N(Body->BodyAnimation->GetCurveValue(TEXT("SparrowBowNockX")),Body->BodyAnimation->GetCurveValue(TEXT("SparrowBowNockY")),Body->BodyAnimation->GetCurveValue(TEXT("SparrowBowNockZ")));
            const FVector Point=Body->GetBodyMesh()->GetSocketTransform(TEXT("hand_r")).TransformPosition(N);
            Error=FMath::Max(FVector::Distance(Point,BowPresentationAudit::StringEnd(String->RodVisual(0))),
                FVector::Distance(Point,BowPresentationAudit::StringEnd(String->RodVisual(1))));
            Contact=Error<.05;
        }
    }
    Row->SetBoolField(TEXT("aim"),Aim);Row->SetBoolField(TEXT("pose"),Pose);Row->SetBoolField(TEXT("identity"),Identity);
    Row->SetBoolField(TEXT("data_or_expiry"),Data);Row->SetBoolField(TEXT("contact"),Contact);Row->SetNumberField(TEXT("contact_cm"),Error);
    Row->SetNumberField(TEXT("native_weight"),Weight);Row->SetStringField(TEXT("clip"),State.BowClip.ToString());
    Row->SetNumberField(TEXT("clip_rate"),State.BowClipRate);Row->SetNumberField(TEXT("pitch"),State.AimPitch);
    Row->SetStringField(TEXT("family"),State.Family.ToString());Row->SetStringField(TEXT("weapon_instance"),State.WeaponInstance);
    Row->SetStringField(TEXT("built_instance"),Body->BowItemInstance);Row->SetStringField(TEXT("channel"),State.Contacts.Channel.ToString());
    Row->SetStringField(TEXT("reported_instance"),Body->ReportedPresentation.WeaponInstance);
    Row->SetStringField(TEXT("reported_clip"),Body->ReportedPresentation.BowClip.ToString());
    Row->SetNumberField(TEXT("sample_age"),Body->ServerClock()-Body->LastPresentationReceivedAt);
    Row->SetBoolField(TEXT("bow_pose_requested"),Body->BodyAnimation->bBowPose);
    Row->SetNumberField(TEXT("action"),int32(State.Action));
    return Aim&&Pose&&Identity&&Data&&Contact&&Weight>.99f;
}

bool AShotgunWireAuditController::TickSparrowPresentation(float Delta)
{
    if(!SparrowWire::Enabled())return false;
    Super::Tick(Delta);if(HasAuthority()||!IsLocalController())return true;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(Current<0||bReported)return true;
    auto* Own=Cast<AFPSGAMECharacter>(GetPawn());
    if(BowFlightWire::Enabled())
    {
        auto* PS=GetPlayerState<AColdSteelPlayerState>();
        if(!Own||!PS)return true;
        auto& T=BowFlightWire::Track;
        BowFlightWire::Sample(Own,Current);
        if(!T.Draw.IsValid()&&Now-Started>1.)
        {
            T.Draw=FGuid::NewGuid();T.Started=GetWorld()->GetTimeSeconds();
            PS->ServerSetBowDraw(Own,Weapon,true,0.f,T.Draw);
        }
        if(!T.Released&&T.Draw.IsValid()&&GetWorld()->GetTimeSeconds()-T.Started>2.4)
        {
            FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::BowShot;R.Item=Weapon;
            R.Sequence=Current+1;R.Pawn=Own;R.Eye=Own->GetPawnViewLocation();R.Origin=T.Origin;R.Direction=FVector::ForwardVector;
            R.BowDrawId=T.Draw;R.Charge=1.f;R.BowChargeElapsed=2.4f;
            PS->ServerInventoryAction(R);T.Released=true;
        }
        if(Now-Started<12.)return true;
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Current);
        bool Passed=BowFlightWire::Check(Current,Row);
        bReported=true;bAllPassed&=Passed;Results.Add(MakeShared<FJsonValueObject>(Row));
        ServerSparrowResult(Current,Passed);ShotgunWire::Save(Results,bAllPassed,TEXT("client"));return true;
    }
    PoseSparrowPresentation(Own,Current,Current==7);
    auto* OwnBow=Own?Own->FindComponentByClass<UBowWeaponComponent>():nullptr;
    auto* Seen=ObserverSubject?ObserverSubject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    // Cold processes load the bow asynchronously. Start the observation window
    // after the source and observer assets exist, with a bounded load deadline.
    const bool AssetsReady=OwnBow&&OwnBow->bPresentationReady&&Seen&&Seen->BowRig&&Seen->BodyAnimation;
    if(!AssetsReady)SentAt=-1.;else if(SentAt<0.)SentAt=Now;
    if(Now-Started<30.&&(SentAt<0.||Now-SentAt<5.))return true;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Current);
    Row->SetBoolField(TEXT("assets_ready"),AssetsReady);
    const bool Passed=CheckSparrowPresentation(ObserverSubject,Current,false,Row)&&AssetsReady;
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=Passed;bReported=true;
    ServerSparrowResult(Current,Passed);ShotgunWire::Save(Results,bAllPassed,TEXT("client"));return true;
}

void AShotgunWireAuditController::ServerSparrowResult_Implementation(int32 Phase,bool ObserverOK)
{
    if(!SparrowWire::Enabled()||Phase!=Expected||Finished!=Phase)return;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);Row->SetBoolField(TEXT("client_observer"),ObserverOK);
    bool Passed=false;
    if(BowFlightWire::Enabled())
    {
        Passed=BowFlightWire::Check(Phase,Row);
        auto* PS=GetPlayerState<AColdSteelPlayerState>();
        auto* M=PS?PS->ShadowModel.Get():nullptr;
        const auto* Item=M?M->ActiveBow():nullptr;
        const float Damage=BowFlightWire::Track.Target.IsValid()?BowFlightWire::Track.Target->Received:0.f;
        const int32 Ammo=Item?M->PouchCount(M->AmmoDefinitionFor(*Item)):-1;
        Row->SetNumberField(TEXT("authority_target_damage"),Damage);Row->SetNumberField(TEXT("guest_arrows_remaining"),Ammo);
        const bool Hit=BowFlightWire::Frontier()&&Phase==0?BowFlightWire::Track.SawMark:Damage>0.f;
        Passed&=Hit&&Ammo==9;
    }
    else Passed=CheckSparrowPresentation(Cast<AFPSGAMECharacter>(GetPawn()),Phase,Phase==7,Row);
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=Passed&&ObserverOK;++Finished;
    UE_LOG(LogTemp,Display,TEXT("SPARROW_PRESENTATION_WIRE_CASE phase=%d observer=%d authority=%d"),Phase,ObserverOK,Passed);
    if(!Passed){FString Detail;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Detail));UE_LOG(LogTemp,Display,TEXT("SPARROW_PRESENTATION_DETAIL %s"),*Detail);}
}

bool AShotgunWireAuditGameMode::TickSparrowPresentation(float Delta)
{
    if(!SparrowWire::Enabled())return false;
    Super::Tick(Delta);const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(!Guest)return true;
    auto* Subject=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Subject||!PS||!Model||!Model->IsAudit())return true;
    if(!HostPawn)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())HostPawn=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    if(!HostPawn)return true;
    if(Guest->Finished>=SparrowWire::Cases()||Now-Joined>180.)
    {
        const bool Pass=Guest->Finished==SparrowWire::Cases()&&Guest->bAllPassed;
        bPresentationPassed&=Pass;PresentationHistory.Append(Guest->Results);Guest->ClientFinish(Pass);++PresentationConnections;
        if(PresentationConnections==1){Guest=nullptr;Prepared=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("SPARROW_PRESENTATION_REJOIN_READY"));return true;}
        ShotgunWire::Save(PresentationHistory,bPresentationPassed,TEXT("listen_host"));ExitAt=Now+3.;return true;
    }
    if(Prepared!=Guest->Finished)
    {
        if(Prepared==INDEX_NONE)SparrowWire::Network(GetWorld());
        Prepared=Guest->Finished;if(Prepared==0||Prepared==6)Weapon=FGuid::NewGuid().ToString();Guest->Expected=Prepared;
        const auto Seed=SparrowWire::Seed(Model,Weapon,Prepared);
        if(!PS->ShadowModel)PS->ShadowModel=Model->CreateShadowModel(Seed);else PS->ShadowModel->Current=Seed;
        if(!PS->ShadowModel)
        {
            UE_LOG(LogTemp,Error,TEXT("SPARROW_FIXTURE profile rejected: %s"),*Model->ResultMessage());
            Guest->bAllPassed=false;Guest->Finished=SparrowWire::Cases();return true;
        }
        PS->ShadowModel->CurrentPawn=Subject;Subject->NetShadowProfile=PS->ShadowModel;Subject->ApplyColdSteelProfile(PS->ShadowModel);
        Model->Current=SparrowWire::Seed(Model,TEXT("SparrowHost_")+Weapon,Prepared);Model->CurrentPawn=HostPawn;HostPawn->ApplyColdSteelProfile(Model);
        Subject->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);HostPawn->SetActorLocationAndRotation(FVector(0,1000,500),FRotator::ZeroRotator);
        if(BowFlightWire::Enabled())
        {
            BowFlightWire::Reset(Subject,Prepared);
            if(Prepared==1)if(auto* Echo=Subject->FindComponentByClass<UBowMountainEchoComponent>())
                for(int32 I=0;I<3;++I)Echo->ConfirmHit(Echo->Epoch);
        }
        LastSetup=-10;
    }
    if(BowFlightWire::Enabled())
    {
        BowFlightWire::Sample(Subject,Prepared);
        if(Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetup(Prepared,Weapon,HostPawn);}return true;
    }
    AShotgunWireAuditController::PoseSparrowPresentation(Subject,Prepared,false);
    AShotgunWireAuditController::PoseSparrowPresentation(HostPawn,Prepared,false);
    if(Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetup(Prepared,Weapon,HostPawn);}return true;
}
