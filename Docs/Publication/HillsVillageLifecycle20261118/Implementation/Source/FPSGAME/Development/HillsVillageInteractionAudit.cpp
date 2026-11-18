#include "HillsVillageInteractionAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Building/ColdSteelWindow.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/HillsBlacksmith.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "../WorldGeneration/HillsNightPortal.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/NurseZombie.h"
#include "Components/ChildActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "Engine/NetDriver.h"
#include "EngineUtils.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Containers/Ticker.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace HillsVillageAudit
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("HillsVillageInteractionAudit"));
#endif
}
FString Output(){FString P;FParse::Value(FCommandLine::Get(),TEXT("HillsVillageAuditOutput="),P);return P;}
void Save(const FString& Name,const TSharedRef<FJsonObject>& R)
{FString J;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&J));IFileManager::Get().MakeDirectory(*Output(),true);FFileHelper::SaveStringToFile(J,*(Output()/Name+TEXT(".json")));}
template<class T> T* Find(UWorld* W){for(TActorIterator<T> It(W);It;++It)return *It;return nullptr;}
TArray<AColdSteelWindow*> VillageWindows(UWorld* W)
{TArray<AColdSteelWindow*> A;for(TActorIterator<AColdSteelWindow> It(W);It;++It)if(It->ActorHasTag(TEXT("VillageShop.WindowR7")))A.Add(*It);A.Sort([](const auto& L,const auto& R){return L.GetName()<R.GetName();});return A;}
bool WindowState(AColdSteelWindow* W,bool Open,FString& Detail)
{
    if(!W){Detail=TEXT("window not mapped");return false;}
    int32 Hinges=0,Leaves=0;bool OK=W->bUseAuthoredHinges&&W->IsWindowOpen()==Open&&!W->IsActorTickEnabled();
    TInlineComponentArray<USceneComponent*> Parts(W);
    for(auto* C:Parts)
    {
        if(C->GetName().StartsWith(TEXT("WindowHinge"))){++Hinges;OK&=FMath::Abs(FMath::Abs(C->GetRelativeRotation().Yaw)-(Open?105.:0.))<.5;}
        if(auto* M=Cast<UStaticMeshComponent>(C);M&&C->GetName().StartsWith(TEXT("WindowLeaf")))
        {++Leaves;OK&=M->GetStaticMesh()&&M->GetStaticMesh()->GetName().EndsWith(TEXT("R7b"));OK&=M->GetCollisionResponseToChannel(ECC_Pawn)==(Open?ECR_Ignore:ECR_Block);}
    }
    Detail=FString::Printf(TEXT("open=%d tick=%d authored=%d hinges=%d leaves=%d"),W->IsWindowOpen(),W->IsActorTickEnabled(),W->bUseAuthoredHinges,Hinges,Leaves);
    return OK&&Hinges==2&&Leaves==2;
}
bool ShopState(UWorld* W,bool Repaired,FString& Detail)
{
    auto* H=Find<ATemperateHillsWorld>(W);auto* S=Find<AHillsBlacksmith>(W);if(!H||!S)return false;
    int32 Repair=0,Ruin=0,Torches=0;bool Bed=false;
    for(const auto& A:S->ShopAssemblies)if(IsValid(A.Get()))
    {TInlineComponentArray<UStaticMeshComponent*> C(A.Get());for(auto* P:C)if(P->IsVisible())
        {Repair+=P->ComponentHasTag(TEXT("VillageShop.Repaired"));Ruin+=P->ComponentHasTag(TEXT("VillageShop.Ruined"));Bed|=P->GetStaticMesh()&&P->GetStaticMesh()->GetName()==TEXT("SM_VillageTimberBed");}}
    TInlineComponentArray<UChildActorComponent*> Children(S);for(auto* C:Children)if(C->ComponentHasTag(TEXT("VillageShop.Torch"))&&C->GetChildActor())++Torches;
    Detail=FString::Printf(TEXT("repaired=%d station=%d repair=%d ruin=%d bed=%d torches=%d"),H->IsVillageBlacksmithRepaired(),S->IsSceneStationAvailable(),Repair,Ruin,Bed,Torches);
    return H->IsVillageBlacksmithRepaired()==Repaired&&S->IsSceneStationAvailable()==Repaired&&(Repaired?(Repair>0&&Ruin==0&&Bed&&Torches==3):(Repair==0&&Ruin>0&&!Bed&&Torches==0));
}
void Place(APlayerController* PC,FVector Eye,FVector Aim)
{
    auto* P=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;if(!P)return;
    P->SetCanBeDamaged(false);P->GetCharacterMovement()->StopMovementImmediately();P->GetCharacterMovement()->DisableMovement();
    const FVector Offset=P->GetMeleeAimTransform().GetLocation()-P->GetActorLocation();
    P->SetActorLocation(Eye-Offset,false,nullptr,ETeleportType::TeleportPhysics);P->ForceNetUpdate();
    const auto R=(Aim-Eye).Rotation();PC->SetControlRotation(R);PC->ClientSetRotation(R,true);
}
bool Ward(UWorld* W,bool Dormant)
{auto* S=Find<AChapelShrine>(W);return S&&S->IsDormant()==Dormant&&(Dormant?S->bRaidNight:FMath::IsNearlyEqual(S->Durability,S->MaxDurability));}
bool Portal(UWorld* W,bool Exists)
{auto* P=Find<AHillsNightPortal>(W);if(!Exists)return !P;if(!P||P->OpenedAt<=0||P->ClosedAt>=0)return false;TInlineComponentArray<UStaticMeshComponent*> C(P);int32 Loaded=0;for(auto* M:C)Loaded+=M->GetStaticMesh()!=nullptr;return Loaded==3;}
}

AHillsVillageInteractionAudit::AHillsVillageInteractionAudit(){bReplicates=true;bOnlyRelevantToOwner=true;PrimaryActorTick.bCanEverTick=true;}
void AHillsVillageInteractionAudit::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AHillsVillageInteractionAudit,Phase);DOREPLIFETIME(AHillsVillageInteractionAudit,Target);DOREPLIFETIME(AHillsVillageInteractionAudit,Aim);}
void AHillsVillageInteractionAudit::ServerResult_Implementation(int32 Case,bool OK,const FString& Text)
{if(!HillsVillageAudit::Enabled()||Case!=Phase)return;Observed=Case;Passed=OK;Detail=Text;}
void AHillsVillageInteractionAudit::ClientFinish_Implementation(){if(HillsVillageAudit::Enabled())FPlatformMisc::RequestExit(false);}
void AHillsVillageInteractionAudit::Tick(float Dt)
{
    Super::Tick(Dt);using namespace HillsVillageAudit;if(!Enabled()||HasAuthority()||Phase<=0)return;
    auto* PC=Cast<APlayerController>(GetOwner());if(!PC||!PC->GetPawn())return;
    if(Previous!=Phase){Previous=Phase;Began=FPlatformTime::Seconds();Requested=Reported=false;}
    if(Reported)return;const double Age=FPlatformTime::Seconds()-Began;if(Age<3.)return;
    bool OK=false;FString Text;
    if(Phase==1||Phase==9)OK=ShopState(GetWorld(),Phase==9,Text);
    else if(Phase>=2&&Phase<=8)
    {
        auto* W=Cast<AColdSteelWindow>(Target);const bool Open=Phase<8&&Phase%2==0;
        if(W&&!Requested&&(Open||Phase==8))
        {
            FVector Eye;FRotator R;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,R);PC->SetControlRotation((Aim-Eye).Rotation());
            if(auto* Push=PC->GetPawn()->FindComponentByClass<UFPSDoorPushComponent>()){Push->RequestDoorInteraction(W);Requested=true;}
        }
        OK=WindowState(W,Open,Text);if(Age<7.)return;
    }
    else if(Phase==10)
    {
        auto* Run=UDungeonRunSubsystem::Get(GetWorld());
        FVector Eye;FRotator R;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,R);PC->SetControlRotation((Aim-Eye).Rotation());
        if(Run&&Target&&!Requested&&ColdSteelWorldInteraction::TraceTarget(PC)==Target){Requested=Run->ClaimShrine(PC,Target);}
        OK=Run&&Run->HasShrineBlessing(PC->GetPawn());Text=FString::Printf(TEXT("requested=%d focus=%s blessing=%d"),Requested,*GetNameSafe(ColdSteelWorldInteraction::TraceTarget(PC)),OK);
    }
    else if(Phase==11||Phase==12)
    {
        auto* Run=UDungeonRunSubsystem::Get(GetWorld());const bool Blessed=Run&&Run->HasShrineBlessing(PC->GetPawn());
        OK=Ward(GetWorld(),Phase==11)&&Blessed==(Phase==12);
        Text=FString::Printf(TEXT("replicated night durability and dawn restoration blessing=%d"),Blessed);
    }
    else if(Phase==13||Phase==14){OK=Portal(GetWorld(),Phase==13);Text=TEXT("replicated portal lifetime and three loaded mesh parts");}
    else if(Phase==15)
    {
        FString S;const auto All=VillageWindows(GetWorld());
        OK=All.Num()==3&&WindowState(All[0],true,S)&&ShopState(GetWorld(),true,Text)&&Ward(GetWorld(),true)&&Portal(GetWorld(),true);
        Text+=TEXT(" window:")+S;
    }
    if(!OK&&Age<40.)return;
    Reported=true;auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("detail"),Text);Save(FString::Printf(TEXT("client-%02d"),Phase),R);ServerResult(Phase,OK,Text);
}

#if !UE_BUILD_SHIPPING
namespace HillsVillageAudit
{
struct FRun
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<APlayerController> Host,Guest;
    TWeakObjectPtr<AHillsVillageInteractionAudit> Probe;
    TArray<TSharedPtr<FJsonValue>> Checks;
    FGuid GuestId;
    int32 Phase=0;
    double Started=FPlatformTime::Seconds(),Next=0.,NextReadiness=0.;
    bool OK=true,WaitingForLogout=false;
    void Record(const FString& Name,bool Pass,const FString& Detail=FString())
    {auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),Pass);R->SetStringField(TEXT("detail"),Detail);Checks.Add(MakeShared<FJsonValueObject>(R));OK&=Pass;UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE_CASE %s=%d %s"),*Name,Pass,*Detail);}
    bool Finish()
    {auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);R->SetArrayField(TEXT("checks"),Checks);Save(TEXT("result"),R);if(Probe.IsValid())Probe->ClientFinish();FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float){FPlatformMisc::RequestExit(false);return false;}),3.f);return false;}
    void NewProbe()
    {FActorSpawnParameters P;P.Owner=Guest.Get();Probe=World->SpawnActor<AHillsVillageInteractionAudit>(P);}
    void Send(int32 N,AActor* Target=nullptr,FVector Aim=FVector::ZeroVector)
    {Phase=N;Probe->Target=Target;Probe->Aim=Aim;Probe->Observed=0;Probe->Phase=N;Probe->ForceNetUpdate();UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE_PHASE %d target=%s"),N,*GetNameSafe(Target));}
    void DamageShrine(AChapelShrine* S)
    {
        S->SetRaidNight(true,1800.f);FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Raider=World->SpawnActor<ANurseZombie>(S->GetActorLocation()+FVector(2000,0,500),FRotator::ZeroRotator,P);
        if(Raider){Raider->Tags.Add(TEXT("HillsNightRaider"));S->TakeDamage(S->MaxDurability,FDamageEvent(),nullptr,Raider);Raider->Destroy();}
    }
    void SpawnPortal(AChapelShrine* S)
    {
        auto* P=World->SpawnActorDeferred<AHillsNightPortal>(AHillsNightPortal::StaticClass(),FTransform(S->GetActorLocation()+FVector(2500,0,0)),nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(P){P->OpenedAt=World->GetGameState()->GetServerWorldTimeSeconds()-1.;P->FinishSpawning(P->GetActorTransform());}
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();if(Now<Next)return true;
        if(Now-Started>1000.){Record(TEXT("deadline"),false,FString::FromInt(Phase));return Finish();}
        UWorld* W=nullptr;for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->GetNetMode()==NM_ListenServer&&C.World()->HasBegunPlay()){W=C.World();break;}if(!W)return true;World=W;
        Host=nullptr;Guest=nullptr;for(auto It=W->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get()){if(PC->IsLocalController())Host=PC;else Guest=PC;}
        if(WaitingForLogout)
        {if(Guest.IsValid())return true;WaitingForLogout=false;Phase=90;UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE_RECONNECT_READY"));return true;}
        auto* PS=Guest.IsValid()?Guest->GetPlayerState<AColdSteelPlayerState>():nullptr;
        if(!Host.IsValid()||!Host->GetPawn()||!Guest.IsValid()||!Guest->GetPawn()||!PS||!PS->ShadowModel)return true;
        auto* H=Find<ATemperateHillsWorld>(W);auto* S=Find<AChapelShrine>(W);auto* Shop=Find<AHillsBlacksmith>(W);auto All=VillageWindows(W);
        if(!H||!H->bReady||!S||!Shop||!Shop->GetOwner()||All.Num()!=3)
        {
            if(Now>=NextReadiness){NextReadiness=Now+30.;UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE_WAIT hills=%d shrine=%s shop=%s owner=%s windows=%d"),H&&H->bReady,*GetNameSafe(S),*GetNameSafe(Shop),*GetNameSafe(Shop?Shop->GetOwner():nullptr),All.Num());}
            return true;
        }
        if(Phase==0)
        {GuestId=PS->ShadowModel->Snapshot().NetworkProfileId;NewProbe();Send(1);return true;}
        if(Phase==90)
        {Record(TEXT("same_guest_profile_on_rejoin"),GuestId==PS->ShadowModel->Snapshot().NetworkProfileId);NewProbe();Send(15);return true;}
        if(!Probe.IsValid()||Probe->Observed!=Phase)return true;
        Record(FString::Printf(TEXT("client_phase_%02d"),Phase),Probe->Passed,Probe->Detail);
        FString Detail;
        if(Phase==1||Phase==9)Record(TEXT("host_shop_state"),ShopState(W,Phase==9,Detail),Detail);
        if(Phase>=2&&Phase<=8)Record(TEXT("host_window_state"),WindowState(Cast<AColdSteelWindow>(Probe->Target),Phase<8&&Phase%2==0,Detail),Detail);
        if(Phase==10)
        {auto* Run=UDungeonRunSubsystem::Get(W);Record(TEXT("guest_blessing_isolated_from_host"),Run&&Run->HasShrineBlessing(Guest->GetPawn())&&!Run->HasShrineBlessing(Host->GetPawn()));}
        if(Phase==15)return Finish();
        const int32 N=Phase+1;
        if(N>=2&&N<=7)
        {
            auto* Window=All[(N-2)/2];const FVector Aim=Window->GetActorTransform().TransformPosition(FVector(-69,0,-69));
            Place(Guest.Get(),Window->GetActorTransform().TransformPosition(FVector(-190,0,-15)),Aim);
            if(N%2)Window->CloseWindow();Send(N,Window,Aim);
        }
        else if(N==8)
        {auto* Window=All[0];const auto Aim=Window->GetActorLocation();Place(Guest.Get(),Aim+FVector(1100,0,0),Aim);Send(N,Window,Aim);}
        else if(N==9)
        {
            const auto P=Shop->GetActorLocation()+FVector(2500,2500,500);Place(Guest.Get(),P,S->GetActorLocation());Place(Host.Get(),P+FVector(0,400,0),S->GetActorLocation());
            FText Failure;const bool Repaired=H->CompleteVillageBlacksmithRepair(Failure);Record(TEXT("repair_saved_transaction"),Repaired,Failure.ToString());Send(N);
        }
        else if(N==10)
        {
            const auto P=S->GetActorLocation();const auto Aim=S->GetRaidTargetPoint(P+FVector(-600,0,-60))+FVector(0,0,8);
            Place(Guest.Get(),Aim+FVector(-110,0,35),Aim);Send(N,S,Aim);
        }
        else if(N==11){DamageShrine(S);Send(N);}
        else if(N==12){S->SetRaidNight(false,1800.f);Send(N);}
        else if(N==13){SpawnPortal(S);Send(N);}
        else if(N==14){if(auto* P=Find<AHillsNightPortal>(W))P->ClosePortal();Send(N);}
        else if(N==15)
        {
            All[0]->OpenWindow();DamageShrine(S);SpawnPortal(S);Probe->ClientFinish();WaitingForLogout=true;
            UE_LOG(LogTemp,Display,TEXT("HILLS_VILLAGE_DISCONNECT_CLIENT"));
        }
        Next=Now+.3;return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HillsVillageInteractionAudit"),TEXT("Opt-in village interactions over actual UDP."),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{if(!Enabled()||!W||W->GetNetMode()!=NM_ListenServer||Output().IsEmpty())return;auto R=MakeShared<FRun>();FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float D){return R->Tick(D);}),.2f);}));
}
#endif
