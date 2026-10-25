#include "Modules/ModuleManager.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimCurveMetadata.h"
#include "UObject/StrongObjectPtr.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/PlatformMisc.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelPickup.h"
#include "Characters/FPSPlayerBodyComponent.h"
#include "Characters/FPSModularOutfitComponent.h"

namespace BeltReview
{
const FString Belt=TEXT("ue_tactical_magazine_belt"),Pants=TEXT("ue_st6_tactical_pants");
const FString Prefix=TEXT("/Game/Characters/ModularOutfit20260924/TacticalMagazineBelt20261024/");
FString Directory,Role,PickupDetail;bool Rejoin=false,Seeded=false,TransientSafe=true,Respawned=false,ResumeEquipped=false,PhasePeerSeen=false;int32 Phase=-1,Written=-1;double PhaseAt=0,LastAction=-10,LastWrite=0;
TWeakObjectPtr<APawn> Attached;TWeakObjectPtr<UWorld> FloorWorld;
FVector PickupPosition=FVector::ZeroVector;float PickupSpeed=0;
TArray<TStrongObjectPtr<USkeleton>> CurveSkeletons;
TSharedPtr<FJsonObject> Read(const FString& File)
{FString Text;TSharedPtr<FJsonObject> Data;if(FFileHelper::LoadFileToString(Text,*File))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data);return Data;}
void Write(const FString& Name,const TSharedPtr<FJsonObject>& Data)
{FString Text;FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Directory/TEXT("results")/Name));}
void PrepareUncookedMetadata()
{
    // UE 5.8's UAnimCurveMetaData::AddCurveMetaData starts an editor transaction
    // for a new morph/material curve even in uncooked -game, where GEditor is null.
    // Populate only the test process's skeleton metadata without a transaction;
    // no animation keys, pose data, packages or production files are changed.
    FString File;FParse::Value(FCommandLine::Get(),TEXT("BeltCurveMetadata="),File);auto Data=Read(File);if(!Data)return;
    for(const auto& Pair:Data->Values)if(auto* Skeleton=LoadObject<USkeleton>(nullptr,*Pair.Key))
    {
        auto* Metadata=Skeleton->GetAssetUserData<UAnimCurveMetaData>();
        if(!Metadata){Metadata=NewObject<UAnimCurveMetaData>(Skeleton);Skeleton->AddAssetUserData(Metadata);}
        for(const auto& Value:Pair.Value->AsArray())Metadata->AddCurveMetaData(FName(*Value->AsString()),false);
        CurveSkeletons.Emplace(Skeleton);
    }
    UE_LOG(LogTemp,Display,TEXT("TACTICAL_BELT_UNCOOKED_METADATA skeletons=%d; no packages saved"),CurveSkeletons.Num());
}
struct FTarget{FName Rig;bool Worn=true,HasPants=true;};
FTarget Target(bool Host,int32 Step)
{
    FTarget T;T.Rig=Host?(Step<=3||Step>=6?FName(TEXT("kaitlin")):FName(TEXT("jason"))):(Step==4||Step==5||Step==12?FName(TEXT("kaitlin")):FName(TEXT("jason")));
    T.Worn=Host?(Step!=5&&Step!=8&&Step!=12):(Step!=3&&Step!=7&&Step!=12);T.HasPants=Host||Step!=6;return T;
}
const FColdSteelItem* Item(UColdSteelStatusModel* Model,const FString& Id)
{if(!Model)return nullptr;return Model->Items().FindByPredicate([&](const FColdSteelItem& I){return I.Definition==Id&&I.Place!=2;});}
bool Worn(UColdSteelStatusModel* Model,int32 Slot,const FString& Id)
{const auto* I=Model?Model->Equipped(Slot):nullptr;return I&&I->Definition==Id;}
UColdSteelStatusModel* Shadow(APawn* Pawn)
{
    auto* PS=Pawn?Pawn->GetPlayerState():nullptr;if(!PS)return nullptr;
    const auto* Property=FindFProperty<FObjectProperty>(PS->GetClass(),TEXT("ShadowModel"));return Property?Cast<UColdSteelStatusModel>(Property->GetObjectPropertyValue_InContainer(PS)):nullptr;
}
bool Replica(APawn* Pawn,bool Expected)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;if(!Body)return false;
    const auto* P=FindFProperty<FArrayProperty>(Body->GetClass(),TEXT("ReplicatedOutfit"));if(!P)return false;
    const auto& Slots=*P->ContainerPtrToValuePtr<TArray<FFPSBodyOutfitSlot>>(Body);int32 N=0;
    for(const auto& I:Slots)if(I.Slot==10&&I.Definition==FName(*Belt))++N;return N==(Expected?1:0);
}
void Floor(UWorld* World)
{
    if(FloorWorld==World)return;FloorWorld=World;auto* Actor=World->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Actor);Actor->AddInstanceComponent(Box);Actor->SetRootComponent(Box);Box->SetBoxExtent(FVector(2000,2000,20));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Actor->SetActorLocation(FVector(0,0,-20));Box->SetMobility(EComponentMobility::Static);
}
void Freeze(APawn* Pawn,bool Host)
{
    Pawn->SetActorLocation(FVector(0,Host?1000:0,96));
    // Keep normal movement/network ticking: ServerMove carries the owning
    // player's view rotation used by authoritative focused-pickup validation.
    if(auto* Character=Cast<ACharacter>(Pawn))Character->GetCharacterMovement()->StopMovementImmediately();
}
bool Seed(UColdSteelStatusModel* Model,APawn* Pawn)
{
    if(!Model||!Model->IsAudit())return false;
    if(!Seeded)
    {
        ResumeEquipped=Worn(Model,10,Belt);
        if(!Rejoin)
        {
            auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};Model->AdoptNetMirror(State);
            if(!Model->AddItem(Belt)||!Model->AddItem(Pants))return false;
        }
        Seeded=true;
    }
    if(Attached!=Pawn){Model->AttachPawn(reinterpret_cast<AFPSGAMECharacter*>(Pawn));Attached=Pawn;Freeze(Pawn,Role==TEXT("host"));}
    return true;
}
FString DropId(UWorld* World,int32& Count,bool& MeshOK,bool& Physical)
{
    FString Id;Count=0;MeshOK=true;Physical=true;
    for(TActorIterator<AColdSteelPickup> It(World);It;++It)
    {
        const auto* Prop=FindFProperty<FStructProperty>(It->GetClass(),TEXT("SharedItem"));if(!Prop)continue;
        const auto& Data=*Prop->ContainerPtrToValuePtr<FColdSteelItem>(*It);if(Data.Definition!=Belt)continue;
        ++Count;Id=It->ItemId;bool Found=false;TArray<UStaticMeshComponent*> Parts;It->GetComponents(Parts);
        for(auto* Part:Parts)if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetPathName().StartsWith(Prefix)){Found=true;MeshOK&=Part->GetStaticMesh()->GetPathName().Contains(TEXT("Pickups/SM_TacticalBelt"));}
        PickupPosition=It->GetActorLocation();PickupSpeed=It->Body?It->Body->GetPhysicsLinearVelocity().Size():-1;
        MeshOK&=Found;Physical&=It->Body&&It->Body->IsSimulatingPhysics()&&It->Body->GetCollisionEnabled()!=ECollisionEnabled::NoCollision&&It->GetActorLocation().Z>=-2;
    }
    return Id;
}
void Act(UWorld* World,UColdSteelStatusModel* Model,APawn* Pawn,const FTarget& T)
{
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();Body&&Body->GetBodyType()!=T.Rig&&Body->CanUseBodyType(T.Rig))Body->SetBodyType(T.Rig);
    if(const auto* I=Item(Model,Pants);I&&Worn(Model,15,Pants)!=T.HasPants)Model->MoveItem(I->InstanceId,T.HasPants?1:0,T.HasPants?15:-1);
    if(Role!=TEXT("host")&&Phase==7){if(const auto* I=Item(Model,Belt))Model->Drop(I->InstanceId);return;}
    if(Role!=TEXT("host")&&Phase==8&&!Item(Model,Belt))
    {
        int32 Count;bool Mesh,Physical;const FString Id=DropId(World,Count,Mesh,Physical);
        if(Count==1)for(TActorIterator<AColdSteelPickup> It(World);It;++It)if(It->ItemId==Id)
        {
            if(auto* PC=Cast<APlayerController>(Pawn->GetController()))
            {
                FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
                // The camera has an offset from the controller pivot. A full
                // snap changes that eye position and oscillates around a close
                // target; approach the direction while normal camera ticks run.
                const FQuat Aim=(It->GetActorLocation()-Eye).Rotation().Quaternion();
                PC->SetControlRotation(FQuat::Slerp(PC->GetControlRotation().Quaternion(),Aim,.2f).Rotator());
                if(PC->PlayerCameraManager)PC->PlayerCameraManager->UpdateCamera(0);
                PC->GetPlayerViewPoint(Eye,View);if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->ApplyInteractionView(Eye,View);
                FHitResult Hit;World->LineTraceSingleByChannel(Hit,Eye,Eye+View.Vector()*250,ECC_Visibility,FCollisionQueryParams(SCENE_QUERY_STAT(BeltReviewFocus),false,Pawn));
                const bool Focused=It->CanInteract(Pawn);const bool Requested=Model->Pickup(Id);
                PickupDetail=FString::Printf(TEXT("distance=%.2f focus=%d request=%d cursor=%d hit=%s eye=%s view=%s target=%s result=%s"),FVector::Dist(Pawn->GetActorLocation(),It->GetActorLocation()),Focused,Requested,PC->bShowMouseCursor,*GetNameSafe(Hit.GetActor()),*Eye.ToCompactString(),*View.ToCompactString(),*It->GetActorLocation().ToCompactString(),*Model->ResultMessage());
            }
            break;
        }
        return;
    }
    if(const auto* I=Item(Model,Belt);I&&Worn(Model,10,Belt)!=T.Worn)Model->MoveItem(I->InstanceId,T.Worn?1:0,T.Worn?10:-1);
}
bool Presentation(APawn* Pawn,const FTarget& T,TSharedPtr<FJsonObject>& Out)
{
    Out=MakeShared<FJsonObject>();auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    auto* Source=Body?Body->GetBodyMesh():nullptr;if(!Source||!Source->GetSkeletalMeshAsset())return false;
    const FString Rig=Body->GetBodyType()==TEXT("kaitlin")?TEXT("Kaitlin"):TEXT("Jason");
    const FString Expected=Prefix+TEXT("Wear/SK_TacticalBelt_")+Rig+TEXT(".SK_TacticalBelt_")+Rig;
    int32 WorldCount=0,OwnerCount=0;bool Binding=true,Asset=true,Native=true;
    TArray<USkeletalMeshComponent*> Parts;Pawn->GetComponents(Parts);
    for(auto* Part:Parts)if(Part->IsRegistered()&&Part->GetSkeletalMeshAsset()&&Part->GetSkeletalMeshAsset()->GetPathName().StartsWith(Prefix))
    {
        const FString Path=Part->GetSkeletalMeshAsset()->GetPathName();Native&=Path==Expected;
        if(Part->bOnlyOwnerSee)++OwnerCount;else ++WorldCount;
        Asset&=Path==Expected;Binding&=Part->LeaderPoseComponent.Get()==Source&&Part->IsVisible()&&!Part->bHiddenInGame;
    }
    TransientSafe&=Native;
    const bool Local=Pawn->IsLocallyControlled();auto* Modular=Pawn->FindComponentByClass<UFPSModularOutfitComponent>();const bool Selected=Modular&&((Modular->EquippedOutfit(10)==FName(*Belt))==T.Worn);
    Out->SetStringField(TEXT("body"),Body->GetBodyType().ToString());Out->SetNumberField(TEXT("world_meshes"),WorldCount);Out->SetNumberField(TEXT("owner_meshes"),OwnerCount);Out->SetBoolField(TEXT("asset"),Asset);Out->SetBoolField(TEXT("binding"),Binding);Out->SetBoolField(TEXT("selected"),Selected);
    return Body->GetBodyType()==T.Rig&&WorldCount==(T.Worn?1:0)&&OwnerCount==(Local&&T.Worn?1:0)&&Asset&&Binding&&Selected;
}
bool SaveRestores(UColdSteelStatusModel* Model,bool Expected)
{
    int64 Generation=-1;int32 Count=-1;
    for(const TCHAR* Suffix:{TEXT("_A"),TEXT("_B")})if(auto* Save=UGameplayStatics::LoadGameFromSlot(Model->ProfileSlot()+Suffix,0))
    {
        const auto* Prop=FindFProperty<FStructProperty>(Save->GetClass(),TEXT("Profile"));if(!Prop)continue;
        const auto& Data=*Prop->ContainerPtrToValuePtr<FColdSteelProfile>(Save);if(Data.Generation<=Generation)continue;
        Generation=Data.Generation;Count=0;for(const auto& I:Data.Items)if(I.Definition==Belt&&I.Place==1&&I.Cell==10)++Count;
    }
    return Count==(Expected?1:0);
}
void ObserveNativeRig(APawn* Pawn)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(!Body||!Body->GetBodyMesh()||!Body->GetBodyMesh()->GetSkeletalMeshAsset())return;
    const FString Wrong=Body->GetBodyType()==TEXT("kaitlin")?TEXT("Jason"):TEXT("Kaitlin");
    TArray<USkeletalMeshComponent*> Parts;Pawn->GetComponents(Parts);
    for(auto* Part:Parts)if(Part->IsRegistered()&&Part->IsVisible()&&!Part->bHiddenInGame&&Part->GetSkeletalMeshAsset())
    {const FString Path=Part->GetSkeletalMeshAsset()->GetPathName();if(Path.StartsWith(Prefix)&&Path.Contains(Wrong))TransientSafe=false;}
}
bool Tick(float)
{
    if(!GEngine)return true;UWorld* World=nullptr;
    for(const auto& Context:GEngine->GetWorldContexts())if(Context.WorldType==EWorldType::Game&&Context.World()&&Context.World()->HasBegunPlay()){World=Context.World();break;}
    if(!World||!World->GetGameInstance())return true;
    auto Control=Read(Directory/TEXT("control.json"));if(!Control)return true;
    FString Exit;Control->TryGetStringField(TEXT("exit_role"),Exit);
    if(Exit==Role||Exit==TEXT("all")){FPlatformMisc::RequestExit(false);return false;}
    const int32 Next=Control->GetIntegerField(TEXT("phase"));const double Now=FPlatformTime::Seconds();
    if(Phase!=Next){Phase=Next;PhaseAt=Now;Written=-1;LastAction=-10;PhasePeerSeen=false;}
    APlayerController* PC=nullptr;for(auto It=World->GetPlayerControllerIterator();It;++It)if(It->IsValid()&&It->Get()->IsLocalController()){PC=It->Get();break;}
    if(!PC||!PC->GetPawn())return true;APawn* Pawn=PC->GetPawn();auto* Model=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Floor(World);
    if(!Seed(Model,Pawn))return true;
    APawn* Other=nullptr;for(TActorIterator<APawn> It(World);It;++It)if(*It!=Pawn&&It->GetPlayerState()&&It->FindComponentByClass<UFPSPlayerBodyComponent>()){Other=*It;break;}
    // Uncooked process startup can spend most of a minute loading content.
    // Start the synchronization deadline when the peer has actually joined;
    // the runner still bounds the entire phase, including startup, to 240 s.
    const bool NeedsPeer=Phase>0&&Phase!=10;
    if(NeedsPeer&&Other&&!PhasePeerSeen){PhasePeerSeen=true;PhaseAt=Now;}
    ObserveNativeRig(Pawn);ObserveNativeRig(Other);
    if(Role==TEXT("host")&&Phase==8&&Other)for(TActorIterator<AColdSteelPickup> It(World);It;++It)
    {
        if(auto* RemotePC=Cast<APlayerController>(Other->GetController()))
        {
            FVector Eye;FRotator View;RemotePC->GetPlayerViewPoint(Eye,View);
            PickupDetail=FString::Printf(TEXT("authority distance=%.2f focus=%d eye=%s view=%s target=%s"),FVector::Dist(Other->GetActorLocation(),It->GetActorLocation()),It->CanInteract(Other),*Eye.ToCompactString(),*View.ToCompactString(),*It->GetActorLocation().ToCompactString());
        }
    }
    if(Role==TEXT("host")&&Phase==9&&!Respawned&&Other)
    {auto* Controller=Cast<APlayerController>(Other->GetController());if(Controller){Controller->UnPossess();Other->Destroy();World->GetAuthGameMode()->RestartPlayer(Controller);Respawned=true;}return true;}
    if(Now-LastAction>.7){Act(World,Model,Pawn,Target(Role==TEXT("host"),Phase));LastAction=Now;}
    if(Now-PhaseAt<3||Written==Phase||Now-LastWrite<.5)return true;LastWrite=Now;
    auto Result=MakeShared<FJsonObject>();TSharedPtr<FJsonObject> Local,Remote;
    bool OK=Presentation(Pawn,Target(Role==TEXT("host"),Phase),Local);Result->SetObjectField(TEXT("local"),Local);
    if(Phase>0&&Phase!=10)
    {
        const auto RemoteTarget=Target(Role!=TEXT("host"),Phase);const bool Visible=Presentation(Other,RemoteTarget,Remote);Result->SetObjectField(TEXT("remote"),Remote);OK&=Visible&&Replica(Other,RemoteTarget.Worn);
        if(Role==TEXT("host")){auto* RemoteModel=Shadow(Other);const bool Authority=RemoteModel&&Worn(RemoteModel,10,Belt)==RemoteTarget.Worn;Result->SetBoolField(TEXT("authority_inventory"),Authority);OK&=Authority;}
    }
    else if(Phase==10)OK&=Other==nullptr;
    const bool Inventory=Worn(Model,10,Belt)==Target(Role==TEXT("host"),Phase).Worn;OK&=Inventory;
    const bool Persist=SaveRestores(Model,Target(Role==TEXT("host"),Phase).Worn);OK&=Persist;
    int32 Count;bool Mesh,Physical;DropId(World,Count,Mesh,Physical);if(Phase==7)OK&=Count==1&&Mesh&&Physical&&PickupSpeed<5;else if(Phase>=8)OK&=Count==0;
    const bool Catalog=Model->ItemCatalog().ContainsByPredicate([](const FColdSteelCatalogEntry& Row){return Row.Definition==Belt&&Row.Group==TEXT("装备")&&Row.Subgroup==TEXT("腰带");});OK&=Catalog&&TransientSafe&&(!Rejoin||ResumeEquipped);
    Result->SetNumberField(TEXT("phase"),Phase);Result->SetStringField(TEXT("role"),Role);Result->SetBoolField(TEXT("passed"),OK);Result->SetBoolField(TEXT("persisted"),Persist);Result->SetBoolField(TEXT("f6_catalog"),Catalog);Result->SetBoolField(TEXT("transient_native_safe"),TransientSafe);Result->SetNumberField(TEXT("pickups"),Count);Result->SetBoolField(TEXT("pickup_mesh"),Mesh);Result->SetBoolField(TEXT("pickup_physics"),Physical);Result->SetBoolField(TEXT("rejoin_loaded_equipped"),ResumeEquipped);Result->SetStringField(TEXT("pickup_detail"),PickupDetail);Result->SetNumberField(TEXT("net_mode"),World->GetNetMode());
    if(Count>0){TArray<TSharedPtr<FJsonValue>> Position;for(double V:{PickupPosition.X,PickupPosition.Y,PickupPosition.Z})Position.Add(MakeShared<FJsonValueNumber>(V));Result->SetArrayField(TEXT("pickup_position"),Position);Result->SetNumberField(TEXT("pickup_speed"),PickupSpeed);}
    if(OK||((!NeedsPeer||PhasePeerSeen)&&Now-PhaseAt>100)){Write(Role+FString::Printf(TEXT("_%02d.json"),Phase),Result);Written=Phase;UE_LOG(LogTemp,Display,TEXT("TACTICAL_BELT_WIRE phase=%d role=%s passed=%d"),Phase,*Role,OK);}
    return true;
}
}
class FTacticalBeltReviewModule : public IModuleInterface
{
    FTSTicker::FDelegateHandle Handle;FDelegateHandle PostInit;
public:
    void StartupModule() override
    {
        if(!FParse::Param(FCommandLine::Get(),TEXT("TacticalBeltAudit")))return;
        FParse::Value(FCommandLine::Get(),TEXT("BeltReviewDirectory="),BeltReview::Directory);FParse::Value(FCommandLine::Get(),TEXT("BeltReviewRole="),BeltReview::Role);
        BeltReview::Rejoin=FParse::Param(FCommandLine::Get(),TEXT("BeltReviewRejoin"));IFileManager::Get().MakeDirectory(*(BeltReview::Directory/TEXT("results")),true);
        PostInit=FCoreDelegates::OnPostEngineInit.AddStatic(&BeltReview::PrepareUncookedMetadata);
        Handle=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateStatic(&BeltReview::Tick),.25f);
    }
    void ShutdownModule() override{if(Handle.IsValid())FTSTicker::GetCoreTicker().RemoveTicker(Handle);if(PostInit.IsValid())FCoreDelegates::OnPostEngineInit.Remove(PostInit);BeltReview::CurveSkeletons.Reset();}
};
IMPLEMENT_MODULE(FTacticalBeltReviewModule,TacticalBeltReview)
