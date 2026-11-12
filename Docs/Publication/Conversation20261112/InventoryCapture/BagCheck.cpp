#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/NetDriver.h"
#include "Engine/NetConnection.h"
#include "UnrealClient.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/ScrollBox.h"
#include "FPSGAMEPlayerController.h"
#include "Multiplayer/ColdSteelPlayerState.h"
#include "UI/ColdSteelHUDWidget.h"
#include "UI/ColdSteelInventoryWidget.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelWeaponIcons.h"
#include "Weapons/GunsmithSystem.h"

namespace {
struct FChoice { const TCHAR* Slot; const TCHAR* Part; };
constexpr FChoice HostParts[]={{TEXT("bipod"),TEXT("m249_no_bipod")}};
constexpr FChoice GuestParts[]={{TEXT("reargrip"),TEXT("phantom_reargrip")},{TEXT("bipod"),TEXT("m249_no_bipod")}};
TConstArrayView<FChoice> Choices(bool IsHost){return IsHost?MakeArrayView(HostParts):MakeArrayView(GuestParts);}
struct FGunPair { FString Profile,Modified,Control; };
bool ReadPair(const FString& Path,FGunPair& Pair){
    TArray<FString> Lines;
    if(!FFileHelper::LoadFileToStringArray(Lines,*Path)||Lines.Num()!=3)return false;
    Pair={Lines[0],Lines[1],Lines[2]};return true;
}
bool Matches(const UColdSteelStatusModel& P,UGunsmithSystem& G,const FGunPair& Pair,bool Host,bool Fitted){
    const auto* A=P.FindItem(Pair.Modified);const auto* B=P.FindItem(Pair.Control);
    if(!A||!B||A==B||A->Definition!=TEXT("ue_m249")||B->Definition!=A->Definition||
       A->Place!=0||A->Cell!=0||B->Place!=0||B->Cell!=6||!G.Installed(*B).IsEmpty())return false;
    const auto Parts=G.Installed(*A);
    if(!Fitted)return Parts.IsEmpty();
    if(Parts.Num()!=Choices(Host).Num())return false;
    for(const auto& C:Choices(Host))if(Parts.FindRef(C.Slot)!=C.Part)return false;
    return true;
}
}

class FBagCheck : public IModuleInterface {
    FString Dir,Role,Endpoint,Run;
    FGunPair Pair,Other;
    bool Host=false,Seeded=false,TravelIssued=false,Opened=false,Applied=false,Sampled=false,ShadowDone=false;
    int32 Phase=INDEX_NONE,Join=0;
    double LastLog=0,Ready=0;
    FString Pending;
    FTSTicker::FDelegateHandle Ticker;
    TWeakObjectPtr<UWorld> FloorWorld;
    FString Path(const FString& Name) const {return Dir/Name;}
    FString Label() const {return FString::Printf(TEXT("%s-%d"),*Role,Phase);}
    void Write(const FString& Name,const FString& Value) const {
        FFileHelper::SaveStringToFile(Value,*Path(Name),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    }
    bool Fail(const TCHAR* Why){
        UE_LOG(LogTemp,Error,TEXT("BAG_WIRE_FAIL %s phase=%d %s"),*Role,Phase,Why);
        Write(Role+TEXT(".error"),Why);FPlatformMisc::RequestExit(false);return false;
    }
    bool Seed(UColdSteelStatusModel& P){
        auto S=P.Snapshot();S.Items.Reset();S.ActiveProductionTool.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto A=P.CreateItem(TEXT("ue_m249")),B=P.CreateItem(TEXT("ue_m249"));
        A.Place=B.Place=0;A.Cell=0;B.Cell=6;A.Magazine=B.Magazine=10;
        S.Items.Add(A);S.Items.Add(B);
        if(!P.CommitState(S)||!P.SaveNow())return false;
        Pair={P.Snapshot().NetworkProfileId.ToString(),A.InstanceId,B.InstanceId};
        Write(Role+TEXT(".ids"),Pair.Profile+TEXT("\n")+Pair.Modified+TEXT("\n")+Pair.Control);
        return true;
    }
    bool Change(UGunsmithSystem& Guns,bool Fitted){
        if(!Guns.Begin(Pair.Modified))return false;
        for(const auto& C:Choices(Host))if(!Guns.Select(C.Slot,Fitted?C.Part:TEXT("false")))return false;
        const bool OK=Guns.Apply();Guns.Close();return OK;
    }
    AColdSteelPlayerState* Remote(UWorld* W) const{
        for(auto It=W->GetPlayerControllerIterator();It;++It){
            auto* C=It->Get();
            if(C&&!C->IsLocalController()&&C->GetNetConnection())return C->GetPlayerState<AColdSteelPlayerState>();
        }
        return nullptr;
    }
    bool Tick(float){
        const double Now=FPlatformTime::Seconds();
        if(IFileManager::Get().FileExists(*Path(Role+TEXT("-")+FString::FromInt(Join)+TEXT(".quit")))){
            UE_LOG(LogTemp,Display,TEXT("BAG_WIRE_QUIT %s join=%d"),*Role,Join);
            FPlatformMisc::RequestExit(false);return false;
        }
        auto* W=GEngine&&GEngine->GameViewport?GEngine->GameViewport->GetWorld():nullptr;
        if(!W||!W->HasBegunPlay())return true;
        auto* PC=Cast<AFPSGAMEPlayerController>(W->GetFirstPlayerController());
        if(!PC||!PC->IsLocalController()||!PC->GetPawn())return true;
        if(W->GetNetMode()!=NM_Client&&FloorWorld.Get()!=W&&(Host||(!TravelIssued&&Join==0))){
            FloorWorld=W;
            if(auto* Floor=LoadClass<AActor>(nullptr,TEXT("/Script/FPSGAME.WeaponEquipWireFloor")))
                W->SpawnActor<AActor>(Floor,FVector(0,0,-20),FRotator::ZeroRotator);
            PC->GetPawn()->SetActorLocation(FVector(0,Host?450:0,120));
        }
        auto* GI=W->GetGameInstance();auto* P=GI->GetSubsystem<UColdSteelStatusModel>();
        if(!P||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("BagWireAudit")))return Fail(TEXT("wrong test profile"));
        if(!Seeded){
            if(Join==0&&!FParse::Param(FCommandLine::Get(),TEXT("BagPreseed"))){
                if(!Host&&W->GetNetMode()!=NM_Standalone)return Fail(TEXT("initial guest seed must precede connection"));
                if(!Seed(*P))return Fail(TEXT("seed/save"));
            }else if(!ReadPair(Path(Role+TEXT(".ids")),Pair))return Fail(TEXT("missing original identities"));
            Seeded=true;
        }
        if(!Host&&Join==0&&!TravelIssued&&!FParse::Param(FCommandLine::Get(),TEXT("BagPreseed"))){
            TravelIssued=true;PC->ClientTravel(Endpoint,TRAVEL_Absolute);return true;
        }
        if(Host&&W->GetNetMode()==NM_ListenServer){
            if(!IFileManager::Get().FileExists(*Path(TEXT("listen.ready"))))Write(TEXT("listen.ready"),TEXT("listen"));
        }else if(Host||W->GetNetMode()!=NM_Client||!W->GetNetDriver()||!W->GetNetDriver()->ServerConnection)return true;
        auto* GuestPS=Host?Remote(W):nullptr;
        if(Host&&!GuestPS&&(Phase==1||Phase==3)&&ShadowDone&&Sampled){
            const FString Offline=Label()+TEXT(".offline");
            if(!IFileManager::Get().FileExists(*Path(Offline)))Write(Offline,TEXT("guest disconnected; host stayed in listen world"));
        }
        FString Command;
        if(!FFileHelper::LoadFileToString(Command,*Path(TEXT("phase.txt"))))return true;
        int32 Next=FCString::Atoi(*Command);
        if(Next<0||Next>4||(!Host&&((Join==0&&Next>1)||(Join==1&&(Next<2||Next>3))||(Join==2&&Next!=4))))return true;
        if(Phase!=Next){
            Phase=Next;Applied=Sampled=ShadowDone=false;Ready=0;Pending.Reset();
            UE_LOG(LogTemp,Display,TEXT("BAG_WIRE_PHASE %s phase=%d join=%d mode=%d"),*Role,Phase,Join,W->GetNetMode());
        }
        if(Host&&!GuestPS)return true;
        if(Other.Modified.IsEmpty()&&!ReadPair(Path(Host?TEXT("guest.ids"):TEXT("host.ids")),Other))return true;
        if(Pair.Profile==Other.Profile||Pair.Modified==Other.Modified||Pair.Control==Other.Control||Pair.Control==Pair.Modified)
            return Fail(TEXT("identities not distinct"));
        auto* Guns=GI->GetSubsystem<UGunsmithSystem>();auto* Icons=GI->GetSubsystem<UColdSteelWeaponIcons>();
        auto* HUD=PC->GetColdSteelHUD();if(!Guns||!Icons||!HUD)return true;
        if(!Opened){
            Opened=true;PC->SetMouseLocation(1,1);HUD->SetInventoryAuditState(1);HUD->HideItemTooltip(true);
            HUD->ProcessEvent(HUD->FindFunctionChecked(TEXT("HandleEquipmentTooltipCloseClicked")),nullptr);
        }
        const bool Fitted=Phase==1||Phase==2;
        if(!Applied){
            if((Phase==1||Phase==3)&&!Change(*Guns,Fitted))return Fail(TEXT("gunsmith apply"));
            if(Phase==1){
                const auto* Fresh=P->FindItem(Pair.Modified);
                if(!Fresh||Icons->Find(*Fresh))return Fail(TEXT("a fresh uncached no-bipod recipe was expected"));
                FScreenshotRequest::RequestScreenshot(Path(Role+TEXT("-immediate.png")),true,false);
            }
            Applied=true;
        }
        if(Host&&!ShadowDone&&GuestPS->ShadowModel){
            auto& Shadow=*GuestPS->ShadowModel;
            if(Matches(Shadow,*Guns,Other,false,Fitted)&&!Shadow.FindItem(Pair.Modified)&&!Shadow.FindItem(Pair.Control)&&
               Shadow.Snapshot().NetworkProfileId.ToString()==Other.Profile){
                ShadowDone=true;
                Write(Label()+TEXT(".shadow"),FString::Printf(TEXT("guest=%s control=%s profile=%s fitted=%d controller=%s"),*Other.Modified,*Other.Control,*Other.Profile,Fitted,*GetNameSafe(GuestPS)));
            }
        }
        if(Sampled)return true;
        if(Now-LastLog>14.){
            LastLog=Now;const auto Info=Icons->GetPerformanceState();
            UE_LOG(LogTemp,Display,TEXT("BAG_WIRE_WAIT %s phase=%d match=%d queued=%d failed=%d wait=%s resource=%s shadow=%d"),*Role,Phase,
                Matches(*P,*Guns,Pair,Host,Fitted),Info.Queued,Info.FailedRecipes,*Info.WaitReason.ToString(),*Info.WaitResource,ShadowDone);
        }
        if(!Matches(*P,*Guns,Pair,Host,Fitted)||!PC->IsItemIconPanelOpen())return true;
        if(P->FindItem(Other.Modified)||P->FindItem(Other.Control)||P->Snapshot().NetworkProfileId.ToString()!=Pair.Profile)
            return Fail(TEXT("owner identity mismatch"));
        auto* A=P->FindItem(Pair.Modified);auto* B=P->FindItem(Pair.Control);
        auto* BA=Icons->Find(*A);auto* BB=Icons->Find(*B);
        FString FallbackWait;
        if(Fitted&&!BA){
            const auto Info=Icons->GetPerformanceState();
            const FString Recipe=Icons->Key(*A);
            const auto* Failure=Info.RecentFailures.FindByPredicate([&](const FFPSIconFailure& Entry){return Entry.Recipe==Recipe;});
            if(!Failure||Now-Failure->Seconds<15.)return true;
            FallbackWait=Failure->Stage.ToString()+TEXT(" ")+Failure->Resource;
        }
        if(BA&&BB&&(BA->GetResourceObject()==BB->GetResourceObject())==Fitted)return Fail(TEXT("incorrect brushes for instances"));
        if(!Ready){
            TArray<UUserWidget*> Boards;UWidgetBlueprintLibrary::GetAllWidgetsOfClass(PC,Boards,UColdSteelInventoryWidget::StaticClass(),false);
            for(auto* Board:Boards)if(auto* Scroll=Cast<UScrollBox>(Board->GetParent()))Scroll->ScrollToEnd();
            Ready=Now;return true;
        }
        if(Now-Ready<2.)return true;
        if(Pending.IsEmpty()){Pending=Path(Label()+TEXT(".png"));FScreenshotRequest::RequestScreenshot(Pending,true,false);return true;}
        if(!IFileManager::Get().FileExists(*Pending))return true;
        if(Host&&Phase==1&&BA)
        {
            auto* Texture=CastChecked<UTexture2D>(BA->GetResourceObject());
            auto& Mip=Texture->GetPlatformData()->Mips[0];
            const auto* Pixels=static_cast<const FColor*>(Mip.BulkData.LockReadOnly());
            TArray64<uint8> Png;
            FImageUtils::PNGCompressImageArray(Texture->GetSizeX(),Texture->GetSizeY(),TArrayView64<const FColor>(Pixels,int64(Texture->GetSizeX())*Texture->GetSizeY()),Png);
            Mip.BulkData.Unlock();
            if(!FFileHelper::SaveArrayToFile(Png,*Path(TEXT("runtime-no-bipod.png"))))return Fail(TEXT("raw icon export failed"));
        }
        Write(Label()+TEXT(".sample"), FString::Printf(TEXT("profile=%s\ninstance=%s\ncontrol=%s\nrecipe=%s\ncontrol_recipe=%s\nmode=%s\nprocess=%u\ndynamic=%d\ncontrol_dynamic=%d\nfallback=%s\n"),
            *Pair.Profile,*Pair.Modified,*Pair.Control,*Icons->Key(*A),*Icons->Key(*B),Host?TEXT("listen"):TEXT("client"),FPlatformProcess::GetCurrentProcessId(),BA!=nullptr,BB!=nullptr,*FallbackWait));
        UE_LOG(LogTemp,Display,TEXT("BAG_WIRE_SAMPLE %s phase=%d key=%s"),*Role,Phase,*Icons->Key(*A));
        Sampled=true;return true;
    }
public:
    void StartupModule()override{
        if(!FParse::Value(FCommandLine::Get(),TEXT("BagWireDir="),Dir))return;
        FParse::Value(FCommandLine::Get(),TEXT("BagWireRole="),Role);
        FParse::Value(FCommandLine::Get(),TEXT("BagWireJoin="),Join);
        FParse::Value(FCommandLine::Get(),TEXT("BagWireURL="),Endpoint);
        Host=Role==TEXT("host");
        Ticker=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateRaw(this,&FBagCheck::Tick),.3f);
    }
    void ShutdownModule()override{FTSTicker::GetCoreTicker().RemoveTicker(Ticker);}
};
IMPLEMENT_MODULE(FBagCheck,BagCheck)
