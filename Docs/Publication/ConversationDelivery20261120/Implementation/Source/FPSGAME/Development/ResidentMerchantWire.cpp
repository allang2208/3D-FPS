#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "VillageNetworkAudit.h"
#include "../FPSGAMEPlayerController.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/ResidentConversation.h"
#include "../NPC/VillageBaker.h"
#include "../NPC/VillageHerbalist.h"
#include "../NPC/VillageTavernKeeper.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelShopModel.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/CapsuleComponent.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/NetDriver.h"
#include "EngineUtils.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"

namespace ResidentMerchantWire
{
const TCHAR* const Products[] = {TEXT("bread"), TEXT("roasted_sausage"), TEXT("hp_potion")};
constexpr int32 MenuSizes[] = {2, 4, 8};

UClass* SellerClass(int32 I)
{
    if (I == 0) return AVillageBaker::StaticClass();
    if (I == 1) return AVillageTavernKeeper::StaticClass();
    return AVillageHerbalist::StaticClass();
}
int64 Quantity(const UColdSteelStatusModel& Profile, const FString& Definition)
{
    int64 Total = 0;
    for (const auto& Item : Profile.Items())
        if (Item.Definition == Definition) Total += Item.Count;
    return Total;
}
FString Ledger(const UColdSteelStatusModel& M)
{
    return FString::Printf(TEXT("%s %lld %lld %lld %lld"), *M.ProfileView().NetworkProfileId.ToString(),
        M.SoulBalance(), Quantity(M, Products[0]), Quantity(M, Products[1]), Quantity(M, Products[2]));
}
struct FRun
{
    FString Folder, Role, Detail;
    int32 LocalShop = 0, Phase = 0, ServerShop = 0;
    int64 OldMoney = 0, OldCount = 0, Price = 0;
    double Deadline = FPlatformTime::Seconds() + 300.;
    double NextLog = 0.;
    bool bSpawned = false, bPositioned = false, bDisconnected = false;

    FString Key(int32 I) const { return FString::FromInt(I); }
    bool Has(const FString& Name) const { return IFileManager::Get().FileExists(*(Folder / Name)); }
    FString Read(const FString& Name) const
    {
        FString S;
        FFileHelper::LoadFileToString(S, *(Folder / Name));
        return S;
    }
    void Mark(const FString& Name, const FString& Text)
    {
        const FString Path = Folder / (Role + TEXT(".") + Name);
        FFileHelper::SaveStringToFile(Text, *(Path + TEXT(".tmp")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        IFileManager::Get().Move(*Path, *(Path + TEXT(".tmp")), true);
        UE_LOG(LogTemp, Display, TEXT("RESIDENT_WIRE %s %s %s"), *Role, *Name, *Text);
    }
    void Finish(bool OK, const FString& Why)
    {
        Mark(OK ? TEXT("done") : TEXT("failed"), Why);
        FPlatformMisc::RequestExit(false);
    }
    AActor* Find(UWorld* W, int32 I) const
    {
        for (TActorIterator<AActor> It(W, SellerClass(I)); It; ++It) return *It;
        return nullptr;
    }
    bool Server(UWorld* W, APlayerController* Local)
    {
        if (!bSpawned)
        {
            for (int32 I = 0; I < UE_ARRAY_COUNT(Products); ++I)
                if (!W->SpawnActor<AActor>(SellerClass(I), FVector(0, I * 1300., 9000.), FRotator::ZeroRotator))
                { Finish(false, TEXT("could not spawn seller")); return false; }
            bSpawned = true;
#if DO_ENABLE_NET_TEST
            if (auto* Net = W->GetNetDriver())
            {
                const auto& P = Net->PacketSimulationSettings;
                Mark(TEXT("transport"),FString::Printf(TEXT("lag=%d loss=%d"),P.PktLag,P.PktLoss));
            }
#endif
        }
        APlayerController* Guest = nullptr;
        for (auto It = W->GetPlayerControllerIterator(); It; ++It)
        {
            APlayerController* PC = It->Get();
            if (!PC) continue;
            if (!PC->GetPawn() && W->GetAuthGameMode())
                W->GetAuthGameMode()->RestartPlayerAtTransform(PC, FTransform(FVector(500,0,9100)));
            if (!PC->IsLocalController()) Guest = PC;
        }
        if (!Guest && ServerShop == UE_ARRAY_COUNT(Products) && !bDisconnected)
        {
            bDisconnected = true;
            Mark(TEXT("disconnected"), TEXT("original guest left"));
        }
        auto* PS = Guest ? Guest->GetPlayerState<AColdSteelPlayerState>() : nullptr;
        auto* RemoteModel = VillageNetAudit::Model(Guest);
        if (!Local || !Local->GetPawn() || !Guest || !Guest->GetPawn() || !PS || !PS->IsGuestInitialized() || !RemoteModel ||
            !RemoteModel->ProfileView().NetworkProfileId.IsValid()) return true;

        if (ServerShop == UE_ARRAY_COUNT(Products))
        {
            if (bDisconnected && Has(TEXT("rejoin.done")))
            {
                const FString Full = Ledger(*RemoteModel);
                Finish(Full == Read(TEXT("guest.paid2")), TEXT("rejoined server profile: ") + Full);
                return false;
            }
            return true;
        }
        if (ServerShop > 0 && (!Has(TEXT("host.left")+Key(ServerShop-1)) || !Has(TEXT("guest.left")+Key(ServerShop-1)))) return true;
        auto* Seller = Find(W,ServerShop);
        if (!Seller) return true;
        if (!bPositioned)
        {
            for (auto* PC : { Local, Guest })
            {
                auto* Capsule = PC->GetPawn()->FindComponentByClass<UCapsuleComponent>();
                if (!Capsule) return true;
                FVector Position = Seller->GetActorTransform().TransformPosition(FVector(180.,PC == Local ? -65. : 65.,0.));
                Position.Z += Capsule->GetScaledCapsuleHalfHeight();
                VillageNetAudit::Place(PC, Position, Seller->GetActorLocation() + FVector(0,0,151));
            }
            if (!ResidentConversation::CanReach(Guest->GetPawn(),Seller) || !ResidentConversation::CanReach(Local->GetPawn(),Seller)) return true;
            Mark(TEXT("at")+Key(ServerShop),TEXT("both buyers within reach"));
            bPositioned = true;
        }
        if (Has(TEXT("host.paid")+Key(ServerShop)) && Has(TEXT("guest.paid")+Key(ServerShop)))
        {
            const FString Ours = Ledger(*VillageNetAudit::Model(Local)), Theirs = Ledger(*RemoteModel);
            if (Ours != Read(TEXT("host.paid")+Key(ServerShop)) || Theirs != Read(TEXT("guest.paid")+Key(ServerShop)) ||
                VillageNetAudit::Model(Local)->ProfileView().NetworkProfileId == RemoteModel->ProfileView().NetworkProfileId)
            { Finish(false, TEXT("authority ledger mismatch: ") + Ours + TEXT(" / ") + Theirs); return false; }
            Mark(TEXT("authority")+Key(ServerShop), Ours + TEXT(" / ") + Theirs);
            for (auto* PC : {Local,Guest})
                VillageNetAudit::Place(PC,PC->GetPawn()->GetActorLocation()+FVector(650,0,0),Seller->GetActorLocation());
            ++ServerShop;
            bPositioned = false;
        }
        return true;
    }
    bool Tick(float)
    {
        if (FPlatformTime::Seconds() >= NextLog)
        {
            UE_LOG(LogTemp, Display, TEXT("RESIDENT_WIRE_WAIT %s seller=%d phase=%d authority=%d %s"),
                *Role,LocalShop,Phase,ServerShop,*Detail);
            NextLog=FPlatformTime::Seconds()+10.;
        }
        if (FPlatformTime::Seconds() > Deadline)
        {
            Finish(false,FString::Printf(TEXT("timed out seller=%d phase=%d server=%d %s"),LocalShop,Phase,ServerShop,*Detail));
            return false;
        }
        UWorld* W = nullptr;
        const ENetMode Want = Role == TEXT("host") ? NM_ListenServer : NM_Client;
        for (const auto& C : GEngine->GetWorldContexts())
            if (C.World() && C.World()->HasBegunPlay() && C.World()->GetNetMode()==Want) { W=C.World(); break; }
        if (!W) return true;
        auto* PC = W->GetFirstPlayerController();
        if (Want==NM_ListenServer && !Server(W,PC)) return false;
        if (!PC || !PC->IsLocalController()) return true;
        auto* M = W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if (!M || !M->ProfileView().NetworkProfileId.IsValid()) return true;
        if (!PC->GetPawn()) return true;
        if (Role == TEXT("host") && !Has(TEXT("host.seed")))
        {
            if (!M->GrantSouls(400)) {Finish(false,M->ResultMessage());return false;}
            Mark(TEXT("seed"),Ledger(*M));
        }
        if (Role == TEXT("rejoin"))
        {
            if (Ledger(*M)!=Read(TEXT("guest.paid2"))) return true;
            if (!Has(TEXT("rejoin.done"))) Mark(TEXT("done"),Ledger(*M));
            if (Has(TEXT("host.done"))) { FPlatformMisc::RequestExit(false);return false; }
            return true;
        }
        if (LocalShop == UE_ARRAY_COUNT(Products))
        {
            if (Role == TEXT("guest")) {Finish(true,Ledger(*M)); return false;}
            return true;
        }
        auto* D = PC->FindComponentByClass<UChapelDialogueComponent>();
        auto* PS = PC->GetPlayerState<AColdSteelPlayerState>();
        auto* Shop = W->GetGameInstance()->GetSubsystem<UColdSteelShopModel>();
        auto* Seller = Find(W, LocalShop);
        if (!D || !PS || !Shop || !Seller) return true;
        const FString Id = Products[LocalShop], K = Key(LocalShop);
        const int32 N = Role == TEXT("host") ? 2 : 1;
        Detail=FString::Printf(TEXT("wallet=%lld UI=%d pending=%d shop=%d canOpen=%d msg=%s %s"),M->SoulBalance(),D->IsOpen(),D->IsPending(),Shop->IsOpen(),D->CanStartConversation(Seller),*D->Message,*Shop->ResultMessage());
        if (Phase == 0 && Has(TEXT("host.at")+K) && D->CanStartConversation(Seller))
        {
            D->OpenMerchant(Seller); ++Phase;
        }
        else if (Phase == 1 && D->IsOpen() && !D->IsPending())
        {
            Mark(TEXT("talk")+K, Seller->GetClass()->GetName());
            D->TradeWithMerchant(); ++Phase;
        }
        else if (Phase == 2 && Shop->IsOpen())
        {
            if (Shop->Stock().Num()!=MenuSizes[LocalShop] || Shop->BuyPrice(Id)<=0 ||
                (LocalShop!=0 && Shop->BuyPrice(TEXT("bread"))>0))
            { Finish(false,TEXT("incorrect menu ")+K); return false; }
            const auto* Stock=Shop->Stock().FindByPredicate([&](const auto& Item){return Item.Definition==Id;});
            OldMoney=M->SoulBalance(); OldCount=Quantity(*M,Id); Price=Shop->BuyPrice(Id);
            if (!Stock || OldMoney>=99*Price || OldMoney<N*Price || !Shop->Buy(Stock->InstanceId,99))
            { Finish(false,TEXT("could not submit ordinary over-budget order: ")+Detail); return false; }
            ++Phase;
        }
        else if (Phase == 3 && !PS->InventoryRequestPending() && Shop->ResultMessage().Contains(TEXT("灵魂不足")))
        {
            if (M->SoulBalance()!=OldMoney || Quantity(*M,Id)!=OldCount)
            {Finish(false,TEXT("denial changed wallet or stock"));return false;}
            Mark(TEXT("denied")+K,Shop->ResultMessage());
            const auto* Stock=Shop->Stock().FindByPredicate([&](const auto& Item){return Item.Definition==Id;});
            if (!Stock || !Shop->Buy(Stock->InstanceId,N)) {Finish(false,Shop->ResultMessage());return false;}
            ++Phase;
        }
        else if (Phase == 4 && !PS->InventoryRequestPending() && Shop->ResultMessage().Contains(TEXT("购买成功")))
        {
            if (M->SoulBalance()!=OldMoney-N*Price || Quantity(*M,Id)!=OldCount+N)
            {Finish(false,TEXT("purchase changed incorrect amounts: ")+Ledger(*M));return false;}
            Mark(TEXT("paid")+K,Ledger(*M)); ++Phase;
        }
        else if (Phase == 5 && Has(TEXT("host.authority")+K) && !Shop->IsOpen())
        {
            const auto* Player = Cast<AFPSGAMEPlayerController>(PC);
            const auto* HUD = Player ? Player->GetColdSteelHUD() : nullptr;
            if (!HUD || HUD->IsInventoryOpen() || PC->bShowMouseCursor || PC->IsMoveInputIgnored() || PC->IsLookInputIgnored())
            {Finish(false,TEXT("merchant closed but inventory or input capture remained"));return false;}
            Mark(TEXT("left")+K,TEXT("range closed merchant and backpack; movement/look restored"));
            ++LocalShop; Phase=0;
        }
        return true;
    }
};

FAutoConsoleCommand Cmd(TEXT("fps.Test.ResidentMerchantWire"),TEXT("Run opt-in resident shop multiplayer checks."),
    FConsoleCommandDelegate::CreateLambda([]
    {
        auto Run=MakeShared<FRun>();
        if (!FParse::Param(FCommandLine::Get(),TEXT("ResidentMerchantWire")) ||
            !FParse::Value(FCommandLine::Get(),TEXT("MerchantEvidence="),Run->Folder) ||
            !FParse::Value(FCommandLine::Get(),TEXT("MerchantRole="),Run->Role)) return;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float Dt){return Run->Tick(Dt);}),.3f);
    }));
}
#endif
