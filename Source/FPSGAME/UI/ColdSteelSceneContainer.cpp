#include "ColdSteelSceneContainer.h"

#include "ColdSteelHUDWidget.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelSceneLoot.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelContainerSearchSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "Engine/GameInstance.h"
#include "../FPSGAMEPlayerController.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/GameStateBase.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Net/UnrealNetwork.h"

AColdSteelSceneContainer::AColdSteelSceneContainer()
{
    PrimaryActorTick.bCanEverTick=true;
    bReplicates=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("ContainerRoot"));
    Root->SetMobility(EComponentMobility::Static);
    SetRootComponent(Root);
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
    Body->SetupAttachment(Root);
    Body->SetMobility(EComponentMobility::Static);
    Body->SetCollisionProfileName(TEXT("BlockAll"));
    DoorHinge=CreateDefaultSubobject<USceneComponent>(TEXT("DoorHinge"));
    DoorHinge->SetupAttachment(Root);
    DoorHinge->SetMobility(EComponentMobility::Movable);
    DoorHinge->SetRelativeLocation(FVector(-29.f,28.4f,0.f));
    Door=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Door"));
    Door->SetupAttachment(DoorHinge);
    Door->SetMobility(EComponentMobility::Movable);
    Door->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Tags.Add(TEXT("ColdSteel.SceneContainer"));
    SetViewHighlighted(false);
}

void AColdSteelSceneContainer::BeginPlay()
{
    Super::BeginPlay();
    ClosedDoorRotation=DoorHinge->GetRelativeRotation();
    ClosedMovingPartLocation=DoorHinge->GetRelativeLocation();
    // Preserve this legacy key for old private contents and authored door poses.
    FString MapName=GetWorld()->GetMapName();
    MapName.RemoveFromStart(GetWorld()->StreamingLevelsPrefix);
    RuntimeStorageKey=TEXT("SceneSearch.")+MapName+TEXT(".")
        +(ContainerId.IsEmpty()?GetName():ContainerId);
    const float InitialFraction=FMath::Clamp(InitialOpenFraction,0.f,1.f);
    ReusableDoorFraction=InitialFraction;
    FRandomStream InitialPose(GetTypeHash(RuntimeStorageKey));
    if(InitialFraction>0.f)
    {
        if(OpeningMotion==EColdSteelContainerMotion::Drawer||OpeningMotion==EColdSteelContainerMotion::OpenShelf)
            DoorHinge->SetRelativeLocation(ClosedMovingPartLocation+DrawerTravel*InitialFraction);
        else
        {
            FRotator Initial=ClosedDoorRotation;
            if(OpeningMotion==EColdSteelContainerMotion::Lid)Initial.Roll+=OpenedRoll*InitialFraction;
            else Initial.Yaw+=OpenedYaw*InitialFraction;
            DoorHinge->SetRelativeRotation(Initial);
        }
    }
    else if(OpeningMotion==EColdSteelContainerMotion::Swing&&ActorHasTag(TEXT("ColdSteel.SceneContainer.RandomOpen"))&&InitialPose.FRand()<.32f)
    {
        FRotator Initial=ClosedDoorRotation;
        Initial.Yaw+=InitialPose.FRandRange(38.f,78.f);
        DoorHinge->SetRelativeRotation(Initial);
    }
    SetViewHighlighted(false);
    bVisualInitialized=true;if(bSearched)OnRep_Searched();
    if(UsesReusableDoor()&&DoorState.bValid)OnRep_DoorState();
    if(ColdSteelSceneLoot::IsBound(this)&&GetNetMode()!=NM_Client)
    {
        if(GetNetMode()==NM_Standalone)
        {
            const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
            if(Model&&Run&&Run->IsRunActive()&&Model->Snapshot().DungeonRun.RunId==Run->RunId()
                &&Model->HasDungeonClaim(ColdSteelSceneLoot::Claim(ContainerId)))OpenSharedVisual(true);
        }
        else if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();Shared&&Shared->InitializeAuthority())
            if(const auto* Stored=Shared->Data().Containers.Find(StorageKey());Stored&&Stored->bSceneLootResolved)OpenSharedVisual(true);
    }
}

FString AColdSteelSceneContainer::StorageKey() const
{
    if(ColdSteelSceneLoot::IsBound(this))
        if(const auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&Run->IsRunActive())
            return RuntimeStorageKey+TEXT(".Run.")+Run->RunId();
    return RuntimeStorageKey;
}

void AColdSteelSceneContainer::ApplyOutline()
{
    // Dedicated post-process uses 201=unsearched, 202=searched. Other stencil
    // users (including first-person whirlwind 231) are left untouched.
    for(auto* Part:{Body.Get(),Door.Get()})
    {
        Part->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
        Part->SetCustomDepthStencilValue(bSearched?202:201);
    }
}

void AColdSteelSceneContainer::SetViewHighlighted(bool bHighlighted)
{
    ApplyOutline();
    for(auto* Part:{Body.Get(),Door.Get()})Part->SetRenderCustomDepth(bHighlighted);
}

FString AColdSteelSceneContainer::GetPromptLabel() const
{
    return Caption+(bOpening?(bClosingReusableDoor?TEXT(" · 关闭中"):TEXT(" · 开启中")):bSearched?TEXT(" · 再次查看"):TEXT(" · 搜寻"));
}

bool AColdSteelSceneContainer::IsWithinPanelReach(const APlayerController* Controller) const
{
    const APawn* Pawn=Controller?Controller->GetPawn().Get():nullptr;
    return Pawn&&Pawn->GetWorld()==GetWorld()
        &&FVector::Dist(Pawn->GetActorLocation(),GetActorLocation()+FVector(0,0,70))<=240.f;
}

void AColdSteelSceneContainer::OpenLootPanel(APlayerController* Controller)
{
    const auto* PC=Cast<AFPSGAMEPlayerController>(Controller);
    auto* HUD=PC?PC->GetColdSteelHUD():nullptr;
    if(HUD&&!HUD->IsInventoryOpen()&&IsWithinPanelReach(Controller))
        HUD->OpenChestLootStorage(this,StorageKey(),FMath::Clamp(StoragePages,1,8),Caption+TEXT(" · 搜寻物品"));
}

bool AColdSteelSceneContainer::TrySearch(APlayerController* Controller)
{
    const auto* PC=Cast<AFPSGAMEPlayerController>(Controller);
    if(!PC||!PC->GetColdSteelHUD()||!Door||!Door->GetStaticMesh()||bOpening||!IsWithinPanelReach(Controller)
        ||ColdSteelWorldInteraction::FocusedSceneContainer(Controller)!=this)return false;
    if(GetNetMode()!=NM_Standalone)
    {
        auto* PS=Controller->GetPlayerState<AColdSteelPlayerState>();
        return PS&&PS->RequestInventoryAction(EColdSteelInventoryAction::ContainerOpen,FString(),this);
    }
    if(ColdSteelSceneLoot::IsBound(this))
    {
        auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Model)return false;
        if(!Model->HasDungeonClaim(ColdSteelSceneLoot::Claim(ContainerId)))
        {
            Model->SyncRuntime();auto State=Model->Snapshot();FString Reason;
            if(!Model->AppendSceneSearchLoot(State,this,Reason)||!Model->CommitState(MoveTemp(State)))
            {Model->PostNotice(TEXT("搜索失败"),Reason.IsEmpty()?Model->ResultMessage():Reason);return false;}
        }
    }
    if(bSearched)
    {
        if(UsesReusableDoor())
        {OpeningController=Controller;StartReusableDoor(false);}
        else OpenLootPanel(Controller);
        return true;
    }
    OpeningController=Controller;OpenSharedVisual();return true;
}

bool AColdSteelSceneContainer::UsesReusableDoor() const
{
    return ActorHasTag(TEXT("ColdSteel.SceneContainer.Reclosable"))||DoorState.bValid;
}

float AColdSteelSceneContainer::DoorClock() const
{const auto* GS=GetWorld()->GetGameState();return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}

float AColdSteelSceneContainer::GetDoorOpenFraction() const
{
    if(!DoorState.bValid)return ReusableDoorFraction;
    const float T=FMath::Clamp((DoorClock()-DoorState.Started)/FMath::Max(.1f,DoorState.Duration),0.f,1.f);
    return FMath::Lerp(DoorState.From,DoorState.To,T*T*(3.f-2.f*T));
}

void AColdSteelSceneContainer::ApplyReusableDoor()
{
    ReusableDoorFraction=GetDoorOpenFraction();
    if(OpeningMotion==EColdSteelContainerMotion::Drawer||OpeningMotion==EColdSteelContainerMotion::OpenShelf)
        DoorHinge->SetRelativeLocation(ClosedMovingPartLocation+DrawerTravel*ReusableDoorFraction);
    else
    {
        FRotator Rotation=ClosedDoorRotation;
        if(OpeningMotion==EColdSteelContainerMotion::Lid)Rotation.Roll+=OpenedRoll*ReusableDoorFraction;
        else Rotation.Yaw+=OpenedYaw*ReusableDoorFraction;
        DoorHinge->SetRelativeRotation(Rotation);
    }
}

void AColdSteelSceneContainer::OnRep_DoorState()
{
    if(!bVisualInitialized||!UsesReusableDoor()||!DoorState.bValid)return;
    bClosingReusableDoor=DoorState.To<.5f;
    ApplyReusableDoor();
    bOpening=DoorClock()<DoorState.Started+DoorState.Duration;
    SetActorTickEnabled(bOpening);
}

void AColdSteelSceneContainer::StartReusableDoor(bool bClose)
{
    if(!HasAuthority()||GetNetMode()==NM_Client)return;
    const float Current=GetDoorOpenFraction(),Target=bClose?0.f:1.f;
    if(DoorState.bValid&&DoorState.To==Target&&(bOpening||FMath::IsNearlyEqual(Current,Target)))
    {
        if(!bClose&&!bOpening){OpenLootPanel(OpeningController.Get());OpeningController.Reset();}
        return;
    }
    bClosingReusableDoor=bClose;
    ReusableDoorStart=Current;
    OpeningElapsed=0.f;
    DoorState.bValid=true;DoorState.From=Current;DoorState.To=Target;DoorState.Started=DoorClock();
    DoorState.Duration=FMath::Max(.1f,OpeningDuration*FMath::Abs(Target-Current));
    OnRep_DoorState();ForceNetUpdate();
}

void AColdSteelSceneContainer::CloseLootVisual()
{
    if(!UsesReusableDoor()||!bVisualInitialized||!HasAuthority()||GetNetMode()==NM_Client)return;
    if(const auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>();Search&&Search->HasViewers(this))return;
    OpeningController.Reset();
    StartReusableDoor(true);
}

void AColdSteelSceneContainer::OpenSharedVisual(bool bInstant)
{
    if(UsesReusableDoor())
    {
        if(!HasAuthority()||GetNetMode()==NM_Client)return;
        bSearched=true;ApplyOutline();StartReusableDoor(false);
        if(bInstant){DoorState.Started=DoorClock()-DoorState.Duration;OnRep_DoorState();}
        ForceNetUpdate();return;
    }
    if(bSearched)return;
    bSearched=true;OnRep_Searched();ForceNetUpdate();
    if(bInstant&&bOpening)Tick(OpeningDuration);
    if(GetNetMode()!=NM_Client&&GetNetMode()!=NM_Standalone&&!GetIsReplicated())
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(auto* PC=It->Get();PC&&!PC->IsLocalController())
                if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())PS->ClientGeneratedContainerOpened(GetName());
}
void AColdSteelSceneContainer::OnRep_Searched()
{
    if(!bSearched||!bVisualInitialized)return;
    ApplyOutline();
    if(UsesReusableDoor()){OnRep_DoorState();return;}
    if(bOpening)return;
    // An initially ajar cabinet is still unsearched. Continue from its current
    // pose to the original final opening angle, without snapping closed first.
    if(OpeningMotion==EColdSteelContainerMotion::Swing)
    {
        const FRotator Start=DoorHinge->GetRelativeRotation();
        OpenedYaw-=Start.Yaw-ClosedDoorRotation.Yaw;
        ClosedDoorRotation=Start;
    }
    else if(OpeningMotion==EColdSteelContainerMotion::Lid)
    {
        const FRotator Start=DoorHinge->GetRelativeRotation();
        OpenedRoll-=Start.Roll-ClosedDoorRotation.Roll;
        ClosedDoorRotation=Start;
    }
    else
    {
        const FVector Start=DoorHinge->GetRelativeLocation();
        DrawerTravel-=Start-ClosedMovingPartLocation;
        ClosedMovingPartLocation=Start;
    }
    bOpening=true;
    OpeningElapsed=0.f;
    SetActorTickEnabled(true);
}
void AColdSteelSceneContainer::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AColdSteelSceneContainer,bSearched);
    DOREPLIFETIME(AColdSteelSceneContainer,DoorState);
}

void AColdSteelSceneContainer::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(UsesReusableDoor())
    {
        ApplyReusableDoor();
        if(DoorClock()>=DoorState.Started+DoorState.Duration)
        {
            bOpening=false;SetActorTickEnabled(false);
            if(!bClosingReusableDoor)OpenLootPanel(OpeningController.Get());
            OpeningController.Reset();
        }
        return;
    }
    OpeningElapsed+=DeltaSeconds;
    const float T=FMath::Clamp(OpeningElapsed/FMath::Max(.1f,OpeningDuration),0.f,1.f);
    const float Ease=T*T*(3.f-2.f*T);
    if(OpeningMotion==EColdSteelContainerMotion::Drawer||OpeningMotion==EColdSteelContainerMotion::OpenShelf)
        DoorHinge->SetRelativeLocation(ClosedMovingPartLocation+DrawerTravel*Ease);
    else
    {
        FRotator Rotation=ClosedDoorRotation;
        if(OpeningMotion==EColdSteelContainerMotion::Lid)Rotation.Roll+=OpenedRoll*Ease;
        else Rotation.Yaw+=OpenedYaw*Ease;
        DoorHinge->SetRelativeRotation(Rotation);
    }
    if(T>=1.f)
    {
        bOpening=false;
        SetActorTickEnabled(false);
        OpenLootPanel(OpeningController.Get());
        OpeningController.Reset();
    }
}

void AColdSteelSceneContainer::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    OpeningController.Reset();
    SetActorTickEnabled(false);
    Super::EndPlay(EndPlayReason);
}
