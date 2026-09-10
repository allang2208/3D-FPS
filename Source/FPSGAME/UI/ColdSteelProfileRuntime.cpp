#include "ColdSteelStatusModel.h"
#include "ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "../Weapons/GunsmithSystem.h"
#include "Misc/SecureHash.h"

using namespace ColdSteelInventory;
namespace
{
bool IsRetiredWeapon(const FString& Id)
{
    static const TSet<FString> Retired = {TEXT("fps_akm"),TEXT("fps_hk416"),TEXT("fps_m16"),TEXT("fps_akm_classic"),TEXT("fps_qbz191"),TEXT("fps_p9")};
    return Retired.Contains(Id);
}
bool RemoveRetiredWeapons(FColdSteelProfile& P)
{
    TSet<FString> Removed;
    for (const auto& I : P.Items) if (IsRetiredWeapon(I.Definition)) Removed.Add(I.InstanceId);
    bool Changed = P.Items.RemoveAll([](const auto& I){ return IsRetiredWeapon(I.Definition); }) > 0;
    Changed |= P.ArmoryReceived.RemoveAll([](const FString& Id){ return IsRetiredWeapon(Id); }) > 0;
    for (int32 N=0; N<P.Hotbar.Num(); ++N) {
        if (Removed.Contains(P.Hotbar[N]) || (P.HotbarDefinitions.IsValidIndex(N) && IsRetiredWeapon(P.HotbarDefinitions[N]))) {
            P.Hotbar[N].Reset(); if (P.HotbarDefinitions.IsValidIndex(N)) P.HotbarDefinitions[N].Reset(); Changed=true;
        }
    }
    if (Owner(P.Items,1,P.ActiveWeaponSlot)<0) {
        const int32 Other=P.ActiveWeaponSlot==6?9:6;
        if (Owner(P.Items,1,Other)>=0) { P.ActiveWeaponSlot=Other; Changed=true; }
    }
    return Changed;
}
FString ChecksumPath(const FString& Slot){return FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sha1"));}
FString HashBytes(const TArray<uint8>& Data){uint8 Hash[20];FSHA1::HashBuffer(Data.GetData(),Data.Num(),Hash);return BytesToHex(Hash,20);}
UColdSteelProfileSave* ReadCheckedProfile(const FString& Slot)
{
    TArray<uint8> Bytes;FString Hash;
    if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0)||Bytes.Num()<32||Bytes.Num()>32*1024*1024||!FFileHelper::LoadFileToString(Hash,*ChecksumPath(Slot))||Hash!=HashBytes(Bytes))return nullptr;
    return Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
}
}
void UColdSteelStatusModel::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    FString Json; TSharedPtr<FJsonObject> Root;
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root))
        for(const auto& Pair:Root->Values){FString Data;FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));Definitions.Add(FString(*Pair.Key),Data);}
    SaveSlot=TEXT("ColdSteelPlayer"); FString Requested;
    bAudit=FString(FCommandLine::Get()).Contains(TEXT("Audit"));
    if(FParse::Value(FCommandLine::Get(),TEXT("ColdSteelProfile="),Requested)) {
        if(!Requested.IsEmpty()&&Requested.Len()<64&&!Requested.Contains(TEXT("/"))&&!Requested.Contains(TEXT("\\"))&&!Requested.Contains(TEXT("..")))SaveSlot=TEXT("ColdSteel_")+Requested;
        else bPersistenceBlocked=true;
    } else if(bAudit)SaveSlot=TEXT("ColdSteel_AuditSession");
    for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})Current.Attributes.Add(Key,10);
    Current.Hotbar.SetNum(4);Current.HotbarDefinitions.SetNum(4);Publish(Current);
    const bool Exists=UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_A"),0)||UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_B"),0);
    if(Exists){if(ReloadProfile())GrantStartingArmory();return;}
    auto Seed=Snapshot();auto Weapon=CreateItem(TEXT("ue_m4a1"));Weapon.Place=1;Weapon.Cell=6;Seed.Items.Add(Weapon);
    for(const auto& Pair:TArray<TPair<FString,int64>>{{TEXT("hp_potion"),5},{TEXT("mp_potion"),3},{TEXT("gold"),200},{TEXT("ammo_556"),90},{TEXT("ammo_762"),90}}) {
        auto I=CreateItem(Pair.Key,Pair.Value); if(!I.Data.IsEmpty())Insert(Seed.Items,I);
    }
    for(int32 Index=0;Index<2;++Index){const FString Def=Index==0?TEXT("hp_potion"):TEXT("mp_potion");for(const auto& I:Seed.Items)if(I.Definition==Def){Seed.Hotbar[Index]=I.InstanceId;Seed.HotbarDefinitions[Index]=Def;break;}}
    if(CommitState(Seed))GrantStartingArmory();
}
void UColdSteelStatusModel::Deinitialize(){SaveNow();Super::Deinitialize();}
FColdSteelProfile UColdSteelStatusModel::Snapshot() const {auto P=Current;P.Name=CharacterName;P.Class=CharacterClass;P.Level=Level;P.Points=AttributePoints;P.Attributes=Attributes;return P;}
void UColdSteelStatusModel::Publish(const FColdSteelProfile& P){Current=P;CharacterName=P.Name;CharacterClass=P.Class;Level=P.Level;AttributePoints=P.Points;Attributes=P.Attributes;}
bool UColdSteelStatusModel::CommitState(FColdSteelProfile State)
{
    if(bPersistenceBlocked||(GetWorld()&&GetWorld()->GetNetMode()!=NM_Standalone)){Message=TEXT("当前玩家数据不可写入");return false;}
    RemoveRetiredWeapons(State);
    FString Reason;if(!Validate(State,Reason)){Message=Reason;return false;}
    if(bAudit&&AuditFailNextSave){AuditFailNextSave=false;Message=TEXT("验收注入：保存失败，操作未提交");return false;}
    State.Version=2;
    State.Generation=Current.Generation+1;
    auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));Save->Profile=State;
    const FString Slot=SaveSlot+(State.Generation%2?TEXT("_A"):TEXT("_B"));
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0)){Message=TEXT("保存失败，操作未提交");return false;}
    TArray<uint8> Written;
    if(!UGameplayStatics::LoadDataFromSlot(Written,Slot,0)||!FFileHelper::SaveStringToFile(HashBytes(Written),*ChecksumPath(Slot))){Message=TEXT("完整性记录写入失败，操作未提交");return false;}
    auto* Verify=ReadCheckedProfile(Slot);
    if(!Verify||Verify->Profile.Generation!=State.Generation||!Validate(Verify->Profile,Reason)){Message=TEXT("存档写入校验失败，操作未提交");return false;}
    Publish(State);Message=TEXT("已保存");ApplyToPawn();OnChanged.Broadcast();return true;
}
bool UColdSteelStatusModel::ReloadProfile()
{
    UColdSteelProfileSave* Best=nullptr;FString Reason;
    for(const TCHAR* S:{TEXT("_A"),TEXT("_B")}) {auto* Save=ReadCheckedProfile(SaveSlot+S); if(Save&&Validate(Save->Profile,Reason)&&(!Best||Save->Profile.Generation>Best->Profile.Generation))Best=Save;}
    if(!Best){bPersistenceBlocked=true;Message=TEXT("两个存档版本均不可读取，已保留原文件");return false;}
    auto Clean=Best->Profile;
    const bool Removed=RemoveRetiredWeapons(Clean);
    Publish(Clean);bPersistenceBlocked=false;
    // Commit through the checked A/B transaction; never reset the player's save.
    if(Removed&&!CommitState(Clean))return false;
    ApplyToPawn();RefreshDrops();OnChanged.Broadcast();return true;
}
bool UColdSteelStatusModel::SaveNow(){SyncRuntime();return CommitState(Snapshot());}
int64 UColdSteelStatusModel::MaxExperience()const{return(20ll+Level*20ll+int64(Level)*Level*12)*8;}
bool UColdSteelStatusModel::GainExperience(int64 Amount)
{
    if(Amount<=0||Amount>1000000000000ll)return false;SyncRuntime();auto P=Snapshot();P.Experience+=Amount;
    while(P.Level<10000){int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    return CommitState(P);
}
bool UColdSteelStatusModel::AwardKill(AActor* Victim,int64 Reward)
{
    if(!Victim||RewardedVictims.Contains(Victim)||Reward<=0||Reward>1000000000)return false;
    SyncRuntime();auto P=Snapshot();P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=Reward;
    while(P.Level<10000){int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(!CommitState(P))return false;RewardedVictims.Add(Victim);return true;
}
const FColdSteelItem* UColdSteelStatusModel::FindItem(const FString& Id)const{return Current.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id;});}
const FColdSteelItem* UColdSteelStatusModel::Equipped(int32 S)const{int32 N=Owner(Current.Items,1,S<0?Current.ActiveWeaponSlot:S);return N>=0?&Current.Items[N]:nullptr;}
bool UColdSteelStatusModel::CycleWeapon(){SyncRuntime();auto P=Snapshot();int32 Other=P.ActiveWeaponSlot==6?9:6;if(Owner(P.Items,1,Other)<0){Message=TEXT("另一组武器槽为空");return false;}P.ActiveWeaponSlot=Other;return CommitState(P);}
FColdSteelItem UColdSteelStatusModel::CreateItem(const FString& Def,int64 Count)const
{
    FColdSteelItem I;I.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);I.Definition=Def;I.Count=Count;
    if(const FString* Data=Definitions.Find(Def))I.Data=*Data;
    I.Magazine=Number(I,TEXT("gunsmith_base_mag"),30);
    I.StackMax=Number(I,TEXT("maxStack"),Number(I,TEXT("stack_max"),1));
    if(Def==TEXT("enhancement_stone")||Def==TEXT("reforge_ticket"))I.StackMax=9999;
    if(Text(I,TEXT("category"))==TEXT("gold"))I.StackMax=9007199254740991ll;
    const auto Size=Footprint(I);I.Width=Size.X;I.Height=Size.Y;
    return I;
}
FColdSteelProposal UColdSteelStatusModel::ProposeMove(const FString& Id,int32 Place,int32 Cell)const{const auto* I=FindItem(Id);if(Place==4||(I&&I->Place==4))return ProposeWarehouse(Id,Place,Cell);auto P=ColdSteelInventory::Move(Current.Items,Id,Place,Cell);P.Revision=Current.Generation;return P;}
bool UColdSteelStatusModel::CommitProposal(const FColdSteelProposal& R){if(!R.bValid){Message=R.Reason;return false;}if(R.Revision!=Current.Generation){Message=TEXT("物品已变化，请重新拖动");return false;}auto P=Snapshot();P.Items=R.Items;if(R.ActiveWeaponSlot>=0)P.ActiveWeaponSlot=R.ActiveWeaponSlot;return CommitState(P);}
bool UColdSteelStatusModel::MoveItem(const FString& Id,int32 Place,int32 Cell){SyncRuntime();return CommitProposal(ProposeMove(Id,Place,Cell));}
bool UColdSteelStatusModel::AddItem(const FString& Def,int64 Count){if(Count<=0||Count>9007199254740991ll||!Definitions.Contains(Def))return false;SyncRuntime();auto P=Snapshot();if(!Insert(P.Items,CreateItem(Def,Count))){Message=TEXT("背包空间不足");return false;}return CommitState(P);}
bool UColdSteelStatusModel::Split(const FString& Id,int64 Count)
{
    SyncRuntime();auto P=Snapshot();auto* I=P.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Id;});
    if(!I||I->Place!=0||Count<=0||Count>=I->Count||Text(*I,TEXT("category"))==TEXT("gold"))return false;
    auto Part=*I;Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);Part.Count=Count;int32 Cell=-1;
    for(int32 C=0;C<72;++C)if(Fits(P.Items,Part,C)){Cell=C;break;}if(Cell<0){Message=TEXT("没有空间拆分");return false;}
    I->Count-=Count;Part.Cell=Cell;P.Items.Add(Part);return CommitState(P);
}
bool UColdSteelStatusModel::Sort()
{
    SyncRuntime();auto P=Snapshot();TArray<FColdSteelItem> Bag;for(const auto& I:P.Items)if(I.Place==0)Bag.Add(I);P.Items.RemoveAll([](const auto& I){return I.Place==0;});
    Bag.Sort([](const auto&A,const auto&B){if(A.Width*A.Height!=B.Width*B.Height)return A.Width*A.Height>B.Width*B.Height;return Text(A,TEXT("category"))+Text(A,TEXT("name"))+A.InstanceId<Text(B,TEXT("category"))+Text(B,TEXT("name"))+B.InstanceId;});
    // Sort preserves stack instances (the source pack contract does not merge them).
    for(auto I:Bag){int32 C=-1;for(int32 N=0;N<72;++N)if(Fits(P.Items,I,N)){C=N;break;}if(C<0){Message=TEXT("无法整理，原布局保留");return false;}I.Cell=C;P.Items.Add(I);}return CommitState(P);
}
bool UColdSteelStatusModel::BindHotbar(int32 Index,const FString& Id){if(Index<0||Index>3)return false;SyncRuntime();auto P=Snapshot();const auto* I=FindItem(Id);if(!Id.IsEmpty()&&(!I||I->Place!=0||Text(*I,TEXT("category"))!=TEXT("consumable")))return false;P.Hotbar[Index]=Id;P.HotbarDefinitions[Index]=I?I->Definition:TEXT("");return CommitState(P);}
bool UColdSteelStatusModel::SwapHotbar(int32 A,int32 B){if(A<0||A>3||B<0||B>3)return false;SyncRuntime();auto P=Snapshot();P.Hotbar.Swap(A,B);P.HotbarDefinitions.Swap(A,B);return CommitState(P);}
const FColdSteelItem* UColdSteelStatusModel::ResolveHotbar(int32 Index)const{if(Index<0||Index>3)return nullptr;const auto* I=FindItem(Current.Hotbar[Index]);if(I&&I->Place==0)return I;return Current.Items.FindByPredicate([&](const auto& V){return V.Place==0&&V.Definition==Current.HotbarDefinitions[Index]&&Text(V,TEXT("category"))==TEXT("consumable");});}
bool UColdSteelStatusModel::UseHotbar(int32 Index){const auto* I=ResolveHotbar(Index);return I&&UseItem(I->InstanceId);}
bool UColdSteelStatusModel::UseItem(const FString& Id)
{
    SyncRuntime();auto P=Snapshot();int32 N=P.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});if(N<0||P.Items[N].Place!=0)return false;
    auto& I=P.Items[N];if(I.Cooldown>0){Message=TEXT("物品冷却中");return false;}
    TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O);const TSharedPtr<FJsonObject>* Effect=nullptr;
    if(!O||!O->TryGetObjectField(TEXT("useEffect"),Effect)||!CurrentPawn.IsValid()){Message=TEXT("该物品当前无法使用");return false;}
    auto Num=[&](const TCHAR* K){double V=0;(*Effect)->TryGetNumberField(K,V);return V;};
    auto* Health=CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>();if(!Health||Health->IsDead())return false;
    const float HP=Num(TEXT("hp"))+Health->MaxHealth*Num(TEXT("maxHpPercent"))*.01;
    const float MP=Num(TEXT("mp"))+Derived(TEXT("maxMp"))*Num(TEXT("maxMpPercent"))*.01;
    if((HP<=0||P.Health>=Health->MaxHealth)&&(MP<=0||P.Mana>=Derived(TEXT("maxMp")))){Message=TEXT("当前资源已满或效果不可用");return false;}
    P.Health=FMath::Clamp(P.Health+FMath::Max(0.f,HP),0.f,Health->MaxHealth);P.Mana=FMath::Clamp(P.Mana+FMath::Max(0.f,MP),0.f,Derived(TEXT("maxMp")));
    I.Cooldown=Number(I,TEXT("useCooldown"));if(--I.Count<=0)P.Items.RemoveAt(N);return CommitState(P);
}
bool UColdSteelStatusModel::DefaultAction(const FString& Id)
{
    const auto* Found=FindItem(Id);if(!Found)return false;const auto I=*Found;
    if(I.Place==4)return TransferWarehouse(Id,0);
    if(bWarehouseOpen&&(I.Place==0||I.Place==1))return TransferWarehouse(Id,4);
    if(I.Place==1)return MoveItem(Id,0,-1);
    if(Text(I,TEXT("category"))==TEXT("consumable"))return UseItem(Id);
    for(int32 S=0;S<15;++S)if(CanEquip(I,S)&&!Equipped(S)&&!Locked(Current.Items,S))return MoveItem(Id,1,S);
    for(int32 S=0;S<15;++S)if(CanEquip(I,S)&&!Locked(Current.Items,S))return MoveItem(Id,1,S);
    Message=TEXT("该物品不能穿戴或使用");return false;
}
void UColdSteelStatusModel::SyncRuntime()
{
    if(!CurrentPawn.IsValid())return;
    if(auto* H=CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>())Current.Health=H->Health;
    for(auto& I:Current.Items)if(I.Place==1&&I.Cell==Current.ActiveWeaponSlot)I.Magazine=CurrentPawn->GetMagazineAmmo();
    for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It)if(auto* I=Current.Items.FindByPredicate([&](const auto& V){return V.InstanceId==It->ItemId&&V.Place==2;})){I->Position=It->GetActorLocation();I->WorldRotation=It->GetActorRotation();}
}
void UColdSteelStatusModel::ApplyToPawn(){if(CurrentPawn.IsValid())CurrentPawn->ApplyColdSteelProfile(this);}
void UColdSteelStatusModel::AttachPawn(AFPSGAMECharacter* Pawn){CurrentPawn=Pawn;if(Current.Health<=0)Current.Health=Derived(TEXT("maxHp"));ApplyToPawn();RefreshDrops();}
void UColdSteelStatusModel::TickRuntime(float Delta,AFPSGAMECharacter* Pawn)
{
    if(Pawn!=CurrentPawn.Get())return;for(auto& I:Current.Items)I.Cooldown=FMath::Max(0.f,I.Cooldown-Delta);
    SaveAccumulator+=Delta;if(SaveAccumulator>=5){SaveAccumulator=0;SaveNow();}
}
FString UColdSteelStatusModel::AmmoDefinition()const{const auto* I=Equipped();if(I)if(const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>())if(const auto* W=G->Weapon(I->Definition))return W->Ammo;return TEXT("ammo_556");}
int32 UColdSteelStatusModel::AmmoCount()const{if(!Equipped())return 0;int64 Total=0;const FString Def=AmmoDefinition();for(const auto&I:Current.Items)if(I.Place==0&&I.Definition==Def)Total+=I.Count;return FMath::Min<int64>(Total,MAX_int32);}
int32 UColdSteelStatusModel::ConsumeAmmo(int32 Requested)
{
    if(Requested<=0||!CurrentPawn.IsValid()||!Equipped()||!CurrentPawn->HasInventoryWeapon())return 0;
    SyncRuntime();Requested=FMath::Min(Requested,CurrentPawn->GetMagazineCapacity()-CurrentPawn->GetMagazineAmmo());if(Requested<=0)return 0;
    auto P=Snapshot();int32 Left=Requested;FString Def=AmmoDefinition();
    for(auto& I:P.Items)if(I.Place==0&&I.Definition==Def){int32 N=FMath::Min<int64>(Left,I.Count);Left-=N;I.Count-=N;}
    P.Items.RemoveAll([](const auto&I){return I.Count<=0;});int32 Taken=Requested-Left;
    for(auto& I:P.Items)if(I.Place==1&&I.Cell==P.ActiveWeaponSlot)I.Magazine+=Taken;
    return Taken>0&&CommitState(P)?Taken:0;
}
bool UColdSteelStatusModel::Drop(const FString& Id)
{
    if(!CurrentPawn.IsValid())return false;SyncRuntime();auto P=Snapshot();auto* I=P.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Id;});if(!I||I->Place>1)return false;
    const FVector Origin=CurrentPawn->GetActorLocation();
    FVector Candidate=Origin+CurrentPawn->GetActorForwardVector()*120;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(InventoryGroundDrop),false,CurrentPawn.Get());
    FHitResult Obstacle,Ground;
    if(GetWorld()->SweepSingleByChannel(Obstacle,Origin,Candidate,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(45),Query))Candidate=Obstacle.Location-CurrentPawn->GetActorForwardVector()*2;
    auto FindGround=[&](FVector At){return GetWorld()->LineTraceSingleByChannel(Ground,At+FVector(0,0,40),At-FVector(0,0,500),ECC_Visibility,Query)&&Ground.ImpactNormal.Z>=.5f&&FVector::Dist(Origin,Ground.ImpactPoint)<=230;};
    if(!FindGround(Candidate)&&!FindGround(Origin)){Message=TEXT("附近没有可放置物品的地面");return false;}
    // Release above the ground; the rigid body resolves the fall and landing.
    I->Place=2;I->Map=UGameplayStatics::GetCurrentLevelName(this,true);I->Position=Ground.ImpactPoint;I->Position.Z=FMath::Max(Ground.ImpactPoint.Z+60,Origin.Z+15);
    I->WorldRotation=FRotator(5,CurrentPawn->GetActorRotation().Yaw,-65);
    const double Begin=FPlatformTime::Seconds();if(!CommitState(P))return false;const double Saved=FPlatformTime::Seconds();RefreshDrops();
    if(bAudit)UE_LOG(LogTemp,Display,TEXT("DropTiming: save %.3f ms spawn %.3f ms"),(Saved-Begin)*1000,(FPlatformTime::Seconds()-Saved)*1000);return true;
}
bool UColdSteelStatusModel::Pickup(const FString& Id)
{
    if(!CurrentPawn.IsValid())return false;
    AColdSteelPickup* Target=nullptr;for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It)if(It->ItemId==Id&&It->CanInteract(CurrentPawn.Get())){Target=*It;break;}
    if(!Target)return false;SyncRuntime();auto P=Snapshot();int32 N=P.Items.IndexOfByPredicate([&](const auto&I){return I.InstanceId==Id&&I.Place==2;});
    if(N<0||P.Items[N].Map!=UGameplayStatics::GetCurrentLevelName(this,true)||FVector::Dist(CurrentPawn->GetActorLocation(),P.Items[N].Position)>250)return false;
    auto I=P.Items[N];P.Items.RemoveAt(N);if(!Insert(P.Items,I)){Message=TEXT("背包已满，物品留在地面");return false;}if(!CommitState(P))return false;RefreshDrops();return true;
}
void UColdSteelStatusModel::RefreshDrops()
{
    if(!GetWorld()||!CurrentPawn.IsValid())return;TSet<FString> Existing;
    for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It){const auto* I=FindItem(It->ItemId);if(!I||I->Place!=2)It->Destroy();else Existing.Add(It->ItemId);}
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    for(const auto& I:Current.Items)if(I.Place==2&&I.Map==Map&&!Existing.Contains(I.InstanceId)){FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;auto* A=GetWorld()->SpawnActor<AColdSteelPickup>(I.Position,I.WorldRotation,Spawn);if(A)A->InitializeItem(I);}
}
