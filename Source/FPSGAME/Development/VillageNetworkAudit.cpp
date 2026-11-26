#include "VillageNetworkAudit.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/ChapelNun.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../Movement/FPSTraversalComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseDebris.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"

AVillageNetworkAudit::AVillageNetworkAudit()
{bReplicates=true;bOnlyRelevantToOwner=true;PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.05f;}
void AVillageNetworkAudit::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AVillageNetworkAudit,Phase);DOREPLIFETIME(AVillageNetworkAudit,Target);
    DOREPLIFETIME(AVillageNetworkAudit,Position);DOREPLIFETIME(AVillageNetworkAudit,Aim);DOREPLIFETIME(AVillageNetworkAudit,ExpectedHealth);
    DOREPLIFETIME(AVillageNetworkAudit,SocketPosition);
}
void AVillageNetworkAudit::ServerResult_Implementation(int32 Case,bool Pass,const FString& Detail)
{if(!VillageNetAudit::Enabled()||Case!=Phase)return;Observed=Case;bPeerPassed=Pass;PeerDetail=Detail;UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_PEER case=%d pass=%d %s"),Case,Pass,*Detail);}
void AVillageNetworkAudit::ClientFinish_Implementation()
{if(VillageNetAudit::Enabled())FPlatformMisc::RequestExit(false);}
void AVillageNetworkAudit::Tick(float Dt)
{
    Super::Tick(Dt);if(!VillageNetAudit::Enabled())return;
    static const bool bConstruction=FParse::Param(FCommandLine::Get(),TEXT("VillageConstructionAudit"));
    if(bConstruction)
    {
        if(bDirector&&HasAuthority())RunConstructionHost();else if(!HasAuthority())RunConstructionClient();
        return;
    }
    if(bDirector&&HasAuthority())RunHost();else if(!HasAuthority())RunClient();
}
void AVillageNetworkAudit::RunClient()
{
    using namespace VillageNetAudit;
    auto* PC=Cast<APlayerController>(GetOwner());auto* C=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    auto* M=Model(PC);auto* H=FindHills(GetWorld());auto* N=FindNun(GetWorld());
    auto* D=PC?PC->FindComponentByClass<UChapelDialogueComponent>():nullptr;
    if(!C||!M||!H||!N||!D||Phase<=0)return;
    if(PreviousPhase!=Phase){PreviousPhase=Phase;ClientAt=FPlatformTime::Seconds();bRequested=bReported=false;}
    if(bReported)return;
    const double Age=FPlatformTime::Seconds()-ClientAt;
    bool Ready=false,OK=false;FString Detail;
    if(Phase==1)
    {Ready=M->Level>=15;OK=Ready&&!D->HolyLightLearned();Detail=FString::Printf(TEXT("level=%d learned=%d"),M->Level,D->HolyLightLearned());}
    else if(Phase==10)
    {
        if(!bRequested){Place(PC,Position,Aim);D->Open(N);bRequested=D->IsPending()||D->IsOpen();}
        Ready=D->IsOpen()&&!D->IsPending()&&Age>3.;OK=Ready&&Facing(N,PC,Detail);
        if(Ready&&!OK&&Age<90.)Ready=false;
    }
    else if(Phase==20||Phase==30||Phase==40)
    {
        if(!bRequested&&D->IsOpen()&&!D->IsPending())
        {D->RequestAction(Phase==20?TEXT("wall"):Phase==30?TEXT("blacksmith"):TEXT("holyLight"));bRequested=true;}
        Ready=bRequested&&!D->IsPending()&&Age>1.;
        if(Phase==20){Ready&=H->IsVillageWallRepaired();OK=Ready;Detail=D->Message;}
        if(Phase==30){Ready&=H->IsVillageBlacksmithRepaired();OK=Ready&&ShopState(GetWorld(),Detail);}
        if(Phase==40){Ready&=D->HolyLightLearned();OK=Ready;Detail=D->Message;}
    }
    else if(Phase==50)
    {
        auto* G=Cast<AVillageDefenseGate>(Target);
        if(G&&!bRequested){D->Close();Place(PC,Position,Aim);bRequested=C->FindComponentByClass<UFPSDoorPushComponent>()->RequestDoorInteraction(G);}
        Ready=bRequested&&Age>3.&&G&&G->GetGateAngle()>87.f;OK=Ready&&GatePose(G,true,Detail);
    }
    else if(Phase==60)
    {Ready=Target&&Age>2.&&D->HolyLightLearned();OK=Ready&&GatePose(Cast<AVillageDefenseGate>(Target),true,Detail);}
    else if(Phase==65)
    {if(!bRequested){D->Close();Place(PC,Position,Aim);bRequested=true;}Ready=Age>1.;OK=Ready;Detail=TEXT("observer moved clear of siege perception and gate swing");}
    else if(Phase==70)
    {
        auto* T=C->FindComponentByClass<UFPSTraversalComponent>();
        if(Target&&T&&!bRequested)
        {
            D->Close();Place(PC,Position,Aim,true);RequestsAtStart=T->NetworkRequest;T->bLastTraversalSucceeded=false;
            PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Pressed,1.f));bRequested=true;
        }
        Ready=bRequested&&T&&T->bLastTraversalSucceeded&&!T->IsTraversing();
        if(Ready){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Released,0.f));OK=T->NetworkRequest>=RequestsAtStart+2;
            Detail=FString::Printf(TEXT("requests=%u success=%d pos=%s"),T->NetworkRequest-RequestsAtStart,T->bLastTraversalSucceeded,*C->GetActorLocation().ToString());}
        if(!Ready&&Age>14.&&T){Ready=true;OK=false;Detail=FString::Printf(TEXT("requests=%u consumed=%d held=%d traversing=%d reason=%s pos=%s"),T->NetworkRequest-RequestsAtStart,T->bJumpRequestConsumed,T->bJumpHeld,T->IsTraversing(),*T->FindTarget(true,true).Reason,*C->GetActorLocation().ToString());PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Released,0.f));}
    }
    else if(Phase==80||Phase==92)
    {
        auto* S=Cast<AVillageDefenseSection>(Target);
        Ready=S&&Age>1.&&FMath::IsNearlyEqual(S->GetHealth(),ExpectedHealth,.01f);
        OK=Ready&&S->GetMasonry()->GetCollisionEnabled()==ECollisionEnabled::NoCollision;
        Detail=S?FString::Printf(TEXT("section=%d health=%.1f collision=%d"),S->GetSectionId(),S->GetHealth(),int32(S->GetMasonry()->GetCollisionEnabled())):TEXT("section not mapped");
    }
    else if(Phase==90)
    {
        if(auto* G=Cast<AVillageDefenseGate>(Target);G&&G->GetMasonry()->GetStaticMesh())
        {
            TInlineComponentArray<UStaticMeshComponent*> Parts(G);
            for(auto* P:Parts)if(P->GetFName()==TEXT("RightLeaf")){P->SetStaticMesh(nullptr);Ready=OK=true;Detail=TEXT("injected right mesh still loading; left mesh loaded");}
        }
    }
    else if(Phase==91)
    {
        auto* G=Cast<AVillageDefenseGate>(Target);Ready=G&&G->GetHealth()<=0&&Age>1.;OK=Ready;
        if(Ready&&!bRequested){G->ProcessEvent(G->FindFunction(TEXT("OnRep_Setup")),nullptr);bRequested=true;}
        if(G){TInlineComponentArray<UStaticMeshComponent*> Parts(G);for(auto* P:Parts)if(P->GetFName()==TEXT("Masonry")||P->GetFName()==TEXT("RightLeaf"))OK&=!P->IsVisible()&&P->GetCollisionEnabled()==ECollisionEnabled::NoCollision;}
        Detail=TEXT("survived missing-right-mesh destruction; load completion does not restore visibility or collision");
    }
    else if(Phase==93)
    {
        if(Age>13.){int32 Count=0;for(TActorIterator<AVillageDefenseDebris> It(GetWorld());It;++It)++Count;Ready=true;OK=Count==0;Detail=FString::Printf(TEXT("debris actors after timeout=%d"),Count);}
    }
    else if(Phase==100)
    {if(!bRequested){Place(PC,Position,Aim);D->Open(N);bRequested=D->IsPending()||D->IsOpen();}Ready=D->IsOpen()&&!D->IsPending();OK=Ready;ConversationSession=D->LocalSession;Detail=TEXT("live conversation established before death");}
    else if(Phase==101)
    {
        if(!bRequested)
        {
            // Deliberately bypass the local button gate, but send real production RPCs.
            // This represents queued/modified-client requests after authority death.
            D->ServerAction(ConversationSession,TEXT("holyLight"));
            D->Close();
            D->LocalSession=ConversationSession+100;D->LocalNun=N;D->bPending=true;D->Message.Reset();
            D->ServerOpen(D->LocalSession,H,C);bRequested=true;
        }
        Ready=bRequested&&!D->bPending&&Age>1.;OK=Ready&&!D->IsOpen()&&!D->Message.IsEmpty();Detail=D->Message;
    }
    if(!Ready&&Age>100.){Ready=true;OK=false;Detail=FString::Printf(TEXT("phase timeout phase=%d pending=%d open=%d msg=%s"),Phase,D->IsPending(),D->IsOpen(),*D->Message);}
    if(Ready){bReported=true;ServerResult(Phase,OK,Detail);}
}
