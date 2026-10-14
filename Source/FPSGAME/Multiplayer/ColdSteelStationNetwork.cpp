#include "ColdSteelStationNetwork.h"
#include "ColdSteelPlayerState.h"
#include "../UI/ColdSteelProfileRecovery.h"
#include "ColdSteelAuthorityContext.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Building/ForgingSystem.h"
#include "../Building/GunAssemblySystem.h"
#include "../Building/WoodworkingSystem.h"
#include "../Building/CraftingSystem.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"

namespace
{
thread_local int32 InputDepth=0;
FString StationInputJobId(const UColdSteelStatusModel* Model,FName Kind)
{
    if(!Model)return {};
    return Kind==TEXT("forge")?Model->ForgeJob().Id:Kind==TEXT("assembly")?Model->GunAssemblyJob().Id:Model->WoodworkingJob().Id;
}
}
ColdSteelStationNet::FInputScope::FInputScope():Root(InputDepth++==0){}
ColdSteelStationNet::FInputScope::~FInputScope(){--InputDepth;}
bool ColdSteelStationNet::IsClient(const UObject* C){return C&&C->GetWorld()&&C->GetWorld()->GetNetMode()==NM_Client;}
bool ColdSteelStationNet::Request(const UObject* C,const FString& Mode,FName Recipe,int64 Count,AActor* Target,FIntVector Cell)
{
    auto* PC=UGameplayStatics::GetPlayerController(C,0);auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!PS)return false;FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Workstation;R.Mode=Mode;R.Definition=Recipe;R.Count=Count;R.Target=Target;R.Anchor=Cell;
    if(Mode.StartsWith(TEXT("wood."))&&Mode!=TEXT("wood.start"))
        if(const auto* M=ColdSteelAuthority::Model(C))R.Item=M->WoodworkingJob().Id;
    return PS->RequestInventoryAction(R);
}
void ColdSteelStationNet::Input(const UObject* C,FName System,uint8 Op,FName Recipe,int32 Index,FVector2D A,FVector2D B)
{
    if(!IsClient(C))return;auto* PC=UGameplayStatics::GetPlayerController(C,0);
    if(auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr)
        PS->ServerStationInput(PC->GetPawn(),StationInputJobId(ColdSteelAuthority::ForPawn(PC->GetPawn()),System),System,Op,Recipe,Index,A,B,System==TEXT("wood")?++PS->WoodInputSerial:0);
}
bool AColdSteelPlayerState::StationReach(FName Kind) const
{
    const auto* Pawn=GetPawn();const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||!Health||Health->IsDead())return false;
    for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
    {
        const auto* Piece=*It;const auto* World=Cast<AVoxelBuildWorld>(Piece->GetOwner());
        if(Piece->IsFalling()||!World||!World->HasPrefabAt(Piece->AnchorCell()))continue;
        const bool Matches=Kind==TEXT("forge")?ColdSteelWorldInteraction::IsForgingStation(Piece):Kind==TEXT("wood")?ColdSteelWorldInteraction::IsWoodworkingBench(Piece):ColdSteelWorldInteraction::IsWorkbench(Piece);
        if(!Matches)continue;
        const FVector Near=Piece->GetComponentsBoundingBox(true).GetClosestPointTo(Pawn->GetPawnViewLocation());
        if(FVector::DistSquared(Near,Pawn->GetPawnViewLocation())>FMath::Square(500.f))continue;
        FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(WorkstationReach),false,Pawn);
        if(!GetWorld()->LineTraceSingleByChannel(Hit,Pawn->GetPawnViewLocation(),Near,ECC_Visibility,Q)||Hit.GetActor()==Piece)return true;
    }
    return false;
}
void AColdSteelPlayerState::InitializeStations(UColdSteelStatusModel* M)
{
    auto* GI=GetGameInstance();if(!M||!GI)return;
    if(!GuestForge||!GuestAssembly||!GuestWood)bStationDirty=bWoodDirty=true;
    if(!GuestForge)GuestForge=GI->GetSubsystem<UColdSteelForgingSystem>()->CreateNetworkSession(M);
    if(!GuestAssembly)GuestAssembly=GI->GetSubsystem<UGunAssemblySystem>()->CreateNetworkSession(M);
    if(!GuestWood)GuestWood=GI->GetSubsystem<UWoodworkingSystem>()->CreateNetworkSession(M);
}
bool AColdSteelPlayerState::ExecuteWorldAction(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason)
{
    if(R.Action==EColdSteelInventoryAction::Harvest||R.Action==EColdSteelInventoryAction::SoilRefill)
    {const double Now=GetWorld()->GetTimeSeconds();if(Now<HarvestAt){Reason=TEXT("工具尚未收势");return false;}HarvestAt=Now+.35;}
    auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();auto* PC=Cast<APlayerController>(GetOwner());
    return Shared&&PC&&Shared->WorldAction(M,PC->IsLocalController()?nullptr:this,R,Reason);
}
bool AColdSteelPlayerState::ExecuteStation(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason)
{
    InitializeStations(M);const FString& Mode=R.Mode;bool Ok=false;
    ColdSteelAuthority::FScope Context(M);
    if(Mode.StartsWith(TEXT("forge.")))
    {
        if(!StationReach(TEXT("forge"))){Reason=TEXT("请靠近铸造台");return false;}
        if(Mode==TEXT("forge.start"))Ok=GuestForge->Start(R.Definition,Reason);
        else if(Mode==TEXT("forge.finish"))Ok=GuestForge->Finish(Reason);
        else if(Mode==TEXT("forge.claim"))Ok=GuestForge->Claim(Reason);
        else if(Mode==TEXT("forge.discard"))Ok=GuestForge->Discard(Reason);
    }
    else if(Mode.StartsWith(TEXT("assembly.")))
    {
        if(!StationReach(TEXT("assembly"))){Reason=TEXT("请靠近枪械工作台");return false;}
        if(Mode==TEXT("assembly.start")){GuestAssembly->SelectRecipe(R.Definition);Ok=GuestAssembly->Start(Reason);CalibrationAt=GetWorld()->GetTimeSeconds();}
        else if(Mode==TEXT("assembly.finish"))Ok=GuestAssembly->Finish(Reason);
        else if(Mode==TEXT("assembly.claim"))Ok=GuestAssembly->Claim(Reason);
        else if(Mode==TEXT("assembly.discard"))Ok=GuestAssembly->Discard(Reason);
    }
    else if(Mode.StartsWith(TEXT("wood.")))
    {
        if(!StationReach(TEXT("wood"))){Reason=TEXT("请靠近木工工作台");return false;}
        if(Mode!=TEXT("wood.start")&&(R.Item.IsEmpty()||R.Item!=M->WoodworkingJob().Id))
        {Reason=TEXT("木工工件已变化，请同步后重试");return false;}
        if(Mode==TEXT("wood.start"))
        {if(!GuestWood->NetworkOpen())GuestWood->Open(false);if(GuestWood->Select(R.Definition))Ok=GuestWood->StartMode(EWoodworkingMode::Craft);}
        else if(Mode==TEXT("wood.resume"))
        {if(!GuestWood->NetworkOpen())GuestWood->Open(false);Ok=GuestWood->Resume();}
        else if(Mode==TEXT("wood.claim"))Ok=GuestWood->Claim();
        else if(Mode==TEXT("wood.discard"))Ok=GuestWood->Discard();
        else if(Mode==TEXT("wood.settle"))Ok=GuestWood->Settle();
        Reason=GuestWood->Message();
    }
    else if(Mode==TEXT("craft"))
    {if(!StationReach(TEXT("craft")))return false;Ok=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>()->Craft(R.Definition,R.Count,Reason);}
    else if(Mode.StartsWith(TEXT("smelt.")))
    {
        auto* W=Cast<AVoxelBuildWorld>(R.Target);auto* Piece=W?W->PrefabActorAt(R.Anchor):nullptr;
        if(!W||W->GetWorld()!=GetWorld()||!Piece||Piece->IsFalling()||!W->IsFurnaceAt(R.Anchor)
            ||Piece->GetComponentsBoundingBox(true).ComputeSquaredDistanceToPoint(GetPawn()->GetPawnViewLocation())>FMath::Square(600.f))return false;
        auto* Smelt=GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>();
        if(Mode==TEXT("smelt.start"))Ok=Smelt->BeginSmelting(W,R.Anchor,R.Definition,Reason,R.Count);
        else if(Mode==TEXT("smelt.fuel"))Ok=Smelt->AddFuel(W,R.Anchor,Reason);
        else if(Mode==TEXT("smelt.collect"))Ok=Smelt->CollectSmelting(W,R.Anchor,Reason);
        else if(Mode==TEXT("smelt.upgrade"))Ok=Smelt->UpgradeFurnace(W,R.Anchor,Reason,int32(R.Count));
    }
    bStationDirty=true;if(Mode.StartsWith(TEXT("wood.")))bWoodDirty=true;return Ok;
}
void AColdSteelPlayerState::ServerStationInput_Implementation(APawn* InputPawn,const FString& JobId,FName System,uint8 Op,FName Recipe,int32 Index,FVector2D A,FVector2D B,uint32 Sequence)
{
    auto* M=ColdSteelAuthority::ForPawn(GetPawn());if(!M||A.ContainsNaN()||B.ContainsNaN())return;
    InitializeStations(M);ColdSteelAuthority::FScope Context(M);FString Reason;
    if(System==TEXT("wood"))
    {
        if(!Sequence||static_cast<int32>(Sequence-WoodAuthoritySequence)<=0)return;
        WoodAuthoritySequence=Sequence;bWoodDirty=true;
    }
    if(InputPawn!=GetPawn()||JobId!=StationInputJobId(M,System)){bStationDirty=true;return;}
    InvalidateTeamTravelReady();
    // Pausing is cleanup, so permit it after leaving the bench. Pawn/job
    // identity was checked above; progress input still requires station reach.
    if(System==TEXT("assembly")&&Op==2)
    {
        const bool Paused=GuestAssembly->Pause(Reason);
        const bool Saved=Paused&&SaveShadowToHostDisk();
        bStationDirty=true;bServerDirty=!Saved;return;
    }
    if(!StationReach(System))
    {
        if(System==TEXT("wood"))GuestWood->NetworkUnavailable(TEXT("已离开木工工作台或角色无法操作，本次加工已停止"));
        return;
    }
    if(System==TEXT("forge"))
    {
        if(Op==0)GuestForge->BeginStrike(Index,FMath::Clamp(A.X,0.,2.),FMath::Clamp(A.Y,0.,3.));
        if(Op==1&&B.X>0&&B.Y>0&&B.X<=.25&&B.Y<=.25)GuestForge->Strike(Index,A,B);
    }
    else if(System==TEXT("assembly"))
    {
        if(Op==0&&A.X>=0)GuestAssembly->Install(Index,float(A.X),float(A.Y),Reason);
        if(Op==1)
        {
            const double Now=GetWorld()->GetTimeSeconds();float Dt=float(FMath::Clamp(FMath::Min(A.X,Now-CalibrationAt),0.,.25));CalibrationAt=Now;
            while(Dt>0){const float Step=FMath::Min(Dt,.05f);GuestAssembly->Calibrate(Step,float(A.Y));Dt-=Step;}
        }
    }
    else if(System==TEXT("wood"))
    {
        switch(Op)
        {
            case 0:GuestWood->Open(Index!=0);break;case 1:GuestWood->Select(Recipe);break;
            case 2:break; // Paid starts use the inventory transaction and its receipt.
            case 3:GuestWood->BeginFeed();break;case 4:if(A.Size()<=4096)GuestWood->MoveBoard(A);break;
            case 5:GuestWood->RotateBoard(Index,A.X!=0);break;case 6:GuestWood->ToggleMotor();break;
            case 7:GuestWood->EndStroke();break;case 8:GuestWood->Undo();break;case 9:GuestWood->Finish();break;
            case 10:GuestWood->Abandon();break;case 11:GuestWood->Close();break;
            case 12:GuestWood->Settle();break;
            case 13:GuestWood->Suspend();break;
        }
    }
    bStationDirty=true;bServerDirty=true;
}
void AColdSteelPlayerState::TickStations(float Delta)
{
    if(!HasAuthority()||(!GuestForge&&!GuestAssembly))return;
    auto* PC=Cast<APlayerController>(GetOwner());if(!PC||PC->IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(Now<StationPublishAt)return;StationPublishAt=Now+.25;
    if(GuestForge&&GuestForge->Active()&&!StationReach(TEXT("forge")))
    {FString Reason;GuestForge->Finish(Reason);bStationDirty=true;bServerDirty=true;}
    if(!bStationDirty&&(!GuestForge||GuestForge->Job().Id.IsEmpty()))return;bStationDirty=false;
    auto Forge=GuestForge?GuestForge->NetworkState():FColdSteelForgeNetState{};
    FColdSteelAssemblyNetState Assembly;
    if(GuestAssembly)
    {
        const auto& Job=GuestAssembly->Job();Assembly.Id=Job.Id;Assembly.InstalledMask=Job.InstalledMask;
        Assembly.Scores=Job.Scores;Assembly.Misses=Job.Misses;Assembly.CalibrationSeconds=Job.CalibrationSeconds;
        Assembly.CalibrationTime=Job.CalibrationTime;Assembly.CalibrationError=Job.CalibrationError;
        Assembly.Quality=Job.Quality;Assembly.Finished=Job.bFinished;
    }
    // These RPC states intentionally omit Item/PaidMaterials; inventory receipts own payment data.
    ClientStationState(Forge,Assembly,GetPawn());
}
void AColdSteelPlayerState::ClientStationState_Implementation(const FColdSteelForgeNetState& Forge,const FColdSteelAssemblyNetState& Assembly,APawn* SourcePawn)
{
    if(!SourcePawn||SourcePawn!=GetPawn())return;
    auto* M=ColdSteelAuthority::Model(this);if(!M)return;
    const auto Previous=M->Snapshot();auto P=Previous;
    if(P.ForgeJob.Id==Forge.JobId){P.ForgeJob.Hits=Forge.Hits;P.ForgeJob.bFinished=Forge.Finished;}
    if(P.GunAssemblyJob.Id==Assembly.Id)
    {
        auto& Job=P.GunAssemblyJob;Job.InstalledMask=Assembly.InstalledMask;Job.Scores=Assembly.Scores;Job.Misses=Assembly.Misses;
        Job.CalibrationSeconds=Assembly.CalibrationSeconds;Job.CalibrationTime=Assembly.CalibrationTime;
        Job.CalibrationError=Assembly.CalibrationError;Job.Quality=Assembly.Quality;Job.bFinished=Assembly.Finished;
    }
    ColdSteelProfileRecovery::StationProgress(P,Previous);
    M->AdoptNetMirror(P);
    GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>()->ApplyNetworkState(Forge);M->NotifyChanged();
}

bool AColdSteelPlayerState::CloseStationSessions()
{
    if(!HasAuthority())return true;
    auto* PC=Cast<APlayerController>(GetOwner());
    const bool Local=PC&&PC->IsLocalController();
    auto* Forge=Local?GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>():GuestForge.Get();
    auto* Wood=Local?GetGameInstance()->GetSubsystem<UWoodworkingSystem>():GuestWood.Get();
    auto* Assembly=Local?GetGameInstance()->GetSubsystem<UGunAssemblySystem>():GuestAssembly.Get();
    FString Reason;
    if(Assembly&&!Assembly->Pause(Reason))return false;
    if(Forge&&Forge->Active()&&!Forge->Finish(Reason))return false;
    if(Wood)
    {
        bWoodDirty=true;if(!Wood->Close())return false;
    }
    bServerDirty=true;
    return !ShadowModel||SaveShadowToHostDisk();
}
