#include "GrantPlayerAKMCommandlet.h"
#include "UI/ColdSteelInventoryTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

int32 UGrantPlayerAKMCommandlet::Main(const FString& Params)
{
    using namespace ColdSteelInventory;
    FString Definition=TEXT("ue_akm"),Id=TEXT("ad015d414361499fbac31ec8d0610910");
    int32 Magazine=30,Reserve=90;
    FParse::Value(*Params,TEXT("Item="),Definition);
    FParse::Value(*Params,TEXT("GrantId="),Id);
    FParse::Value(*Params,TEXT("Magazine="),Magazine);
    FParse::Value(*Params,TEXT("Reserve="),Reserve);
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("SaveGames");
    auto Hash=[](const TArray<uint8>& Bytes){uint8 H[20];FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num(),H);return BytesToHex(H,20);};
    auto Read=[&](const FString& Slot)->UColdSteelProfileSave* {
        TArray<uint8> Bytes;FString Check,Reason;
        if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0)||!FFileHelper::LoadFileToString(Check,*(Dir/(Slot+TEXT(".sha1"))))||Check!=Hash(Bytes))return nullptr;
        auto* S=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
        return S&&Validate(S->Profile,Reason)?S:nullptr;
    };
    auto* A=Read(TEXT("ColdSteelPlayer_A"));auto* B=Read(TEXT("ColdSteelPlayer_B"));
    auto* Save=A&&(!B||A->Profile.Generation>=B->Profile.Generation)?A:B;
    if(!Save){UE_LOG(LogTemp,Error,TEXT("PLAYER_AKM_GRANT: no valid player save"));return 1;}
    // Stable instance ID makes an interrupted retry idempotent.
    if(const auto* Existing=Save->Profile.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id;})){
        UE_LOG(LogTemp,Display,TEXT("PLAYER_AKM_GRANT: VERIFIED existing instance place=%d cell=%d magazine=%d"),Existing->Place,Existing->Cell,Existing->Magazine);return 0;
    }
    FString Json;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root->HasTypedField<EJson::Object>(Definition))return 2;
    FColdSteelItem Item;Item.InstanceId=Id;Item.Definition=Definition;Item.Magazine=Magazine;Item.Reserve=Reserve;
    FJsonSerializer::Serialize(Root->GetObjectField(Definition).ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));
    auto Size=Footprint(Item);Item.Width=Size.X;Item.Height=Size.Y;
    auto Next=Save->Profile;
    if(!Insert(Next.Items,Item)){UE_LOG(LogTemp,Error,TEXT("PLAYER_ITEM_GRANT: backpack has no free %dx%d space"),Size.X,Size.Y);return 3;}
    ++Next.Generation;FString Reason;
    if(!Validate(Next,Reason)){UE_LOG(LogTemp,Error,TEXT("PLAYER_AKM_GRANT: %s"),*Reason);return 4;}
    const FString Backup=FPaths::ProjectSavedDir()/TEXT("PlayerGrantBackups")/Id;IFileManager::Get().MakeDirectory(*Backup,true);
    for(const TCHAR* S:{TEXT("ColdSteelPlayer_A"),TEXT("ColdSteelPlayer_B")})for(const TCHAR* Ext:{TEXT(".sav"),TEXT(".sha1")}){
        const FString Name=FString(S)+Ext;
        if(IFileManager::Get().FileExists(*(Dir/Name))&&!IFileManager::Get().FileExists(*(Backup/Name)))
            if(IFileManager::Get().Copy(*(Backup/Name),*(Dir/Name))!=COPY_OK)return 5;
    }
    const FString Slot=Next.Generation%2?TEXT("ColdSteelPlayer_A"):TEXT("ColdSteelPlayer_B");
    Save->Profile=Next;if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))return 6;
    TArray<uint8> Bytes;if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0)||!FFileHelper::SaveStringToFile(Hash(Bytes),*(Dir/(Slot+TEXT(".sha1")))))return 7;
    auto* Verified=Read(Slot);if(!Verified||Verified->Profile.Generation!=Next.Generation)return 8;
    const auto* Added=Verified->Profile.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(!Added||Added->Place!=0)return 9;
    UE_LOG(LogTemp,Display,TEXT("PLAYER_ITEM_GRANT: SAVED item=%s instance=%s slot=%s row=%d column=%d magazine=%d existing_items=%d"),*Definition,*Id,*Slot,Added->Cell/18+1,Added->Cell%18+1,Added->Magazine,Next.Items.Num()-1);
    return 0;
}
