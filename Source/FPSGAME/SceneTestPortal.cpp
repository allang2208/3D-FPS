#include "SceneTestPortal.h"
#include "UI/ColdSteelWorldText.h"
#include "WorldGeneration/ForestVillageMap.h"
#include "Monsters/WildlifeSubsystem.h"
#include "Dungeons/DungeonRunSubsystem.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "Multiplayer/ColdSteelPlayerState.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Net/UnrealNetwork.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/InputComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"
#include "InputCoreTypes.h"
#include "UI/TransitLoadingSubsystem.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "UI/ColdSteelUIStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
FText PortalTravelPrompt(const FString& Label)
{
    return FText::FromString(Label + TEXT("\n[E] 进入（2 米内）"));
}

class SFinalReturnConfirmation : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFinalReturnConfirmation) {}
        SLATE_EVENT(FSimpleDelegate, OnCancel)
        SLATE_EVENT(FSimpleDelegate, OnConfirm)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args)
    {
        Cancel=Args._OnCancel;Confirm=Args._OnConfirm;
        Card=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius);
        Shade=ColdSteelUI::RoundedBrush(FLinearColor(0,0,0,.55f),0);
        Buttons=ColdSteelUI::ButtonStyle();
        ChildSlot
        [SNew(SBorder).BorderImage(&Shade).Padding(24).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .OnMouseButtonDown_Lambda([](const FGeometry&,const FPointerEvent&){return FReply::Handled();})
            [SNew(SBox).MaxDesiredWidth(520)
                [SNew(SBorder).BorderImage(&Card).Padding(24)
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Text(FText::FromString(TEXT("尚未领取奖励")))
                            .Font(ColdSteelUI::TextFont(15,true)).ColorAndOpacity(ColdSteelUI::HUDGold)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,16,0,0)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("你尚未从奖励宝箱取出物品，确定现在返回主神空间？")))
                            .AutoWrapText(true).Font(ColdSteelUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("未领取的宝箱物品不会随你带回。")))
                            .AutoWrapText(true).Font(ColdSteelUI::TextFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,24,0,0)
                        [SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight)
                            [SNew(SHorizontalBox)
                                +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,4,0)
                                [SAssignNew(CancelButton,SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center)
                                    .OnClicked_Lambda([this](){Cancel.ExecuteIfBound();return FReply::Handled();})
                                    [SNew(STextBlock).Text(FText::FromString(TEXT("继续搜刮")))
                                        .Font(ColdSteelUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextPrimary)]]
                                +SHorizontalBox::Slot().FillWidth(1).Padding(4,0,0,0)
                                [SNew(SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center)
                                    .OnClicked_Lambda([this](){Confirm.ExecuteIfBound();return FReply::Handled();})
                                    [SNew(STextBlock).Text(FText::FromString(TEXT("确认离开")))
                                        .Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::HUDGoldLight)]]]]]]]];
    }
    TSharedRef<SWidget> InitialFocus() const { return CancelButton.ToSharedRef(); }
    virtual FReply OnPreviewKeyDown(const FGeometry&,const FKeyEvent& Key) override
    {
        if(Key.GetKey()==EKeys::Escape)
        {if(!Key.IsRepeat())Cancel.ExecuteIfBound();return FReply::Handled();}
        return FReply::Unhandled();
    }
private:
    FSimpleDelegate Cancel,Confirm;
    FSlateBrush Card,Shade;
    FButtonStyle Buttons;
    TSharedPtr<SButton> CancelButton;
};
}

namespace ScenePortalMaps
{
    const TCHAR* Hub = TEXT("/Game/GameMaps/DayNight_Lighting");
    const TCHAR* Hills = ForestVillageMap::Package;
    const TCHAR* RandomizedDungeon = TEXT("/Game/GameMaps/L_Dungeon_Randomized");

    /** Return-door spacing in the hills; the hub uses its saved layout anchor. */
    constexpr float PortalSpacing = 350.f;
}

ASceneTestPortal::ASceneTestPortal()
{
    bReplicates=true;bAlwaysRelevant=true;
    PrimaryActorTick.bCanEverTick = false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    for (int32 Index = 0; Index < 3; ++Index)
    {
        UStaticMeshComponent* Frame = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Frame%d"), Index));
        Frame->SetupAttachment(RootComponent);
        Frame->SetStaticMesh(Cube.Object);
        Frame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Frame->SetRelativeLocation(Index < 2 ? FVector(0, Index == 0 ? -75 : 75, 110) : FVector(0, 0, 220));
        Frame->SetRelativeScale3D(Index < 2 ? FVector(.15, .15, 2.2) : FVector(.15, 1.65, .15));
    }
    Sign = CreateDefaultSubobject<UTextRenderComponent>(TEXT("DestinationSign"));
    ColdSteelWorldText::SetConstructorFont(*Sign);
    Sign->SetupAttachment(RootComponent);
    Sign->SetRelativeLocation(FVector(12, 0, 260));
    Sign->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    Sign->SetWorldSize(22);
    Sign->SetTextRenderColor(FColor::Cyan);
}

void ASceneTestPortal::Configure(const FString& Map, const FString& Label, const FString& Options, FColor Color)
{
    Destination = Map;
    DestinationOptions = Options;
    DestinationLabel = Label;
    Sign->SetText(PortalTravelPrompt(Label));
    Sign->SetTextRenderColor(Color);

    auto* PortalFrame=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Frame.SM_GamedevPortal_Frame"));
    auto* PortalEnergy=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Energy.SM_GamedevPortal_Energy"));
    if(PortalFrame && PortalEnergy)
    {
        TInlineComponentArray<UStaticMeshComponent*> Pieces(this);
        for(auto* Piece:Pieces)
        {
            const FName PieceName=Piece->GetFName();
            if(PieceName==TEXT("Frame0") || PieceName==TEXT("Frame1"))
            {
                const bool Solid=PieceName==TEXT("Frame0");
                Piece->SetStaticMesh(Solid?PortalFrame:PortalEnergy);
                Piece->SetRelativeTransform(FTransform::Identity);
                Piece->SetVisibility(true);
                Piece->SetCollisionProfileName(Solid?TEXT("BlockAll"):TEXT("NoCollision"));
                Piece->SetCollisionEnabled(Solid?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
                Piece->SetGenerateOverlapEvents(false);
                Piece->SetCastShadow(Solid);
            }
            else if(PieceName==TEXT("Frame2"))
            {
                Piece->SetVisibility(false);
                Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            }
        }
        Sign->SetRelativeLocation(FVector(12,0,PortalFrame->GetBounds().Origin.Z+PortalFrame->GetBounds().BoxExtent.Z+45.f));
    }
}

void ASceneTestPortal::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(ASceneTestPortal,Destination);DOREPLIFETIME(ASceneTestPortal,DestinationOptions);DOREPLIFETIME(ASceneTestPortal,DestinationLabel);}
void ASceneTestPortal::OnRep_Destination(){if(!Destination.IsEmpty())Configure(Destination,DestinationLabel,DestinationOptions);}
void ASceneTestPortal::BeginPlay()
{
    Super::BeginPlay();
    ColdSteelWorldText::RestoreInstanceDefault(*Sign);
    if (!DestinationLabel.IsEmpty()) Sign->SetText(PortalTravelPrompt(DestinationLabel));

    EnableInput(UGameplayStatics::GetPlayerController(this, 0));
    if (InputComponent)
    {
        InputComponent->BindKey(EKeys::E, IE_Pressed, this, &ASceneTestPortal::UsePortal).bConsumeInput = false;
        InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &ASceneTestPortal::CancelLoading).bConsumeInput = false;
    }
}

bool ASceneTestPortal::IsWithinInteractionRange(const APawn* Pawn) const
{
    if(!Pawn||ActorHasTag(TEXT("DungeonReward.Locked")))return false;
    if(ActorHasTag(TEXT("DungeonFinalReturn")))
    {
        const auto* Run=UDungeonRunSubsystem::Get(GetWorld());if(!Run||!Run->CanUseFinalReturn())return false;
        if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    }
    const FVector Delta=Pawn->GetActorLocation()-GetActorLocation();
    return Delta.SizeSquared2D()<=FMath::Square(200.f)&&FMath::Abs(Delta.Z)<=250.f;
}

void ASceneTestPortal::UsePortal()
{
    APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
    APawn* Pawn = PC ? PC->GetPawn() : nullptr;
    if (bTravelling || ReturnConfirmation || !Pawn || PC->bShowMouseCursor) return;
    if(const auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();PS&&PS->TeamTravelId.IsValid())return;
    if (!IsWithinInteractionRange(Pawn)) return;
    if(ActorHasTag(TEXT("DungeonFinalReturn")))
        if(const auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&!(UDungeonRoomSubsystem::Supports(GetWorld())?(PC->GetPlayerState<AColdSteelPlayerState>()&&PC->GetPlayerState<AColdSteelPlayerState>()->bClaimedFinalDungeonTreasure):Run->IsFinalTreasureLooted()))
        {ShowReturnConfirmation(PC);return;}
    BeginTravel();
}

void ASceneTestPortal::ShowReturnConfirmation(APlayerController* PC)
{
    auto* Viewport=GetGameInstance()?GetGameInstance()->GetGameViewportClient():nullptr;
    if(!PC||!PC->IsLocalController()||!Viewport||ReturnConfirmation||!FSlateApplication::IsInitialized())return;
    auto Panel=SNew(SFinalReturnConfirmation)
        .OnCancel(FSimpleDelegate::CreateWeakLambda(this,[this](){CloseReturnConfirmation();}))
        .OnConfirm(FSimpleDelegate::CreateUObject(this,&ASceneTestPortal::ConfirmReturn));
    ReturnConfirmation=Panel;ConfirmationPlayer=PC;ConfirmationPawn=PC->GetPawn();ConfirmationViewport=Viewport;
    PC->OnPossessedPawnChanged.AddUniqueDynamic(this,&ASceneTestPortal::OnConfirmationPawnChanged);
    Viewport->AddViewportWidgetContent(Panel,90000);
    PC->FlushPressedKeys();PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);
    PC->bShowMouseCursor=true;
    PC->SetInputMode(FInputModeUIOnly().SetWidgetToFocus(Panel->InitialFocus())
        .SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock));
    FSlateApplication::Get().SetAllUserFocus(Panel->InitialFocus(),EFocusCause::SetDirectly);
}

void ASceneTestPortal::CloseReturnConfirmation(bool bRestoreInput)
{
    if(!ReturnConfirmation)return;
    if(auto* Viewport=ConfirmationViewport.Get())Viewport->RemoveViewportWidgetContent(ReturnConfirmation.ToSharedRef());
    ReturnConfirmation.Reset();ConfirmationViewport.Reset();
    if(auto* PC=ConfirmationPlayer.Get())
    {
        PC->OnPossessedPawnChanged.RemoveDynamic(this,&ASceneTestPortal::OnConfirmationPawnChanged);
        PC->SetIgnoreMoveInput(false);PC->SetIgnoreLookInput(false);
        if(bRestoreInput)
        {
            PC->bShowMouseCursor=false;PC->SetInputMode(FInputModeGameOnly());
            if(FSlateApplication::IsInitialized())FSlateApplication::Get().SetAllUserFocusToGameViewport();
        }
    }
    ConfirmationPlayer.Reset();ConfirmationPawn.Reset();
}

void ASceneTestPortal::CloseLocalReturnConfirmations(APlayerController* Player)
{
    if(!Player||!Player->IsLocalController()||!Player->GetWorld())return;
    for(TActorIterator<ASceneTestPortal> It(Player->GetWorld());It;++It)
        if(It->ConfirmationPlayer.Get()==Player)It->CloseReturnConfirmation();
}

void ASceneTestPortal::OnConfirmationPawnChanged(APawn*,APawn* NewPawn)
{
    if(!ReturnConfirmation||(ConfirmationPawn.IsValid()&&NewPawn==ConfirmationPawn.Get()))return;
    const auto* Loading=GetGameInstance()?GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
    CloseReturnConfirmation(!Loading||!Loading->IsHoldingGameplayInput());
}

void ASceneTestPortal::ConfirmReturn()
{
    if(!ReturnConfirmation)return;
    const auto* PC=ConfirmationPlayer.Get();
    const bool SamePawn=PC&&ConfirmationPawn.IsValid()&&PC->GetPawn()==ConfirmationPawn.Get();
    CloseReturnConfirmation();
    if(SamePawn)BeginTravel(true);
}

void ASceneTestPortal::BeginTravel(bool bConfirmUnclaimedReward)
{
    auto* PC=UGameplayStatics::GetPlayerController(this,0);
    if(bTravelling||!PC||PC->bShowMouseCursor||!IsWithinInteractionRange(PC->GetPawn()))return;
    if(const auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();PS&&PS->TeamTravelId.IsValid())return;
    if(ActorHasTag(TEXT("DungeonFinalReturn"))&&!bConfirmUnclaimedReward)
        if(const auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&!(UDungeonRoomSubsystem::Supports(GetWorld())?(PC->GetPlayerState<AColdSteelPlayerState>()&&PC->GetPlayerState<AColdSteelPlayerState>()->bClaimedFinalDungeonTreasure):Run->IsFinalTreasureLooted()))
        {ShowReturnConfirmation(PC);return;}
    if (!FPackageName::DoesPackageExist(Destination))
    {
        if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Red, TEXT("传送目的地未设置，已取消传送。"));
        UE_LOG(LogTemp, Error, TEXT("ScenePortal: Missing destination %s"), *Destination);
        return;
    }
    if(GetNetMode()!=NM_Standalone)
    {if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())PS->RequestTeamTravel(this,bConfirmUnclaimedReward);return;}
    bTravelling = true;
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        Loading->BeginTransition(Destination,FSimpleDelegate::CreateUObject(this,&ASceneTestPortal::CancelLoading));
    if (Destination == ScenePortalMaps::Hills)
    {
        Sign->SetText(FText::FromString(TEXT("正在准备目的地…\n[Esc] 取消")));
        const FString ObjectPath=Destination+TEXT(".")+FPackageName::GetShortName(Destination);
        PreloadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(FSoftObjectPath(ObjectPath),FStreamableDelegate::CreateUObject(this,&ASceneTestPortal::FinishLoading));
        if(!PreloadHandle)FinishLoading();
        return;
    }
    if(Destination==ScenePortalMaps::RandomizedDungeon||Destination==ScenePortalMaps::Hub)
    {
        GetWorldTimerManager().SetTimer(DungeonTravelTimer,this,&ASceneTestPortal::OpenDestination,.1f,false);
        return;
    }
    OpenDestination();
}

void ASceneTestPortal::OpenDestination()
{
    if(!bTravelling)return;
    if(!UWildlifeSubsystem::FlushPendingLoot(GetWorld()))
    {
        CancelLoading();
        Sign->SetText(FText::FromString(TEXT("掉落保存失败，请重试\n[E] 进入")));
        return;
    }
    if(ActorHasTag(TEXT("DungeonFinalReturn")))
    {
        auto* Run=UDungeonRunSubsystem::Get(GetWorld());
        auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Run||!Run->CanUseFinalReturn()||!IsWithinInteractionRange(UGameplayStatics::GetPlayerPawn(this,0)))
        {CancelLoading();return;}
        Run->MarkFinalReturnUsed(this);
        if(!Model||Model->Snapshot().DungeonRun.RunId!=Run->RunId()||!Model->Snapshot().DungeonRun.bCompleted)
        {Run->CancelFinalReturn(this);CancelLoading();return;}
        // OpenLevel may fail after the completion save has already committed.
        if(GEngine&&!TravelFailureHandle.IsValid())TravelFailureHandle=GEngine->OnTravelFailure().AddWeakLambda(this,
            [this](UWorld* FailedWorld,ETravelFailure::Type,const FString&)
            {
                if(FailedWorld!=GetWorld()||!bTravelling)return;
                if(auto* FailedRun=UDungeonRunSubsystem::Get(GetWorld()))FailedRun->CancelFinalReturn(this);
                CancelLoading();
            });
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Travel %s"), *Destination);
    UGameplayStatics::OpenLevel(this, FName(*Destination), true, DestinationOptions);
}

void ASceneTestPortal::FinishLoading()
{
    if (!bTravelling) return;
    if (!PreloadHandle || !PreloadHandle->GetLoadedAsset())
    {
        CancelLoading();
        Sign->SetText(FText::FromString(DestinationLabel + TEXT("加载失败\n[E] 重试")));
        return;
    }
    OpenDestination();
}

void ASceneTestPortal::CancelLoading()
{
    if (!bTravelling) return;
    GetWorldTimerManager().ClearTimer(DungeonTravelTimer);
    if(PreloadHandle){PreloadHandle->CancelHandle();PreloadHandle.Reset();}
    bTravelling=false;
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())Loading->CancelTransition();
    Sign->SetText(PortalTravelPrompt(DestinationLabel));
}

void ASceneTestPortal::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GEngine&&TravelFailureHandle.IsValid())GEngine->OnTravelFailure().Remove(TravelFailureHandle);
    CloseReturnConfirmation(Reason==EEndPlayReason::Destroyed);
    GetWorldTimerManager().ClearTimer(DungeonTravelTimer);
    if(PreloadHandle){PreloadHandle->CancelHandle();PreloadHandle.Reset();}
    Super::EndPlay(Reason);
}

int32 ASceneTestPortal::InstallHillsLink(UWorld* World)
{
    if (!World || !World->IsGameWorld() || World->GetNetMode() == NM_Client) return 2;
    const FString Current = UGameplayStatics::GetCurrentLevelName(World, true);
    if (Current != TEXT("DayNight_Lighting") && !ForestVillageMap::HasVillage(Current)) return 2;
    APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
    if (!Pawn) return 0;
    const FName LinkTag(TEXT("ScenePortal.HillsLink"));
    for (TActorIterator<ASceneTestPortal> It(World); It; ++It)
        if (It->ActorHasTag(LinkTag)) return 1;

    const bool bHills = ForestVillageMap::HasVillage(Current);
    const bool bReturnToHub = bHills;
    const FString Map = bReturnToHub ? ScenePortalMaps::Hub : ScenePortalMaps::Hills;
    const FString Label = bReturnToHub ? TEXT("返回主神空间") : TEXT("林道村庄\n森林小径");
    const FString Options = bReturnToHub ? FString() : TEXT("HillsContinue");
    const FColor Color = bReturnToHub ? FColor::Cyan : FColor(100, 255, 145);
    FRotator Facing(0, Pawn->GetActorRotation().Yaw + 180.f, 0);
    FVector Position = Pawn->GetActorLocation() - Pawn->GetActorForwardVector() * ScenePortalMaps::PortalSpacing;
    bool bFixedHubAnchor = false;
    if (!bHills)
        for (TActorIterator<AActor> It(World); It; ++It)
            if (It->ActorHasTag(TEXT("GodSpace.HillsPortalAnchor")))
            {
                Position = It->GetActorLocation();
                Facing = It->GetActorRotation();
                bFixedHubAnchor = true;
                break;
            }
    if (!bFixedHubAnchor)
    {
        FHitResult Hit;
        FCollisionQueryParams Params;
        Params.AddIgnoredActor(Pawn);
        if (World->LineTraceSingleByChannel(Hit, Position + FVector(0, 0, 200), Position - FVector(0, 0, 1500), ECC_Pawn, Params))
            Position.Z = Hit.ImpactPoint.Z + .5f;
        else
            Position.Z -= 90.f;
    }
    FActorSpawnParameters SpawnParams;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ASceneTestPortal* Portal = World->SpawnActor<ASceneTestPortal>(Position, Facing, SpawnParams);
    if (Portal)
    {
        Portal->Tags.Add(LinkTag);
        Portal->Configure(Map, Label, Options, Color);
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Installed hills link in %s"), *Current);
    return 1;
}
