#include "BackpackWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSBodyOutfitResources.h"
#include "../Characters/FPSBackpackMotionComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace BackpackWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("BackpackWireAudit"));}
bool WantsObserver(){return FParse::Param(FCommandLine::Get(),TEXT("BackpackWireObserverCheck"));}
const int32 Slots[]={14,14,7,7};
// The second body pass begins with the same equipment IDs as the first ends.
const int32 Masks[]={5,10,4,9,6,0,9, 9,10,4,5,6,0,9};
const int32 HostMasks[]={10,5,9,6,0,10,5, 5,10,9,6,0,10,9};
FString Target(){FString V;FParse::Value(FCommandLine::Get(),TEXT("BackpackWirePack="),V);return V.IsEmpty()?TEXT("ue_pathfinder_backpack"):V;}
FString Definition(int32 I)
{
    if(I==0)return Target();if(I==1)return Target()==TEXT("ue_expedition_backpack")?TEXT("ue_portable_backpack"):TEXT("ue_expedition_backpack");
    return I==2?TEXT("ue_work_jacket"):TEXT("ue_blue_mage_robe");
}
FString Id(int32 I){return FString::Printf(TEXT("BackpackAudit_Item%d"),I);}
FName Rig(int32 Phase,bool Host){return (Phase<7)==Host?FName(TEXT("jason")):FName(TEXT("kaitlin"));}
TSharedPtr<FJsonObject> Read(const TCHAR* Name)
{
    FString Text;TSharedPtr<FJsonObject> Data;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Name));
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data);return Data;
}
TSharedPtr<FJsonObject> Config(){static auto Data=Read(TEXT("player_body.json"));return Data;}
TSharedPtr<FJsonObject> Catalog(){static auto Data=Read(TEXT("items.json"));return Data;}
TSharedPtr<FJsonObject> RigConfig(FName Body){return Body==TEXT("jason")?Config():Config()->GetObjectField(TEXT("body_variants"))->GetObjectField(Body.ToString());}
void Freeze(AFPSGAMECharacter* Pawn,bool Host)
{
    if(!Pawn)return;Pawn->SetActorLocation(FVector(0,Host?1000:0,500));
    Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->GravityScale=0.f;Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void RequestBody(AFPSGAMECharacter* Pawn,FName Desired)
{
    if(auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr)
        if(Body->GetBodyType()!=Desired&&Body->CanUseBodyType(Desired))Body->SetBodyType(Desired);
}
bool Seed(UColdSteelStatusModel* Model,AFPSGAMECharacter* Pawn)
{
    if(!Model||!Model->IsAudit()||!Pawn){UE_LOG(LogTemp,Warning,TEXT("BACKPACK_WIRE_SEED_WAIT model=%d audit=%d pawn=%d"),Model!=nullptr,Model&&Model->IsAudit(),Pawn!=nullptr);return false;}
    if(!Model->FindItem(Id(0)))
    {
        auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};
        for(int32 I=0;I<4;++I)
        {
            auto Item=Model->CreateItem(Definition(I));Item.InstanceId=Id(I);Item.Place=0;Item.Cell=INDEX_NONE;
            for(int32 Cell=0;Cell<72;++Cell)if(ColdSteelInventory::Fits(State.Items,Item,Cell)){Item.Cell=Cell;break;}
            if(Item.Cell==INDEX_NONE){UE_LOG(LogTemp,Error,TEXT("BACKPACK_WIRE_SEED_SPACE %s %dx%d"),*Item.Definition,Item.Width,Item.Height);return false;}State.Items.Add(Item);
        }
        FString Reason;if(!ColdSteelInventory::Validate(State,Reason)){UE_LOG(LogTemp,Error,TEXT("BACKPACK_WIRE_SEED_REJECTED %s"),*Reason);return false;}
        Model->AdoptNetMirror(State);
    }
    Model->AttachPawn(Pawn);Model->NotifyChanged();return true;
}
int32 InventoryMask(UColdSteelStatusModel* Model)
{
    if(!Model)return -1;int32 Mask=0;
    for(int32 I=0;I<4;++I)if(const auto* Item=Model->Equipped(Slots[I]);Item&&Item->Definition==Definition(I))Mask|=1<<I;
    int32 Rows=4;FIntPoint Grid=FIntPoint::ZeroValue;
    if(Mask&3)
    {
        const auto Item=Catalog()->GetObjectField(Definition((Mask&1)?0:1));Rows+=Item->GetIntegerField(TEXT("bagExtraCells"))/18;
        double Columns=6,Height=6;Item->TryGetNumberField(TEXT("bagCompartmentColumns"),Columns);Item->TryGetNumberField(TEXT("bagCompartmentRows"),Height);Grid=FIntPoint(int32(Columns),int32(Height));
    }
    return ColdSteelInventory::BagRows(Model->Items())==Rows&&ColdSteelInventory::CompartmentGrid(Model->Items())==Grid?Mask:-1;
}
bool Wear(UColdSteelStatusModel* Model,int32 Mask)
{
    bool OK=true;
    for(int32 I=0;I<4;++I)if(!(Mask&(1<<I)))if(const auto* Item=Model->FindItem(Id(I));Item&&Item->Place==1)OK=Model->MoveItem(Id(I),0,-1)&&OK;
    for(int32 I=0;I<4;++I)if(Mask&(1<<I))if(const auto* Item=Model->FindItem(Id(I));Item&&Item->Place!=1)OK=Model->MoveItem(Id(I),1,Slots[I])&&OK;
    return OK;
}
int32 ReplicatedMask(UFPSPlayerBodyComponent* Body)
{
    const auto* Property=FindFProperty<FArrayProperty>(UFPSPlayerBodyComponent::StaticClass(),TEXT("ReplicatedOutfit"));if(!Body||!Property)return -1;
    const auto& Values=*Property->ContainerPtrToValuePtr<TArray<FFPSBodyOutfitSlot>>(Body);int32 Mask=0;
    for(const auto& V:Values)for(int32 I=0;I<4;++I)if(V.Slot==Slots[I]&&V.Definition==FName(*Definition(I)))Mask|=1<<I;return Mask;
}
bool PackPath(const FString& Path){return Path.Contains(TEXT("Backpack"))||Path.Contains(TEXT("SimpleSling"))||Path.Contains(TEXT("simple_sling"));}
bool NativeRigSafe(AFPSGAMECharacter* Pawn)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;if(!Body||!Body->GetBodyMesh())return true;
    const FString Wrong=Body->GetBodyType()==TEXT("kaitlin")?TEXT("Jason"):TEXT("Kaitlin");
    TArray<USkeletalMeshComponent*> Parts;Pawn->GetComponents(Parts);
    for(auto* Part:Parts)if(Part->IsRegistered()&&Part->GetSkeletalMeshAsset())
    {const FString Path=Part->GetSkeletalMeshAsset()->GetPathName();if(PackPath(Path)&&Path.Contains(Wrong))return false;}
    return true;
}
FVector Vector(const TArray<TSharedPtr<FJsonValue>>& V){return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());}
bool HangingSupported(USkeletalMeshComponent* Source,USkeletalMeshComponent* Strap,const TSharedPtr<FJsonObject>& Recipe,const FTransform& Carrier,double& Slack,double& ContactGap)
{
    const auto& D=Strap->GetCustomPrimitiveData().Data;
    const auto WorldPoint=[&](const TArray<TSharedPtr<FJsonValue>>& V)
    {
        const FVector At=Carrier.TransformPosition(Vector(V)),Q=At-FVector(D[0],D[1],D[2]);
        return At+FVector(FVector::DotProduct(FVector(D[3],D[4],D[5]),Q)+D[12],FVector::DotProduct(FVector(D[6],D[7],D[8]),Q)+D[13],FVector::DotProduct(FVector(D[9],D[10],D[11]),Q)+D[14]);
    };
    Slack=DBL_MAX;ContactGap=DBL_MAX;double MaxStretch=0.;
    for(const auto& Value:Recipe->GetArrayField(TEXT("tethers")))
    {
        const auto T=Value->AsObject();FVector Anchor=FVector::ZeroVector;double Weight=0.;
        for(const auto& Influence:T->GetArrayField(TEXT("support")))
        {
            const auto I=Influence->AsObject();const double W=I->GetNumberField(TEXT("weight"));
            Anchor+=Source->GetSocketTransform(FName(*I->GetStringField(TEXT("bone")))).TransformPosition(Vector(I->GetArrayField(TEXT("local"))))*W;Weight+=W;
        }
        const double Gap=T->GetNumberField(TEXT("length"))-FVector::Dist(Anchor/Weight,WorldPoint(T->GetArrayField(TEXT("point"))));
        Slack=FMath::Min(Slack,Gap);MaxStretch=FMath::Max(MaxStretch,-Gap);
    }
    for(const auto& Value:Recipe->GetArrayField(TEXT("hulls")))
    {
        const auto H=Value->AsObject();const FTransform Bone=Source->GetSocketTransform(FName(*H->GetStringField(TEXT("bone"))));
        const int32 Sides=H->GetIntegerField(TEXT("side_planes"));const auto& Planes=H->GetArrayField(TEXT("planes"));
        for(const auto& Probe:Recipe->GetArrayField(TEXT("probes")))
        {
            const FVector Point=WorldPoint(Probe->AsArray());bool InSlice=true;double Side=-DBL_MAX;
            for(int32 I=0;I<Planes.Num();++I)
            {
                const auto& P=Planes[I]->AsArray();const FVector N=Bone.TransformVectorNoScale(Vector(P)/Bone.GetScale3D());
                const double Distance=(FVector::DotProduct(N,Point-Bone.GetLocation())+P[3]->AsNumber())/N.Size();
                if(I<Sides)Side=FMath::Max(Side,Distance);else if(Distance>.2+.5)InSlice=false;
            }
            if(InSlice)ContactGap=FMath::Min(ContactGap,Side-.2);
        }
    }
    // A rotating hanging pouch may rise at its centre while a strap or torso
    // supports it. Test those physical supports, not the sign of centre motion.
    return MaxStretch<.5&&(FMath::Abs(Slack)<.5||FMath::Abs(ContactGap)<.5);
}
bool Presentation(AFPSGAMECharacter* Pawn,int32 Mask,FName DesiredRig,FString& Details)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;auto* Source=Body?Body->GetBodyMesh():nullptr;
    if(!Source||!Source->GetSkeletalMeshAsset()||Body->GetBodyType()!=DesiredRig)return false;
    const bool HasPack=(Mask&3)!=0;bool Split=false;FString Expected,ExpectedRigid;FVector RigidReference=FVector::ZeroVector;TSharedPtr<FJsonObject> HangingRecipe;
    if(HasPack)
    {
        const auto O=RigConfig(DesiredRig)->GetObjectField(TEXT("outfits"))->GetObjectField(Definition((Mask&1)?0:1));
        const FName Shirt=FPSBodyOutfitResources::FittedShirt(O,FName(*(Mask&4?Definition(2):Mask&8?Definition(3):FString())));
        Expected=FPSBodyOutfitResources::StringForShirt(O,TEXT("world_mesh"),Shirt);Split=O->HasField(TEXT("rigid_pack"));
        if(O->HasField(TEXT("hanging_pack")))
        {
            HangingRecipe=O->GetObjectField(TEXT("hanging_pack"));
            if(!Shirt.IsNone())HangingRecipe=O->GetObjectField(TEXT("hanging_pack_by_shirt"))->GetObjectField(Shirt.ToString());
        }
        if(Split)
        {
            const auto R=O->GetObjectField(TEXT("rigid_pack"));ExpectedRigid=FPSBodyOutfitResources::StringForShirt(R,TEXT("mesh"),Shirt);
            const auto& V=Shirt.IsNone()?R->GetArrayField(TEXT("location")):R->GetObjectField(TEXT("location_by_shirt"))->GetArrayField(Shirt.ToString());
            RigidReference=FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
        }
    }
    int32 Skinned=0,Rigids=0;bool Binding=true,CorrectAsset=true;USkeletalMeshComponent* Strap=nullptr;UStaticMeshComponent* Rigid=nullptr;
    TArray<USkeletalMeshComponent*> Meshes;Pawn->GetComponents(Meshes);
    for(auto* Part:Meshes)if(Part!=Source&&Part->IsRegistered()&&Part->GetSkeletalMeshAsset()&&PackPath(Part->GetSkeletalMeshAsset()->GetPathName()))
    {++Skinned;Strap=Part;CorrectAsset&=Part->GetSkeletalMeshAsset()->GetPathName()==Expected;Binding&=Part->LeaderPoseComponent.Get()==Source&&Part->IsVisible()&&!Part->bHiddenInGame&&!Part->bOnlyOwnerSee;}
    TArray<UStaticMeshComponent*> Statics;Pawn->GetComponents(Statics);
    for(auto* Part:Statics)if(Part->IsRegistered()&&Part->GetStaticMesh()&&PackPath(Part->GetStaticMesh()->GetPathName()))
    {++Rigids;Rigid=Part;CorrectAsset&=Part->GetStaticMesh()->GetPathName()==ExpectedRigid;Binding&=Part->GetAttachParent()==Source&&Part->GetAttachSocketName()==TEXT("spine_03")&&Part->IsVisible()&&!Part->bHiddenInGame&&!Part->bOnlyOwnerSee;}
    auto* Motion=Pawn->FindComponentByClass<UFPSBackpackMotionComponent>();double Drop=0.,SeamError=0.,Slack=0.,ContactGap=0.;
    bool Dynamic=HasPack?Motion&&Motion->IsComponentTickEnabled()&&Strap&&Strap->GetCustomPrimitiveData().Data.Num()==30:!Motion||!Motion->IsComponentTickEnabled();
    if(HasPack&&Dynamic){Drop=-Strap->GetCustomPrimitiveData().Data[14];Dynamic&=HangingRecipe.IsValid()||Drop>.02;}
    if(Split&&Rigid&&Strap&&Strap->GetCustomPrimitiveData().Data.Num()==30)
    {
        const auto& Ref=Source->GetSkeletalMeshAsset()->GetRefSkeleton();const int32 Spine=Ref.FindBoneIndex(TEXT("spine_03"));
        FTransform Bind=Ref.GetRefBonePose()[Spine];for(int32 P=Ref.GetParentIndex(Spine);P!=INDEX_NONE;P=Ref.GetParentIndex(P))Bind=Bind*Ref.GetRefBonePose()[P];
        const FTransform Carrier=Bind.Inverse()*Source->GetBoneTransform(Spine);
        if(HangingRecipe)Dynamic&=Pawn->GetWorld()->GetGravityZ()<-100.f&&HangingSupported(Source,Strap,HangingRecipe,Carrier,Slack,ContactGap);
        const FVector At=Carrier.TransformPosition(RigidReference);const auto& D=Strap->GetCustomPrimitiveData().Data;
        const FVector Q=At-FVector(D[0],D[1],D[2]);
        const FVector Shift(FVector::DotProduct(FVector(D[3],D[4],D[5]),Q)+D[12],FVector::DotProduct(FVector(D[6],D[7],D[8]),Q)+D[13],FVector::DotProduct(FVector(D[9],D[10],D[11]),Q)+D[14]);
        SeamError=FVector::Dist(At+Shift,Rigid->GetComponentLocation());Dynamic&=SeamError<.25;
    }
    Details=FString::Printf(TEXT("rig=%s mask=%d replicas=%d skinned=%d rigid=%d asset=%d bind=%d motion=%d drop_cm=%.3f seam_cm=%.5f tether_slack_cm=%.3f contact_gap_cm=%.3f"),*DesiredRig.ToString(),Mask,ReplicatedMask(Body),Skinned,Rigids,CorrectAsset,Binding,Dynamic,Drop,SeamError,Slack,ContactGap);
    return Skinned==(HasPack?1:0)&&Rigids==(Split?1:0)&&CorrectAsset&&Binding&&Dynamic&&NativeRigSafe(Pawn);
}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role)
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("passed"),Pass);Root->SetStringField(TEXT("role"),Role);Root->SetStringField(TEXT("target_pack"),Target());Root->SetArrayField(TEXT("cases"),Rows);Root->SetBoolField(TEXT("rendered"),false);
    Root->SetStringField(TEXT("scope"),TEXT("Real UDP; normal async preload and gravity; native-body swaps, clothing/pack swaps, pawn recreation and same-profile reconnect; optional late observing client"));
    FString Json,Path;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("BackpackWireOutput="),Path)){IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);}
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_RESULT %s"),*Json);
}
}

void ABackpackWireAuditController::ClientCase_Implementation(int32 Phase,AFPSGAMECharacter* Subject)
{
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_CLIENT_DISPATCH phase=%d current=%d authority=%d subject=%d pawn=%d"),Phase,Current,HasAuthority(),Subject!=nullptr,GetPawn()!=nullptr);
    if(!BackpackWire::Enabled()||HasAuthority()||Phase==Current||Phase<0||Phase>=UE_ARRAY_COUNT(BackpackWire::Masks))return;
    auto* PlayerPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Subject||!Model)return;
    if(Current==INDEX_NONE&&FParse::Param(FCommandLine::Get(),TEXT("BackpackWireReconnect")))
        ReconnectRestored=BackpackWire::InventoryMask(Model)==BackpackWire::Masks[UE_ARRAY_COUNT(BackpackWire::Masks)-1];
    if(!BackpackWire::Seed(Model,PlayerPawn))return;
    BackpackWire::Freeze(PlayerPawn,false);Host=Subject;Current=Phase;Started=GetWorld()->GetRealTimeSeconds();LastSent=-10;
    BackpackWire::RequestBody(PlayerPawn,BackpackWire::Rig(Phase,false));MovesOK=BackpackWire::Wear(Model,BackpackWire::Masks[Phase]);
    if(Phase==4||Phase==7)MovesOK=BackpackWire::Wear(Model,0)&&BackpackWire::Wear(Model,BackpackWire::Masks[Phase])&&MovesOK;
}
void ABackpackWireAuditController::ClientObserveCase_Implementation(int32 Phase,AFPSGAMECharacter* HostPawn,AFPSGAMECharacter* GuestPawn)
{
    if(!BackpackWire::Enabled()||HasAuthority()||Phase<0||Phase>=UE_ARRAY_COUNT(BackpackWire::Masks)||!HostPawn||!GuestPawn)return;
    if(Phase==Current&&ObservedGuest==GuestPawn)return;IsObserver=true;Host=HostPawn;ObservedGuest=GuestPawn;Current=Phase;Started=GetWorld()->GetRealTimeSeconds();LastSent=-10;
    BackpackWire::Freeze(Cast<AFPSGAMECharacter>(GetPawn()),false);
}
void ABackpackWireAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!BackpackWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* PlayerPawn=Cast<AFPSGAMECharacter>(GetPawn());
    // Entry has no floor. Freeze the local carrier before any RPC containing
    // the host's actor reference arrives, otherwise it can fall out of relevancy
    // while waiting for that reference. Backpack world gravity stays enabled.
    BackpackWire::Freeze(PlayerPawn,false);
    TransientSafe&=BackpackWire::NativeRigSafe(Host)&&BackpackWire::NativeRigSafe(IsObserver?ObservedGuest.Get():PlayerPawn);
    if(Current<0)return;if(!IsObserver)BackpackWire::RequestBody(PlayerPawn,BackpackWire::Rig(Current,false));
    if(Now-Started<3||Now-LastSent<1)return;
    FString Local,Remote;const bool A=BackpackWire::Presentation(IsObserver?ObservedGuest.Get():PlayerPawn,BackpackWire::Masks[Current],BackpackWire::Rig(Current,false),Local);
    const bool B=BackpackWire::Presentation(Host,BackpackWire::HostMasks[Current],BackpackWire::Rig(Current,true),Remote);
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const bool OK=A&&B&&TransientSafe&&(IsObserver||BackpackWire::InventoryMask(Model)==BackpackWire::Masks[Current]);
    if(OK||Now-Started>60.)
    {
        const FString Details=Local+TEXT(" | host: ")+Remote+FString::Printf(TEXT(" | transient_rig_safe=%d"),TransientSafe);
        if(IsObserver)ServerObservation(Current,OK,Details);else ServerResult(Current,OK&&MovesOK&&ReconnectRestored,Details+FString::Printf(TEXT(" | reconnect_restored=%d"),ReconnectRestored));
        LastSent=Now;
        UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_CLIENT_RESULT phase=%d ok=%d moves=%d %s"),Current,OK,MovesOK,*Details);
    }
}
void ABackpackWireAuditController::ServerObservation_Implementation(int32 Phase,bool Pass,const FString& Details)
{if(BackpackWire::Enabled()&&IsObserver){ObservedPhase=Phase;ObservationPassed=Pass;ObservationDetails=Details;}}
void ABackpackWireAuditController::ServerResult_Implementation(int32 Phase,bool ClientPassed,const FString& Details)
{
    if(!BackpackWire::Enabled()||Phase!=Finished||Phase>=UE_ARRAY_COUNT(BackpackWire::Masks))return;
    auto* PlayerPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();const int32 Mask=BackpackWire::Masks[Phase];FString Remote,Observation;
    const bool Inventory=PS&&BackpackWire::InventoryMask(PS->GetShadowModel())==Mask;
    const bool Replication=PlayerPawn&&BackpackWire::ReplicatedMask(PlayerPawn->FindComponentByClass<UFPSPlayerBodyComponent>())==Mask;
    const bool Visible=BackpackWire::Presentation(PlayerPawn,Mask,BackpackWire::Rig(Phase,false),Remote);
    bool Observed=true;auto* Mode=Cast<ABackpackWireAuditGameMode>(GetWorld()->GetAuthGameMode());if(!Mode||!Mode->ObserverReady(Phase,Observed,Observation))return;
    if(ClientPassed&&(!Inventory||!Replication||!Visible))return;
    const bool Pass=ClientPassed&&Inventory&&Replication&&Visible&&Observed;auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);Row->SetBoolField(TEXT("passed"),Pass);Row->SetBoolField(TEXT("authority_inventory"),Inventory);Row->SetBoolField(TEXT("replicated_slots"),Replication);Row->SetStringField(TEXT("client"),Details);Row->SetStringField(TEXT("host_observer"),Remote);Row->SetStringField(TEXT("other_client"),Observation);Results.Add(MakeShared<FJsonValueObject>(Row));AllPassed&=Pass;++Finished;
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_CASE phase=%d pass=%d %s"),Phase,Pass,*Remote);
}
void ABackpackWireAuditController::ClientFinish_Implementation(bool Pass)
{if(BackpackWire::Enabled()){if(!IsObserver){auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Pass=Model&&Model->SaveNow()&&Pass;}BackpackWire::Save(Results,Pass,IsObserver?TEXT("observer"):TEXT("client"));ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}}
ABackpackWireAuditGameMode::ABackpackWireAuditGameMode()
{PlayerControllerClass=ABackpackWireAuditController::StaticClass();PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
FString ABackpackWireAuditGameMode::InitNewPlayer(APlayerController* Player,const FUniqueNetIdRepl& Id,const FString& Options,const FString& Portal)
{
    const FString Error=Super::InitNewPlayer(Player,Id,Options,Portal);
    if(auto* Controller=Cast<ABackpackWireAuditController>(Player))Controller->IsObserver=UGameplayStatics::HasOption(Options,TEXT("BackpackObserver"));return Error;
}
void ABackpackWireAuditGameMode::PostLogin(APlayerController* Player)
{
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_LOGIN %s local=%d"),*GetNameSafe(Player),Player->IsLocalController());
    Super::PostLogin(Player);if(!BackpackWire::Enabled()||Player->IsLocalController())return;
    auto* Controller=Cast<ABackpackWireAuditController>(Player);if(!Controller)return;
    if(Controller->IsObserver){Observer=Controller;return;}
    Guest=Controller;Joined=GetWorld()->GetRealTimeSeconds();Prepared=INDEX_NONE;
    // The first connection exercises the complete swap matrix. Reconnection
    // verifies its saved final state without reseeding or replaying that matrix.
    if(Connections==1)Guest->Finished=UE_ARRAY_COUNT(BackpackWire::Masks)-1;
    if(Observer)Observer->ObservedPhase=INDEX_NONE;
}
bool ABackpackWireAuditGameMode::ObserverReady(int32 Phase,bool& Pass,FString& Details) const
{
    Pass=true;if(!BackpackWire::WantsObserver()||Phase<3)return true;
    if(!Observer||Observer->ObservedPhase!=Phase)return false;Pass=Observer->ObservationPassed;Details=Observer->ObservationDetails;return true;
}
void ABackpackWireAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!BackpackWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Host)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)if(It->IsValid()&&It->Get()->IsLocalController())Host=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Model)return;
    if(!HostSeeded){if(!BackpackWire::Seed(Model,Host))return;BackpackWire::Freeze(Host,true);HostSeeded=true;UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_HOST_READY"));}
    if(!Guest)return;Passed&=BackpackWire::NativeRigSafe(Host)&&BackpackWire::NativeRigSafe(Cast<AFPSGAMECharacter>(Guest->GetPawn()));
    if(Guest->Finished>=UE_ARRAY_COUNT(BackpackWire::Masks)||Now-Joined>600.)
    {
        Passed&=Guest->AllPassed&&Guest->Finished==UE_ARRAY_COUNT(BackpackWire::Masks);History.Append(Guest->Results);Guest->ClientFinish(Passed);++Connections;
        if(Connections==1){Guest=nullptr;Prepared=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_REJOIN_READY"));return;}
        if(Observer)Observer->ClientFinish(Passed);BackpackWire::Save(History,Passed,TEXT("listen_host"));ExitAt=Now+3.;return;
    }
    BackpackWire::RequestBody(Host,BackpackWire::Rig(Guest->Finished,true));
    if(Prepared!=Guest->Finished)
    {
        if(Guest->Finished==3||Guest->Finished==10)
        {
            APawn* Previous=Guest->GetPawn();Guest->UnPossess();if(Previous)Previous->Destroy();RestartPlayer(Guest);
            UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_RESPAWN connection=%d"),Connections);
        }
        Prepared=Guest->Finished;Passed=BackpackWire::Wear(Model,BackpackWire::HostMasks[Prepared])&&Passed;
        UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_PHASE phase=%d host_mask=%d"),Prepared,BackpackWire::HostMasks[Prepared]);
        if(Prepared==4||Prepared==7)Passed=BackpackWire::Wear(Model,0)&&BackpackWire::Wear(Model,BackpackWire::HostMasks[Prepared])&&Passed;
        if(Prepared==3&&Connections==0)UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_OBSERVER_READY"));LastSetup=-10;
    }
    if(auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn()))BackpackWire::Freeze(Pawn,false);
    if(Now-LastSetup>2)
    {LastSetup=Now;Guest->ClientCase(Prepared,Host);if(Observer)Observer->ClientObserveCase(Prepared,Host,Cast<AFPSGAMECharacter>(Guest->GetPawn()));}
}
