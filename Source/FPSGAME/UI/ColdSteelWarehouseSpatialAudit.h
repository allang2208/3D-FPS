#pragma once
#include "ColdSteelStatusModel.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/SecureHash.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

// Explicit audit profiles only. Exercise migration through the real checked A/B loader.
static void RunWarehouseSpatialChecks(UColdSteelStatusModel* M,TFunctionRef<void(bool,const TCHAR*)> Check)
{
    using namespace ColdSteelInventory;
    auto Empty=M->Snapshot();Empty.Items.Empty();Empty.Hotbar.Init(TEXT(""),4);Empty.HotbarDefinitions.Init(TEXT(""),4);Empty.WarehousePages=5;
    auto SameItems=[](const TArray<FColdSteelItem>& A,const TArray<FColdSteelItem>& B){
        if(A.Num()!=B.Num())return false;
        for(auto I:A){const auto* Found=B.FindByPredicate([&](const auto& V){return V.InstanceId==I.InstanceId;});if(!Found)return false;
            auto J=*Found;I.Cell=J.Cell=0;if(!FColdSteelItem::StaticStruct()->CompareScriptStruct(&I,&J,0))return false;}
        return true;
    };
    auto Legacy=Empty;Legacy.WarehouseLayoutVersion=0;
    for(int32 N=0;N<100;++N){auto I=M->CreateItem(TEXT("ue_m4a1"));I.Place=4;I.Cell=N;I.Magazine=N%29;I.Reserve=10+N;I.BackpackCell=N%60;Legacy.Items.Add(I);}
    FString Reason;Check(Validate(Legacy,Reason),TEXT("legacy hundred full-size weapons remain a valid old layout"));
    auto Migrated=Legacy;Check(ColdSteelWarehouse::MigrateLayout(Migrated)&&Migrated.WarehouseLayoutVersion==1&&Migrated.WarehousePages==6&&Validate(Migrated,Reason),TEXT("legacy full warehouse expands pages without clipping any footprint"));
    Check(SameItems(Legacy.Items,Migrated.Items),TEXT("migration preserves every reflected item field except spatial anchor"));
    auto Again=Migrated;Check(ColdSteelWarehouse::MigrateLayout(Again)&&FColdSteelProfile::StaticStruct()->CompareScriptStruct(&Again,&Migrated,0),TEXT("spatial migration is idempotent"));
    auto Invalid=Legacy;Invalid.Items[1].Cell=0;auto InvalidBefore=Invalid;
    Check(!ColdSteelWarehouse::MigrateLayout(Invalid)&&FColdSteelProfile::StaticStruct()->CompareScriptStruct(&Invalid,&InvalidBefore,0),TEXT("invalid legacy duplicate anchor rejected without partial migration"));
    const auto BeforeReload=M->Snapshot();Legacy.Generation=BeforeReload.Generation+100;
    auto* Save=NewObject<UColdSteelProfileSave>();Save->Profile=Legacy;bool Written=true;
    for(const TCHAR* S:{TEXT("_A"),TEXT("_B")}){
        const FString Slot=M->ProfileSlot()+S;TArray<uint8> Bytes;uint8 Hash[20];
        Written&=UGameplayStatics::SaveGameToSlot(Save,Slot,0)&&UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0);
        FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num(),Hash);
        Written&=FFileHelper::SaveStringToFile(BytesToHex(Hash,20),*(FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sha1"))));
    }
    Check(Written,TEXT("isolated legacy A/B save fixture written with real checksums"));M->AuditFailNextSave=true;
    const bool Failed=!M->ReloadProfile();const auto AfterFailed=M->Snapshot();
    Check(Failed&&FColdSteelProfile::StaticStruct()->CompareScriptStruct(&BeforeReload,&AfterFailed,0),TEXT("failed migration save keeps previous published snapshot intact"));
    Check(M->ReloadProfile()&&M->Snapshot().WarehouseLayoutVersion==1&&M->Snapshot().WarehousePages==6&&SameItems(M->Items(),Migrated.Items),TEXT("real legacy loader retries and publishes lossless spatial save"));
    const auto Reloaded=M->Snapshot();Check(M->ReloadProfile()&&M->Snapshot().Generation==Reloaded.Generation&&SameItems(M->Items(),Reloaded.Items),TEXT("migrated checked save reloads without a second conversion"));

    auto P=Empty;auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Place=4;Gun.Cell=216;Gun.Magazine=17;Gun.Reserve=143;
    auto Other=M->CreateItem(TEXT("ue_m4a1"));Other.Place=4;Other.Cell=0;Other.Magazine=9;P.Items={Gun,Other};Check(M->CommitState(P),TEXT("two-page spatial fixture"));
    Check(Owner(M->Items(),4,216+18+4)>=0&&Owner(M->Items(),4,216+5)<0,TEXT("warehouse owner resolves all occupied cells and excludes outside cells"));
    Check(M->MoveItem(Gun.InstanceId,4,0)&&M->FindItem(Gun.InstanceId)->Cell==0&&M->FindItem(Other.InstanceId)->Cell==216&&M->FindItem(Gun.InstanceId)->Magazine==17,TEXT("cross-page spatial swap preserves exact source page and ammo"));
    const auto BeforeEdge=M->Snapshot();Check(!M->MoveItem(Gun.InstanceId,4,17)&&!M->MoveItem(Gun.InstanceId,4,198)&&SameItems(BeforeEdge.Items,M->Items()),TEXT("right and bottom page edges reject crossing weapons"));
    Check(M->MoveItem(Gun.InstanceId,1,6)&&M->Equipped()&&M->Equipped()->InstanceId==Gun.InstanceId&&M->Equipped()->Magazine==17,TEXT("warehouse rifle directly equips through shared transaction"));
    Check(M->TransferWarehouse(Gun.InstanceId,4,0),TEXT("equipped rifle returns to warehouse"));
    const auto BeforeSort=M->Items();Check(M->SortWarehouse(TEXT("rarity"))&&SameItems(BeforeSort,M->Items()),TEXT("spatial sort preserves every item field and identity"));
    P=Empty;auto Stack=M->CreateItem(TEXT("hp_potion"),9);Stack.Place=4;Stack.Cell=216+20;P.Items={Stack};M->CommitState(P);
    Check(M->Split(Stack.InstanceId,4)&&M->FindItem(Stack.InstanceId)->Count==5&&M->Items().Num()==2&&M->Items()[1].Place==4&&M->Items()[1].Cell/216==1,TEXT("warehouse split creates a separate stack on the same page"));
    const auto BeforeSplit=M->Items();M->AuditFailNextSave=true;Check(!M->Split(Stack.InstanceId,2)&&SameItems(BeforeSplit,M->Items()),TEXT("split save failure preserves original counts"));
    P=Empty;auto Gold=M->CreateItem(TEXT("gold"),100);Gold.Place=4;P.Items={Gold};M->CommitState(P);Check(!M->Split(Gold.InstanceId,30),TEXT("warehouse keeps gold split restriction"));
    P=Empty;P.WarehousePages=1;for(int32 C=0;C<216;++C){auto I=M->CreateItem(TEXT("hp_potion"),9);I.Place=4;I.Cell=C;P.Items.Add(I);}M->CommitState(P);
    const auto Full=M->Items();Check(!M->Split(Full[0].InstanceId,2)&&SameItems(Full,M->Items()),TEXT("full warehouse split rejects atomically"));
    P.WarehousePages=5;M->CommitState(P);M->WarehousePage=0;Check(M->Split(Full[0].InstanceId,2)&&M->WarehousePage==1&&Owner(M->Items(),4,216)>=0,TEXT("split switches to new stack page when current page is full"));
    M->CommitState(Empty);M->WarehousePage=0;
}
