#include "ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"

// Explicit opt-in; every write uses an isolated Audit profile.
void RunRetiredWeaponsAudit(AFPSGAMEPlayerController* PC)
{
    auto* M=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!M||!M->IsAudit()||!M->ProfileSlot().Contains(TEXT("RetiredWeaponsAudit")))return;
    int32 Checks=0,Failures=0;
    auto Check=[&](bool Pass,const TCHAR* Label){++Checks;if(!Pass)++Failures;UE_LOG(LogTemp,Display,TEXT("RetiredWeapons: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Label);};
    const TArray<FString> Retired={TEXT("fps_akm"),TEXT("fps_hk416"),TEXT("fps_m16"),TEXT("fps_akm_classic"),TEXT("fps_qbz191"),TEXT("fps_p9")};
    auto P=M->Snapshot();P.Items.Reset();P.Hotbar.Init(TEXT(""),4);P.HotbarDefinitions.Init(TEXT(""),4);P.ArmoryReceived=Retired;
    auto M4=M->CreateItem(TEXT("ue_m4a1"));M4.Place=1;M4.Cell=9;M4.Magazine=13;P.Items.Add(M4);
    auto Potion=M->CreateItem(TEXT("hp_potion"),3);Potion.Cell=0;P.Items.Add(Potion);P.Hotbar[0]=Potion.InstanceId;P.HotbarDefinitions[0]=Potion.Definition;
    P.Points=17;P.Kills=23;P.ActiveWeaponSlot=6;
    for(int32 N=0;N<Retired.Num();++N){
        Check(M->CreateItem(Retired[N]).Data.IsEmpty()&&!M->AddItem(Retired[N],1),TEXT("retired definition cannot be created or rewarded"));
        auto I=M4;I.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);I.Definition=Retired[N];
        I.Place=N==0?1:N==1?0:N==2?2:4;I.Cell=N==0?6:N==1?5:N;
        if(I.Place==2)I.Map=TEXT("AuditMap");P.Items.Add(I);
        if(N==0){P.Hotbar[1]=I.InstanceId;P.HotbarDefinitions[1]=I.Definition;}
    }
    FString Reason;Check(ColdSteelInventory::Validate(P,Reason),TEXT("legacy inventory fixture is valid before migration"));
    Check(M->CommitState(P),TEXT("commit removes retired definitions atomically"));
    auto Verify=[&](){const auto Q=M->Snapshot();const auto* Gun=M->FindItem(M4.InstanceId);const auto* Kept=M->FindItem(Potion.InstanceId);
        return Q.Items.Num()==2&&Gun&&Gun->Data==M4.Data&&Gun->Magazine==13&&Kept&&Kept->Count==3&&Q.Points==17&&Q.Kills==23&&Q.ActiveWeaponSlot==9&&Q.Hotbar[0]==Potion.InstanceId&&Q.Hotbar[1].IsEmpty()&&Q.HotbarDefinitions[1].IsEmpty()&&Q.ArmoryReceived.IsEmpty();};
    Check(Verify(),TEXT("native gun ammo item identities hotbar and progression preserved"));
    Check(M->ReloadProfile()&&Verify(),TEXT("clean profile survives reload"));
    // Write a checksum-valid old profile to both banks, bypassing current commit filtering.
    for(const TCHAR* S:{TEXT("_A"),TEXT("_B")}){
        auto* Old=Cast<UColdSteelProfileSave>(UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
        Old->Profile=P;Old->Profile.Generation=M->Snapshot().Generation+10;
        const FString Slot=M->ProfileSlot()+S;TArray<uint8> Bytes;
        bool OK=UGameplayStatics::SaveGameToSlot(Old,Slot,0)&&UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0);
        if(OK){uint8 Hash[20];FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num(),Hash);OK=FFileHelper::SaveStringToFile(BytesToHex(Hash,20),*(FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sha1"))));}
        Check(OK,TEXT("legacy A/B fixture written with valid checksum"));
    }
    Check(M->ReloadProfile()&&Verify(),TEXT("legacy equipped backpack warehouse and dropped guns removed on load"));
    Check(M->SaveNow()&&M->ReloadProfile()&&Verify(),TEXT("repeated save and reload cannot resurrect discarded guns"));
    Check(M->GrantStartingArmory()&&Verify(),TEXT("starter armory cannot regrant discarded guns"));
    UE_LOG(LogTemp,Display,TEXT("RetiredWeapons: COMPLETE checks=%d failures=%d"),Checks,Failures);
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"checks\":%d,\"failures\":%d}"),Checks,Failures),*(FPaths::ProjectSavedDir()/TEXT("DiscardedWeapons20260909/runtime-audit.json")));
    PC->ConsoleCommand(TEXT("quit"));
}
