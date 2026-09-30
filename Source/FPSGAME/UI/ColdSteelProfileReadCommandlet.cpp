#include "ColdSteelProfileReadCommandlet.h"
#include "ColdSteelInventoryTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"

int32 UColdSteelProfileReadCommandlet::Main(const FString& Params)
{
    FString Report;int32 Failures=0;
    for(const TCHAR* S:{TEXT("_A"),TEXT("_B")})
    {
        const FString Slot=TEXT("ColdSteelPlayer")+FString(S);
        TArray<uint8> Bytes;FString StoredHash;uint8 Hash[20];
        if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0)||
           !FFileHelper::LoadFileToString(StoredHash,*(FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sha1")))))
        {++Failures;continue;}
        FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num(),Hash);
        auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
        if(StoredHash!=BytesToHex(Hash,20)||!Save){++Failures;continue;}
        const auto Before=Save->Profile;FString Reason;
        const bool ValidBefore=ColdSteelInventory::Validate(Before,Reason);
        Report+=FString::Printf(TEXT("%s generation=%lld items=%d valid_before=%d reason=%s\n"),*Slot,Before.Generation,Before.Items.Num(),ValidBefore,*Reason);
        bool Changed=false;auto After=Before;
        const bool Migrated=ColdSteelInventory::MigrateLegacyWoodFootprints(After,Changed,Reason);
        Report+=FString::Printf(TEXT("migration=%d changed=%d items_after=%d reason=%s\n"),Migrated,Changed,After.Items.Num(),*Reason);
        if(!Migrated||Before.Items.Num()!=After.Items.Num()){++Failures;continue;}
        for(int32 N=0;N<Before.Items.Num();++N)
        {
            auto Expected=Before.Items[N];const auto& Actual=After.Items[N];
            if(Expected.Definition==TEXT("wood")&&Expected.Width==1&&Expected.Height==1)
            {
                Report+=FString::Printf(TEXT("wood %s %dx%d->%dx%d place %d->%d cell %d->%d count=%lld\n"),
                    *Expected.InstanceId,Expected.Width,Expected.Height,Actual.Width,Actual.Height,Expected.Place,Actual.Place,Expected.Cell,Actual.Cell,Actual.Count);
                Expected.Width=Actual.Width;Expected.Height=Actual.Height;Expected.bRotated=Actual.bRotated;
                Expected.Place=Actual.Place;Expected.Cell=Actual.Cell;Expected.Container=Actual.Container;Expected.BackpackCell=Actual.BackpackCell;
            }
            if(!FColdSteelItem::StaticStruct()->CompareScriptStruct(&Expected,&Actual,0))++Failures;
        }
        auto Again=After;bool ChangedAgain=false;
        if(!ColdSteelInventory::MigrateLegacyWoodFootprints(Again,ChangedAgain,Reason)||ChangedAgain||
            !FColdSteelProfile::StaticStruct()->CompareScriptStruct(&After,&Again,0))++Failures;
    }
    Report+=FString::Printf(TEXT("read_only_failures=%d; no slots written\n"),Failures);
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("SaveRecovery20260924");
    FFileHelper::SaveStringToFile(Report,*(Dir/TEXT("profile-diagnosis.txt")));
    UE_LOG(LogTemp,Display,TEXT("%s"),*Report);
    return Failures?1:0;
}
