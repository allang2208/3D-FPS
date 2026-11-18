#include "HillsSceneryNetworkProbe.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/TemperateHillsGroundLayers.h"
#include "../WorldGeneration/TemperateHillsCaptureReadiness.h"
#include "../WorldGeneration/TemperateHillsCompatibility.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Production/ProductionResource.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/NetDriver.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Containers/Ticker.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/SecureHash.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace HillsSceneryProbe
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("HillsSceneryNetworkProbe"));
#endif
}
FString Output(){FString P;FParse::Value(FCommandLine::Get(),TEXT("HillsSceneryOutput="),P);return P;}
void Save(const FString& Name,const TSharedRef<FJsonObject>& R)
{FString J;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&J));IFileManager::Get().MakeDirectory(*Output(),true);FFileHelper::SaveStringToFile(J,*(Output()/Name+TEXT(".json")));}
ATemperateHillsWorld* Hills(UWorld* W)
{for(TActorIterator<ATemperateHillsWorld> It(W);It;++It)if(It->bReady)return *It;return nullptr;}
UColdSteelStatusModel* Model(UWorld* W){return W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();}
bool Ground(ATemperateHillsWorld* H,FVector P)
{FHitResult Hit;return HillsLandscapeCapture::GroundHit(H,FVector2D(P),Hit)&&FMath::Abs(Hit.ImpactPoint.Z-H->Height(P.X,P.Y))<35.;}
void Place(APlayerController* PC,FVector P)
{
    auto* Pawn=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;if(!Pawn)return;
    Pawn->SetCanBeDamaged(false);Pawn->GetCharacterMovement()->StopMovementImmediately();
    Pawn->GetCharacterMovement()->DisableMovement();Pawn->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);Pawn->ForceNetUpdate();
}
FString Snapshot(ATemperateHillsWorld* H,FVector P)
{
    FString S=H->WorldId.ToString()+FString::Printf(TEXT("/%d/%d"),H->Seed,H->GeneratorVersion);
    for(int32 Y=-4;Y<=4;++Y)for(int32 X=-4;X<=4;++X)
    {
        const double WX=P.X+X*600.,WY=P.Y+Y*600.;const auto R=H->SampleRiver(WX,WY);
        S+=FString::Printf(TEXT("|%lld,%lld,%lld"),FMath::RoundToInt64(H->Height(WX,WY)*10.),FMath::RoundToInt64(R.WaterZ*10.),FMath::RoundToInt64(R.Wet*10000.));
    }
    for(int32 Layer=0;Layer<=4;++Layer)
    {
        TArray<FTemperatePlacement> Points;H->GetPlacements(Layer,FBox(P-FVector(1800,1800,100000),P+FVector(1800,1800,100000)),Points);
        Points.Sort([](const auto& A,const auto& B){if(A.CandidateId!=B.CandidateId)return A.CandidateId<B.CandidateId;return A.Mesh.ToString()<B.Mesh.ToString();});
        S+=FString::Printf(TEXT("L%d:%d"),Layer,Points.Num());
        for(const auto& V:Points)
        {
            const auto T=V.Transform;const auto L=T.GetLocation(),Scale=T.GetScale3D();
            S+=FString::Printf(TEXT("|%llu:%s:%lld,%lld,%lld:%.5f,%.5f,%.5f:%.5f"),V.CandidateId,*V.Mesh.ToString(),FMath::RoundToInt64(L.X*10.),FMath::RoundToInt64(L.Y*10.),FMath::RoundToInt64(L.Z*10.),Scale.X,Scale.Y,Scale.Z,T.Rotator().Yaw);
        }
    }
    return FMD5::HashAnsiString(*S);
}
bool Landmarks(ATemperateHillsWorld* H,FString& Detail)
{
    int32 N=0;bool OK=true;TInlineComponentArray<UInstancedStaticMeshComponent*> Parts(H);
    for(auto* C:Parts)if(C->ComponentHasTag(TEXT("HillsWhiteCliffs")))
    {N+=C->GetInstanceCount();OK&=C->GetAttachParent()==H->GetRootComponent()&&C->GetCollisionEnabled()!=ECollisionEnabled::NoCollision;
        if(H->HasAuthority())OK&=C->CanEverAffectNavigation();}
    Detail=FString::Printf(TEXT("instances=%d attachment_collision_navigation=%d"),N,OK);return OK&&N>0;
}
bool Depleted(UWorld* W,const TArray<FString>& Ids)
{
    auto* M=UColdSteelSharedInventorySubsystem::HarvestModel(W);if(!M||Ids.Num()!=2)return false;
    return M->TreeHealthRatio(Ids[0])<=0.f&&M->RockHealthRatio(Ids[1])<=0.f;
}
}

AHillsSceneryNetworkProbe::AHillsSceneryNetworkProbe()
{bReplicates=true;bOnlyRelevantToOwner=true;PrimaryActorTick.bCanEverTick=true;}
void AHillsSceneryNetworkProbe::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AHillsSceneryNetworkProbe,Phase);DOREPLIFETIME(AHillsSceneryNetworkProbe,Center);DOREPLIFETIME(AHillsSceneryNetworkProbe,Expected);DOREPLIFETIME(AHillsSceneryNetworkProbe,Harvested);}
void AHillsSceneryNetworkProbe::ServerResult_Implementation(int32 Case,bool OK,const FString& Text)
{if(!HillsSceneryProbe::Enabled()||Case!=Phase)return;Observed=Case;Passed=OK;Detail=Text;}
void AHillsSceneryNetworkProbe::ClientFinish_Implementation(bool OK)
{if(!HillsSceneryProbe::Enabled())return;auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);HillsSceneryProbe::Save(TEXT("client-finished"),R);FPlatformMisc::RequestExit(false);}
void AHillsSceneryNetworkProbe::Tick(float Dt)
{
    Super::Tick(Dt);using namespace HillsSceneryProbe;
    if(!Enabled()||HasAuthority()||Phase<=0)return;
    auto* H=Hills(GetWorld());auto* PC=Cast<APlayerController>(GetOwner());if(!H||!PC||!PC->GetPawn())return;
    if(LastPhase!=Phase){LastPhase=Phase;Began=FPlatformTime::Seconds();WalkStarted=0.;Reported=false;Requested=false;}
    if(Reported)return;
    const double Age=FPlatformTime::Seconds()-Began;bool Ready=false,OK=false;FString Text;
    if(Phase<10)
    {
        Ready=Age>4.&&FVector::Dist2D(PC->GetPawn()->GetActorLocation(),Center)<200.&&Ground(H,Center);
        if(Ready){const auto Actual=Snapshot(H,Center);OK=Actual==Expected;Text=TEXT("snapshot=")+Actual;}
    }
    else if(Phase==10||Phase==11)
    {Ready=Age>2.&&Depleted(GetWorld(),Harvested);OK=Ready;Text=TEXT("tree and rock depletion received through shared world mirror");}
    else if(Phase==20)
    {
        auto* C=Cast<ACharacter>(PC->GetPawn());
        if(C&&Ground(H,C->GetActorLocation()))
        {
            if(WalkStarted==0.)WalkStarted=FPlatformTime::Seconds();
            if(FPlatformTime::Seconds()-WalkStarted<3.){C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);C->AddMovementInput(FVector(0,1,0),1.f);}
        }
        Ready=WalkStarted>0.&&FPlatformTime::Seconds()-WalkStarted>4.;OK=Ready&&C&&FVector::Dist2D(C->GetActorLocation(),Center)>80.;Text=C?C->GetActorLocation().ToString():TEXT("no character");
    }
    else if(Phase==21)
    {
        if(!Requested)if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>()){PS->ServerVisitHillsQuarry();Requested=true;}
        Ready=Age>2.&&FVector::Dist2D(PC->GetPawn()->GetActorLocation(),Center)<750.&&Ground(H,PC->GetPawn()->GetActorLocation());
        OK=Ready;Text=TEXT("guest landmark command used owning PlayerState RPC and server collision staging");
    }
    else if(Phase==40)
    {
        auto* M=Model(GetWorld());auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();
        if(M&&PS&&!Requested)
        {
            Requested=true;NextHarvest=0.;FString Id;
            const bool Added=M->AddItem(TEXT("tool_pickaxe"));
            for(const auto& I:M->Items())if(I.Definition==TEXT("tool_pickaxe")&&I.Place==0){Id=I.InstanceId;break;}
            if(!Added||!M->MoveItem(Id,1,6)){Ready=true;Text=TEXT("client tool setup failed: ")+M->ResultMessage();}
        }
        auto* Shared=UColdSteelSharedInventorySubsystem::HarvestModel(GetWorld());
        if(!Ready&&Shared&&Shared->RockHealthRatio(Expected)<=0.f)
        {Ready=true;OK=true;Text=TEXT("guest mining submitted through RequestInventoryAction and received authoritative depletion");}
        if(!Ready&&M&&PS&&Age>NextHarvest)
        {
            FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Harvest;R.Eye=PC->GetPawn()->GetPawnViewLocation();R.Direction=(Center-FVector(R.Eye)).GetSafeNormal();
            PS->RequestInventoryAction(R);NextHarvest=Age+.7;
        }
    }
    if(Age>180.){Ready=true;OK=false;Text=TEXT("client readiness timeout phase=")+FString::FromInt(Phase);}
    if(Ready){Reported=true;auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("detail"),Text);Save(FString::Printf(TEXT("client-%02d"),Phase),R);ServerResult(Phase,OK,Text);}
}

#if !UE_BUILD_SHIPPING
namespace HillsSceneryProbe
{
struct FRun
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<APlayerController> Host,Guest,OldGuest;
    TWeakObjectPtr<AHillsSceneryNetworkProbe> Probe;
    TArray<TSharedPtr<FJsonValue>> Checks;
    TArray<FVector> Centers;
    TArray<FString> Harvested;
    TArray<FTemperatePlacement> ResourceCandidates;
    FTemperatePlacement CurrentResource;
    FVector HarvestTarget=FVector::ZeroVector;
    FGuid WorldId,GuestId;
    int32 Stage=0,Area=0,Layer=0,CandidateIndex=0;
    double Started=FPlatformTime::Seconds(),Next=0.,HarvestStarted=0.;
    bool OK=true,ResourcePlaced=false;
    void Record(const FString& Name,bool Pass,const FString& Detail=FString())
    {auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),Pass);R->SetStringField(TEXT("detail"),Detail);Checks.Add(MakeShared<FJsonValueObject>(R));OK&=Pass;UE_LOG(LogTemp,Display,TEXT("HILLS_SCENERY_CASE %s=%d %s"),*Name,Pass,*Detail);}
    bool Finish()
    {auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);R->SetArrayField(TEXT("checks"),Checks);R->SetStringField(TEXT("content_signature"),TemperateHillsCompatibility::Signature());Save(TEXT("result"),R);if(Probe.IsValid())Probe->ClientFinish(OK);FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float){FPlatformMisc::RequestExit(false);return false;}),3.f);return false;}
    void NewProbe()
    {FActorSpawnParameters P;P.Owner=Guest.Get();Probe=World->SpawnActor<AHillsSceneryNetworkProbe>(P);}
    void Send(int32 Phase,FVector Center=FVector::ZeroVector,const FString& Expected=FString())
    {Probe->Center=Center;Probe->Expected=Expected;Probe->Harvested=Harvested;Probe->Observed=0;Probe->Phase=Phase;Probe->ForceNetUpdate();}
    bool Bind(UWorld* W)
    {
        World=W;Host=nullptr;Guest=nullptr;
        for(auto It=W->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get()){if(PC->IsLocalController())Host=PC;else Guest=PC;}
        auto* PS=Guest.IsValid()?Guest->GetPlayerState<AColdSteelPlayerState>():nullptr;
        return Host.IsValid()&&Host->GetPawn()&&Guest.IsValid()&&Guest->GetPawn()&&PS&&PS->ShadowModel;
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();if(Now<Next)return true;
        if(!OK)return Finish();if(Now-Started>1500.){Record(TEXT("deadline"),false,FString::FromInt(Stage));return Finish();}
        UWorld* W=nullptr;for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->GetNetMode()==NM_ListenServer&&C.World()->HasBegunPlay()){W=C.World();break;}
        if(!W)return true;World=W;auto* H=Hills(W);if(!H)return true;
        if(Stage==90)
        {
            bool Found=false;for(auto It=W->GetPlayerControllerIterator();It;++It)if(!It->Get()->IsLocalController())Found=true;
            if(Found)return true;Record(TEXT("production_logout_removed_guest"),!OldGuest.IsValid());
            UE_LOG(LogTemp,Display,TEXT("HILLS_SCENERY_RECONNECT_READY"));Stage=91;return true;
        }
        if(!Bind(W))return true;
        if(Stage==0)
        {
            WorldId=H->WorldId;GuestId=Guest->GetPlayerState<AColdSteelPlayerState>()->ShadowModel->Snapshot().NetworkProfileId;
            FString Detail;Record(TEXT("landmark_attachment_collision_navigation"),Landmarks(H,Detail),Detail);
            TemperateHillsGround::FMapSource Map;H->CopyMapGround(Map);if(!Map.River||!Map.River->Lake.Valid){Record(TEXT("lake_exists"),false);return true;}
            const auto& Lake=Map.River->Lake;const auto& Quarry=Map.River->WhiteCliffs;
            Centers={FVector(Lake.Center+Lake.Axis*(Lake.RadiusX+2200.),0),FVector(Map.River->ForestAnchor,0),FVector(Quarry.World(0,-3600.),0)};
            for(auto& C:Centers)C.Z=H->Height(C.X,C.Y)+100.;
            NewProbe();Stage=1;
        }
        if(Stage==1)
        {Place(Guest.Get(),Centers[Area]);Send(Area+1,Centers[Area],Snapshot(H,Centers[Area]));Stage=2;return true;}
        if(Stage==2&&Probe->Observed==Area+1)
        {
            Record(FString::Printf(TEXT("area_%d_peer_terrain_and_five_placement_layers"),Area),Probe->Passed,Probe->Detail);
            Record(FString::Printf(TEXT("area_%d_remote_authority_ground"),Area),Ground(H,Centers[Area]));
            if(++Area<Centers.Num())Stage=1;else{Stage=30;Area=0;}return true;
        }
        if(Stage==30)
        {
            TemperateHillsGround::FMapSource Map;H->CopyMapGround(Map);
            const auto XY=Map.River->WhiteCliffs.World(2200.*FMath::Sin(-3600./2600.),-3600.);
            Send(21,FVector(XY,H->Height(XY.X,XY.Y)+100.));Stage=31;return true;
        }
        if(Stage==31&&Probe->Observed==21)
        {Record(TEXT("guest_quarry_teleport_rpc"),Probe->Passed,Probe->Detail);Stage=3;return true;}
        if(Stage==3)
        {
            const auto P=Centers[0];Place(Guest.Get(),P);
            if(auto* C=Cast<ACharacter>(Guest->GetPawn()))C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            Send(20,P);Stage=4;return true;
        }
        if(Stage==4&&Probe->Observed==20)
        {
            Record(TEXT("client_lakeshore_character_movement"),Probe->Passed,Probe->Detail);
            Record(TEXT("authority_received_client_movement"),FVector::Dist2D(Guest->GetPawn()->GetActorLocation(),Centers[0])>80.);
            Stage=5;return true;
        }
        if(Stage==5)
        {
            auto* M=Model(W);const FString Tool=Layer==0?TEXT("tool_axe"):TEXT("tool_pickaxe");
            if(Layer==0)
            {
                if(!M->AddItem(Tool)){Record(TEXT("prepare_tool"),false,M->ResultMessage());return true;}
                FString Id;for(const auto& I:M->Items())if(I.Definition==Tool&&I.Place==0){Id=I.InstanceId;break;}
                if(!M->MoveItem(Id,1,6)){Record(TEXT("equip_tool"),false,M->ResultMessage());return true;}
            }
            const FVector P=H->GetStartLocation();ResourceCandidates.Reset();
            H->GetPlacements(Layer,FBox(P-FVector(15000,15000,100000),P+FVector(15000,15000,100000)),ResourceCandidates);
            ResourceCandidates.Sort([P](const auto& A,const auto& B){return FVector::DistSquared2D(A.Transform.GetLocation(),P)<FVector::DistSquared2D(B.Transform.GetLocation(),P);});
            CandidateIndex=0;ResourcePlaced=false;Stage=6;return true;
        }
        if(Stage==6)
        {
            if(CandidateIndex>=ResourceCandidates.Num()){Record(TEXT("harvestable_candidate"),false,FString::FromInt(Layer));return true;}
            if(!ResourcePlaced)
            {
                CurrentResource=ResourceCandidates[CandidateIndex];auto P=CurrentResource.Transform.GetLocation();
                HarvestTarget=P+FVector(0,0,100.);P.X+=220.;
                if(Layer==1)if(auto* Mesh=Cast<UStaticMesh>(CurrentResource.Mesh.ResolveObject()))
                {
                    FBox B=Mesh->GetBoundingBox();B.Min+=Mesh->GetNegativeBoundsExtension();B.Max-=Mesh->GetPositiveBoundsExtension();B=B.TransformBy(CurrentResource.Transform);
                    if(Mesh->GetBounds().SphereRadius*CurrentResource.Transform.GetScale3D().GetAbsMax()>500.){++CandidateIndex;return true;}
                    HarvestTarget=B.GetCenter();HarvestTarget.Z=FMath::Max(HarvestTarget.Z,H->Height(HarvestTarget.X,HarvestTarget.Y)+25.);
                    P=FVector(B.Max.X+140.,HarvestTarget.Y,0.);
                }
                P.Z=H->Height(P.X,P.Y)+100.;
                Place(Layer==0?Host.Get():Guest.Get(),P);Place(Layer==0?Guest.Get():Host.Get(),P+FVector(0,400,0));ResourcePlaced=true;HarvestStarted=Now;Next=Now+3.;return true;
            }
            auto* M=Model(W);auto* Worker=Layer==0?Host.Get():Guest.Get();const FVector Eye=Worker->GetPawn()->GetPawnViewLocation();
            const FVector Target=HarvestTarget;
            FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(HillsNetworkHarvest),false,Worker->GetPawn());
            FProductionResource Resource;FString Reason;
            const bool Found=W->LineTraceSingleByChannel(Hit,Eye,Eye+(Target-Eye).GetSafeNormal()*500.,ECC_Visibility,Q)&&H->ResolveProductionResource(Hit,Resource,Reason)&&Resource.Layer==Layer&&Resource.CandidateId==CurrentResource.CandidateId;
            if(!Found){if(Now-HarvestStarted>30.){++CandidateIndex;ResourcePlaced=false;}Next=Now+.5;return true;}
            if(Layer==1){Harvested.Add(Resource.Id);Send(40,Target,Resource.Id);Stage=61;return true;}
            FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Harvest;R.Eye=Eye;R.Direction=(Target-Eye).GetSafeNormal();
            const bool Success=Host->GetPlayerState<AColdSteelPlayerState>()->ExecuteWorldAction(R,M,Reason);
            if(!Success&&Now-HarvestStarted>100.){Record(TEXT("authority_harvest_transaction"),false,Reason);return true;}
            if(H->IsProductionDepleted(Layer,Resource.CandidateId))
            {
                Harvested.Add(Resource.Id);Record(Layer==0?TEXT("tree_harvest_transaction"):TEXT("rock_harvest_transaction"),Success,Resource.Id);
                if(++Layer<2)Stage=5;else{Send(10);Stage=7;}
            }
            Next=Now+.5;return true;
        }
        if(Stage==61&&Probe->Observed==40)
        {
            Record(TEXT("guest_rock_harvest_rpc"),Probe->Passed,Probe->Detail);
            Record(TEXT("authority_confirmed_guest_rock_depletion"),H->IsProductionDepleted(1,CurrentResource.CandidateId));
            Send(10);Stage=7;return true;
        }
        if(Stage==7&&Probe->Observed==10)
        {
            Record(TEXT("client_received_both_depletions"),Probe->Passed,Probe->Detail);
            OldGuest=Guest;Stage=90;if(auto* D=W->GetNetDriver())D->ConnectionTimeout=12.;
            UE_LOG(LogTemp,Display,TEXT("HILLS_SCENERY_DISCONNECT_CLIENT"));return true;
        }
        if(Stage==91)
        {
            Record(TEXT("same_profile_and_world_on_rejoin"),H->WorldId==WorldId&&Guest->GetPlayerState<AColdSteelPlayerState>()->ShadowModel->Snapshot().NetworkProfileId==GuestId);
            NewProbe();Send(11);Stage=92;return true;
        }
        if(Stage==92&&Probe->Observed==11)
        {Record(TEXT("rejoin_keeps_tree_and_rock_depleted"),Probe->Passed,Probe->Detail);return Finish();}
        return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HillsSceneryNetworkProbe"),TEXT("Opt-in scenery transport and harvesting check."),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{if(!Enabled()||!W||W->GetNetMode()!=NM_ListenServer||Output().IsEmpty())return;auto R=MakeShared<FRun>();FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float D){return R->Tick(D);}),.2f);}));
}
#endif
