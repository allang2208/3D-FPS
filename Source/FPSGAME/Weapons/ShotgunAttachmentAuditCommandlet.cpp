#include "ShotgunAttachmentAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/QuickCombatRifleMotion.h"
#include "WeaponGripProfile.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "GunsmithSystem.h"
#include "GunsmithModificationTier.h"
#include "ShotgunDuckbillAssets.h"
#include "ShotgunChokeAssets.h"
#include "ShotgunSuppressorAssets.h"
#include "ShotgunBirdcageAssets.h"
#include "Super90TubeMagazineAssets.h"
#include "M870TubeMagazineAssets.h"
#include "M870WeaponAssets.h"
#include "WeaponReloadStages.h"
#include "FPSWeaponFXComponent.h"
#include "WeaponPresentationMaterials.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "TimerManager.h"
#include "Misc/Parse.h"
#include "Super90Spread.h"
#include "Super90SpeedloaderAssets.h"
#include "FPSBallisticsComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace ShotgunAudit
{
void Parts(FColdSteelItem& Item,const TCHAR* Muzzle,bool Tube,bool Loader=false)
{
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("muzzle"),Item.Definition==M870WeaponAssets::Definition?TEXT("false"):Muzzle);
    if(Tube)P->SetStringField(TEXT("magazine"),Item.Definition==M870WeaponAssets::Definition?M870TubeMagazineAssets::Part:Super90TubeMagazineAssets::Part);
    if(Loader)P->SetStringField(TEXT("reload_device"),Super90SpeedloaderAssets::Id);
    Data->SetObjectField(TEXT("gunsmith_parts"),P);Data->SetNumberField(TEXT("gunsmith_version"),1);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
}
}
int32 UShotgunAttachmentAuditCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("PistolAmmo")))return RunPistolAmmoAudit(Params);
    if(FParse::Param(*Params,TEXT("AnimationHandoff")))return RunAnimationHandoffAudit(Params);
    if(FParse::Param(*Params,TEXT("PistolBody")))return RunPistolBodyReview(Params);
    if(FParse::Param(*Params,TEXT("SVCHReview")))return RunSVCHReview(Params);
    if(FParse::Param(*Params,TEXT("Saiga12KNetwork")))return RunSaiga12KNetworkAudit(Params);
    if(FParse::Param(*Params,TEXT("Saiga12KPresentation")))return RunSaiga12KPresentationAudit(Params);
    if(FParse::Param(*Params,TEXT("M870Presentation")))return RunM870PresentationAudit(Params);
    using namespace ShotgunAudit;
    const bool M870=FParse::Param(*Params,TEXT("M870"));
    const TCHAR* TubeId=M870?M870TubeMagazineAssets::Part:Super90TubeMagazineAssets::Part;
    const FString Original=FCommandLine::Get(),Slot=TEXT("ShotgunAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("ShotgunAttachmentAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Model||!G||!Model->IsAudit())return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool Pass,const FString& Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),Pass);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("SHOTGUN_AUDIT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Base=Model->Snapshot();Base.Items.Reset();Base.ActiveWeaponSlot=6;Base.ActiveProductionTool.Reset();Base.DungeonRun={};
    Base.NetworkProfileId=FGuid::NewGuid();Base.AmmoPouch.Add(TEXT("ammo_12g"),100);Base.AmmoPouch.Add(TEXT("ammo_12g_slug"),100);Base.AmmoPouch.Add(TEXT("ammo_12g_flechette"),100);
    auto Item=Model->CreateItem(M870?M870WeaponAssets::Definition:TEXT("ue_super90"));Item.Place=1;Item.Cell=6;Item.Magazine=7;Item.VirtualMagazineAmmo=0;
    Item.LoadedAmmoType=TEXT("ammo_12g");Parts(Item,TEXT("false"),false);Base.Items={Item};Model->Current=Base;
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->SetPlayerState(World->SpawnActor<AColdSteelPlayerState>());
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Pawn);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pawn->DispatchBeginPlay();Model->CurrentPawn=Pawn;
    Pawn->ApplyColdSteelProfile(Model);
    const auto Default=G->CalculateItem(Item,G->Installed(Item));
    const auto Trigger=[&](FColdSteelItem& Gun)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
        Data->GetObjectField(TEXT("gunsmith_parts"))->SetStringField(TEXT("trigger"),TEXT("m870_lightweight_trigger_kit"));
        Gun.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));
    };
    if(M870)
    {
        auto Kit=Item;Parts(Kit,TEXT("false"),true);Trigger(Kit);Kit.Magazine=10;
        const auto Stats=G->CalculateItem(Kit,G->Installed(Kit));
        Check(Stats.Capacity==10&&FMath::IsNearlyEqual(Stats.Interval,.675,1.e-6),TEXT("M870 tube and trigger compose to ten rounds / 675 ms"));
        Check(FMath::IsNearlyEqual(Stats.Recoil,Default.Recoil*.95,1.e-5)&&FMath::IsNearlyEqual(Stats.Handling.Stability,Default.Handling.Stability*1.05,1.e-5),TEXT("M870 trigger recoil -5 and stability +5 percent"));
        Check(ColdSteelModification::Tier(Item.Definition,TEXT("trigger"),TEXT("m870_lightweight_trigger_kit"))==EGunsmithModificationTier::Special&&
            ColdSteelModification::Tier(Item.Definition,TEXT("magazine"),TubeId)==EGunsmithModificationTier::Special,TEXT("both M870 modifications have special tier"));
        Check(!G->ModifiableWeapon(Item.Definition)->Allowed.Contains(TEXT("reargrip")),TEXT("retired M870 reargrip is not exposed"));
        Model->Current=Base;Model->Current.Items={Kit};Pawn->ApplyColdSteelProfile(Model);
        Check(FMath::IsNearlyEqual(Pawn->EffectiveFireInterval(),.675,1.e-6)&&FMath::IsNearlyEqual(Pawn->M870PumpPlayRate(),4.f/3.f,1.e-5f),TEXT("M870 runtime cadence and pump rate use the kit"));
        Check(Pawn->FireAnimation&&Pawn->AimFireAnimation&&Pawn->ReloadAnimation&&Pawn->ReloadEmptyAnimation&&Pawn->InspectAnimation,TEXT("M870 primary action assets resolve"));
        if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())
        {
            const auto Captured=Body->CaptureWeapon(Pawn->AKMViewmodel,Pawn->IdleAnimation,TEXT("Gun"));
            bool ArmsHidden=true,CapHidden=false,TubeAttached=false;int32 ArmSections=0;
            const auto* Asset=Pawn->AKMViewmodel->GetSkeletalMeshAsset();
            for(int32 I=0;I<Asset->GetMaterials().Num();++I)
            {
                const auto& Material=Asset->GetMaterials()[I];
                if(WeaponPresentationMaterials::IsArmSection(Material)){++ArmSections;ArmsHidden&=Captured.HiddenMaterials.Contains(I);}
                if(Material.MaterialSlotName==TEXT("M870_FactoryTubeCap"))CapHidden=Captured.HiddenMaterials.Contains(I);
            }
            for(const auto& Part:Captured.Parts)if(Part.Mesh.ToSoftObjectPath().ToString().StartsWith(M870TubeMagazineAssets::MeshPath))
                TubeAttached=Part.bVisible&&Part.Socket==TEXT("WPN_root");
            Check(ArmSections>0&&ArmsHidden&&CapHidden&&TubeAttached,TEXT("M870 world recipe excludes arms and cap and retains attached tube"));
        }
        auto* FX=Pawn->WeaponFX.Get();
        FX->SchedulePumpEjection(4.f/3.f,.1f);
        Check(FMath::IsNearlyEqual(World->GetTimerManager().GetTimerRemaining(FX->PumpEjectTimer),.1625f,1.e-5f),TEXT("remote pump ejection uses accepted rate minus network age"));
        World->GetTimerManager().ClearTimer(FX->PumpEjectTimer);
        auto* KitSave=NewObject<UColdSteelProfileSave>();KitSave->Profile=Model->Snapshot();TArray<uint8> KitBytes;
        const bool Written=UGameplayStatics::SaveGameToMemory(KitSave,KitBytes);
        const auto* KitRestore=Written?Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(KitBytes)):nullptr;
        Check(KitRestore&&G->Installed(KitRestore->Profile.Items[0]).FindRef(TEXT("trigger"))==TEXT("m870_lightweight_trigger_kit")&&
            G->CalculateItem(KitRestore->Profile.Items[0],G->Installed(KitRestore->Profile.Items[0])).Capacity==10,TEXT("M870 trigger and tube survive profile serialization"));
        Model->Current=Base;Pawn->ApplyColdSteelProfile(Model);
    }
    Check(ColdSteelModification::Tier(Item.Definition,TEXT("muzzle"),ShotgunDuckbillAssets::Part)==EGunsmithModificationTier::Special,TEXT("duckbill special modification tier"));
    for(const TCHAR* Muzzle:M870?TArray<const TCHAR*>{TEXT("false")}:TArray<const TCHAR*>{TEXT("false"),ShotgunChokeAssets::Part,ShotgunBirdcageAssets::Part,ShotgunSuppressorAssets::Part,ShotgunDuckbillAssets::Part})
        for(bool Tube:{false,true})
        {
            auto Equipped=Item;Parts(Equipped,Muzzle,Tube);Equipped.Magazine=Tube?10:7;Model->Current=Base;Model->Current.Items={Equipped};Pawn->ApplyColdSteelProfile(Model);
            const FString Case=FString(Muzzle)+(Tube?TEXT(" + extended"):TEXT(" + factory"));
            Check(Pawn->MagazineCapacity==(Tube?10:7),Case+TEXT(" capacity"));
            Check((Pawn->LargeDrum!=nullptr)==Tube,Case+TEXT(" tube model"));
            bool FoundCap=false,CapCorrect=true;
            if(const auto* Mesh=Pawn->AKMViewmodel->GetSkeletalMeshAsset())
                for(int32 M=0;M<Mesh->GetMaterials().Num();++M)
                    if(M870?Mesh->GetMaterials()[M].MaterialSlotName==TEXT("M870_FactoryTubeCap"):Mesh->GetMaterials()[M].MaterialSlotName.ToString().StartsWith(TEXT("S90_FactoryTubeCap_")))
                    {FoundCap=true;CapCorrect&=Pawn->AKMViewmodel->IsMaterialSectionShown(M,0)==!Tube;}
            Check(FoundCap&&CapCorrect,Case+TEXT(" native end cap visibility"));
            const bool Factory=FString(Muzzle)==TEXT("false");
            const TCHAR* Path=FString(Muzzle)==ShotgunDuckbillAssets::Part?ShotgunDuckbillAssets::MeshPath:
                FString(Muzzle)==ShotgunChokeAssets::Part?(Tube?Super90TubeMagazineAssets::ChokeMeshPath:ShotgunChokeAssets::MeshPath):
                FString(Muzzle)==ShotgunSuppressorAssets::Part?(Tube?Super90TubeMagazineAssets::SuppressorMeshPath:ShotgunSuppressorAssets::MeshPath):ShotgunBirdcageAssets::MeshPath;
            Check(Factory?!Pawn->MuzzleAttachment:Pawn->MuzzleAttachment&&Pawn->MuzzleAttachment->GetStaticMesh()&&
                Pawn->MuzzleAttachment->GetStaticMesh()->GetPathName().StartsWith(Path),Case+TEXT(" fitted muzzle model"));
            if(FString(Muzzle)==ShotgunDuckbillAssets::Part)
            {
                Check(Pawn->HasShotgunDuckbill()&&FMath::IsNearlyEqual(Pawn->HipSpreadMultiplier,float(Default.Spread*.75))&&Pawn->GetShotgunPelletSpreadMultiplier()==1.f,Case+TEXT(" only approved gameplay modifiers"));
                Check(FMath::IsNearlyEqual(Pawn->ADSInDuration,float(Default.ADS)*(Tube?1.1f:1.f)),Case+TEXT(" ADS composition"));
                const auto* Socket=Pawn->MuzzleAttachment->GetStaticMesh()->FindSocket(TEXT("Muzzle"));
                Check(Socket&&Socket->RelativeLocation.Equals(FVector(10.7,0,0),.001),Case+TEXT(" visible exit socket"));
            }
        }
    // A workbench draft may render on this pawn but must not alter committed ballistics.
    Model->Current=Base;Pawn->ApplyColdSteelProfile(Model);G->Begin(Item.InstanceId);G->Select(TEXT("muzzle"),ShotgunDuckbillAssets::Part);Pawn->ApplyColdSteelProfile(Model);
    Check(!Pawn->HasShotgunDuckbill()&&FMath::IsNearlyEqual(Pawn->HipSpreadMultiplier,float(Default.Spread)),TEXT("unapplied duckbill preview cannot enable gameplay"));
    G->Select(TEXT("muzzle"),ShotgunChokeAssets::Part);Pawn->ApplyColdSteelProfile(Model);
    Check(Pawn->GetShotgunPelletSpreadMultiplier()==1.f,TEXT("unapplied choke preview cannot tighten gameplay"));
    G->Close();
    auto Duck=Item;Parts(Duck,ShotgunDuckbillAssets::Part,true);Duck.Magazine=10;Model->Current=Base;Model->Current.Items={Duck};Pawn->ApplyColdSteelProfile(Model);
    G->Begin(Item.InstanceId);G->Select(TEXT("muzzle"),TEXT("false"));Pawn->ApplyColdSteelProfile(Model);
    Check(M870?!Pawn->HasShotgunDuckbill():Pawn->HasShotgunDuckbill(),TEXT("preview removal retains committed spread recipe"));G->Close();
    auto* Save=NewObject<UColdSteelProfileSave>();Save->Profile=Model->Snapshot();TArray<uint8> Bytes;
    Check(UGameplayStatics::SaveGameToMemory(Save,Bytes),TEXT("isolated profile serializes"));
    const auto* Restored=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
    Check(Restored&&(M870?!G->Installed(Restored->Profile.Items[0]).Contains(TEXT("muzzle")):G->Installed(Restored->Profile.Items[0]).FindRef(TEXT("muzzle"))==ShotgunDuckbillAssets::Part)&&
        G->Installed(Restored->Profile.Items[0]).FindRef(TEXT("magazine"))==TubeId,TEXT("save roundtrip preserves both slots"));
    for(bool Aiming:{false,true})
    {
        bool Match=true,Planar=true,Bounded=true,Ordered=true,Varied=false;
        FVector PreviousPattern=FVector::ZeroVector;
        for(uint32 Sequence=1;Sequence<=128;++Sequence)
        {
            const FVector Forward=FRotator(Sequence%2?47.f:-32.f,37.f,0).Vector();
            const FRotationMatrix Basis(Forward.Rotation());const FVector Up=Basis.GetUnitAxis(EAxis::Z),Right=Basis.GetUnitAxis(EAxis::Y);
            FRandomStream Owner(Super90Spread::Seed(Sequence)),Server(Super90Spread::Seed(Sequence));float Last=-10;
            for(int32 P=0;P<8;++P)
            {
                const float Cone=Super90Spread::ConeRadians(8,Aiming);
                const FVector A=Super90Spread::HorizontalFan(Forward,Cone,P,8,Owner.FRand());
                const FVector B=Super90Spread::HorizontalFan(Forward,Cone,P,8,Server.FRand());
                Match&=A.Equals(B,1.e-10);Planar&=FMath::Abs(A|Up)<1.e-7;
                const float Angle=FMath::Atan2(A|Right,A|Forward);Bounded&=FMath::Abs(Angle)<=Cone;Ordered&=Angle>Last;Last=Angle;
                if(P==0){if(Sequence>2)Varied|=!A.Equals(PreviousPattern,1.e-5);PreviousPattern=A;}
            }
        }
        Check(Match&&Planar&&Bounded&&Ordered&&Varied,Aiming?TEXT("ADS seeded fan: matched planar ordered bounded"):TEXT("hip seeded fan: matched planar ordered bounded"));
    }
    Check(Super90Spread::HorizontalFan(FVector::ForwardVector,.1f,0,1,.25f)==FVector::ForwardVector&&Super90Spread::ConeRadians(1,true)==0,TEXT("slug has no pellet fan"));

    auto* RemotePC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,500),FRotator::ZeroRotator);
    PS->SetOwner(RemotePC);RemotePC->SetPlayerState(PS);RemotePC->Possess(Remote);Remote->SetPlayerState(PS);
    auto* Shadow=Model->CreateShadowModel(Base);PS->ShadowModel=Shadow;Remote->NetShadowProfile=Shadow;Shadow->CurrentPawn=Remote;
    Remote->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Remote->DispatchBeginPlay();
    Check(Remote->HasAuthority()&&!Remote->IsLocallyControlled(),TEXT("remote authority identity"));
    uint32 Sequence=0;
    for(const TCHAR* Ammo:{TEXT("ammo_12g"),TEXT("ammo_12g_flechette"),TEXT("ammo_12g_slug")})
    {
        Shadow->Current=Base;Duck.LoadedAmmoType=Ammo;Duck.Magazine=10;Shadow->Current.Items={Duck};Remote->ApplyColdSteelProfile(Shadow);
        Remote->Ballistics->Rounds.Reset();Remote->CurrentSpread=Remote->MoveSpread=Remote->AirSpread=0;PS->Super90NextFireTime=0;
        const FVector Eye=Remote->GetPawnViewLocation(),Muzzle=Eye+FVector(50,0,0);const uint32 Shot=++Sequence;
        PS->ServerSuper90Shot_Implementation(Shot,Duck.InstanceId,Eye,Muzzle,FVector::ForwardVector,true,World->GetTimeSeconds(),Remote);
        const int32 Count=Shadow->AmmoProjectileCount(Duck,8);float Damage=0;bool Flat=true;
        for(const auto& Round:Remote->Ballistics->Rounds){Damage+=Round.Damage;Flat&=(M870||FMath::Abs(Round.Direction.Z)<1.e-6)&&!Round.bCosmeticOnly;}
        Check(Shadow->FindItem(Duck.InstanceId)->Magazine==9&&Remote->Ballistics->ActiveCount()==Count,FString(Ammo)+TEXT(" server owns count and one-shell consumption"));
        Check(Flat&&FMath::IsNearlyEqual(Damage,Remote->DamagePerShot,.01f),FString(Ammo)+TEXT(" server horizontal directions and conserved total damage"));
        PS->ServerSuper90Shot_Implementation(Shot,Duck.InstanceId,Eye,Muzzle,FVector::ForwardVector,true,World->GetTimeSeconds(),Remote);
        Check(Shadow->FindItem(Duck.InstanceId)->Magazine==9&&Remote->Ballistics->ActiveCount()==Count,FString(Ammo)+TEXT(" duplicate request ignored"));
    }
    for(bool Loader:{false,true})
    {
        auto Empty=Item;Parts(Empty,ShotgunDuckbillAssets::Part,true,Loader);Empty.Magazine=0;
        Shadow->Current=Base;Shadow->Current.Items={Empty};Remote->ApplyColdSteelProfile(Shadow);PS->Super90Reload.Active=false;
        PS->ServerSuper90Reload_Implementation(++Sequence,Empty.InstanceId,FString(),Remote);
        Check(PS->Super90Reload.Active&&PS->Super90Reload.Count==(Loader?7:10),Loader?TEXT("server loader respects seven-shell physical limit"):TEXT("server ordinary reload plans all ten shells"));
        if(PS->Super90Reload.Active)
        {
            PS->Super90Reload.Started=World->GetTimeSeconds()-PS->Super90Reload.Duration-.1;
            PS->TickSuper90Authority(0.f);
        }
        Check(Shadow->FindItem(Empty.InstanceId)->Magazine==(Loader?7:10)&&Shadow->PouchCount(TEXT("ammo_12g"))==(Loader?93:90)&&!PS->Super90Reload.Active,
            Loader?TEXT("server loader commits seven once"):TEXT("server ordinary reload commits ten once"));
        if(Loader)
        {
            PS->ServerSuper90Reload_Implementation(++Sequence,Empty.InstanceId,FString(),Remote);
            Check(PS->Super90Reload.Active&&PS->Super90Reload.Count==3,TEXT("server second loader fills remaining three"));
            if(PS->Super90Reload.Active){PS->Super90Reload.Started=World->GetTimeSeconds()-PS->Super90Reload.Duration-.1;PS->TickSuper90Authority(0.f);}
            Check(Shadow->FindItem(Empty.InstanceId)->Magazine==10&&Shadow->PouchCount(TEXT("ammo_12g"))==90,TEXT("two loader actions conserve ten shells"));
        }
    }
    // Capacity shrink against authority, including already-fired and virtual shells.
    for(int32 AmmoCount:{10,8,6})for(int32 Virtual:{0,3})
    {
        auto Previous=Base;auto Old=Item;Parts(Old,ShotgunDuckbillAssets::Part,true);Old.Magazine=AmmoCount;Old.VirtualMagazineAmmo=Virtual;Previous.Items={Old};
        auto Incoming=Previous;Parts(Incoming.Items[0],ShotgunDuckbillAssets::Part,false);
        Incoming.Items[0].Magazine=7;Incoming.AmmoPouch[TEXT("ammo_12g")]=103;Shadow->Current=Previous;
        PS->IncomingSuper90Revision=0;PS->Super90PouchDelta={0,0,0};
        const bool OK=PS->RebaseSuper90Upload(Incoming,Previous,false);
        const int32 Overflow=FMath::Max(0,AmmoCount-7),Refund=FMath::Max(0,Overflow-Virtual);
        Check(OK&&Incoming.Items[0].Magazine==FMath::Min(AmmoCount,7)&&Incoming.AmmoPouch.FindRef(TEXT("ammo_12g"))==100+Refund&&
            Incoming.Items[0].VirtualMagazineAmmo==Virtual-FMath::Min(Virtual,Overflow)&&Incoming.CampfireInventoryRevision==Previous.CampfireInventoryRevision+1,
            FString::Printf(TEXT("authority resize %d rounds %d virtual: no phantom refund"),AmmoCount,Virtual));
    }
    // The real profile-acceptance entrypoint must reject the old inventory revision on replay.
    auto Previous=Base;auto Full=Item;Parts(Full,ShotgunDuckbillAssets::Part,true);Full.Magazine=10;Previous.Items={Full};Shadow->Current=Previous;
    auto Upload=Previous;Parts(Upload.Items[0],ShotgunDuckbillAssets::Part,false);Upload.Items[0].Magazine=7;Upload.AmmoPouch[TEXT("ammo_12g")]=103;
    PS->BoundProfileId=Upload.NetworkProfileId;PS->Super90PouchDelta={0,0,0};PS->IncomingSuper90Revision=0;PS->Super90Reload.Active=false;
    const bool First=PS->ApplyGuestProfile(Upload);const auto Once=Shadow->Snapshot();const bool Again=PS->ApplyGuestProfile(Upload);const auto Twice=Shadow->Snapshot();
    Check(First&&Again&&Once.Items[0].Magazine==7&&Twice.Items[0].Magazine==7&&Once.AmmoPouch.FindRef(TEXT("ammo_12g"))==103&&Twice.AmmoPouch.FindRef(TEXT("ammo_12g"))==103,
        TEXT("actual guest upload resize and stale replay refund once"));

    if(M870)
    {
        auto Kit=Item;Parts(Kit,TEXT("false"),true);Trigger(Kit);Kit.Magazine=10;
        Shadow->Current=Base;Shadow->Current.Items={Kit};Remote->ApplyColdSteelProfile(Shadow);
        PS->Super90Reload.Active=false;PS->Super90NextFireTime=0;Remote->Ballistics->Rounds.Reset();
        const FVector Eye=Remote->GetPawnViewLocation(),Muzzle=Eye+FVector(50,0,0);const double Now=World->GetTimeSeconds();
        const uint32 Shot=++Sequence;
        PS->ServerSuper90Shot_Implementation(Shot,Kit.InstanceId,Eye,Muzzle,FVector::ForwardVector,true,Now,Remote);
        Check(Shadow->FindItem(Kit.InstanceId)->Magazine==9&&FMath::IsNearlyEqual(PS->Super90NextFireTime-Now,.675,1.e-5),TEXT("M870 authority applies committed trigger cadence"));
        Check(FMath::IsNearlyEqual(PS->M870AuthorityPumpClosedTime-Now,double(M870WeaponAssets::PumpClosed)/(4./3.),1.e-5),TEXT("M870 authority records the shortened pump close time"));
        PS->ServerSuper90Shot_Implementation(++Sequence,Kit.InstanceId,Eye,Muzzle,FVector::ForwardVector,true,Now,Remote);
        Check(Shadow->FindItem(Kit.InstanceId)->Magazine==9,TEXT("M870 authority rejects a new shot inside cooldown"));
        PS->ServerM870PumpInterrupt_Implementation(++Sequence,Kit.InstanceId,Shot,Now,Remote);
        Check(WeaponReloadStages::NeedsCycle(*Shadow->FindItem(Kit.InstanceId)),TEXT("accepted M870 pump interrupt persists pending chamber"));
        PS->ServerSuper90Reload_Implementation(++Sequence,Kit.InstanceId,FString(),Remote);
        Check(PS->Super90Reload.Active&&PS->Super90Reload.CycleOnly&&PS->Super90Reload.Count==0,TEXT("M870 pending chamber resumes as pump only"));
        if(PS->Super90Reload.Active){PS->Super90Reload.Started=Now-PS->Super90Reload.Duration-.1;PS->TickSuper90Authority(0.f);}
        Check(Shadow->FindItem(Kit.InstanceId)->Magazine==9&&!WeaponReloadStages::NeedsCycle(*Shadow->FindItem(Kit.InstanceId)),TEXT("M870 pump-only recovery neither creates nor spends a shell"));
        // Test the actual client receipt entrypoint against an old-pawn response.
        auto* OwnerPS=PC->GetPlayerState<AColdSteelPlayerState>();Model->Current=Base;Model->CurrentPawn=Pawn;Pawn->ApplyColdSteelProfile(Model);
        FSuper90NetAmmoState Receipt;Receipt.SourcePawn=Remote;Receipt.PouchCounts={12,12,12};Receipt.PouchDelta={0,0,0};
        Receipt.InventoryRevision=Model->InventoryRevision();Receipt.Revision=1;Receipt.Magazines.AddDefaulted();
        Receipt.Magazines[0].Instance=Item.InstanceId;Receipt.Magazines[0].Ammo=TEXT("ammo_12g");Receipt.Magazines[0].Count=1;Receipt.Magazines[0].NeedsCycle=true;
        OwnerPS->Super90ClientPawn=Pawn;OwnerPS->ClientSuper90Ammo_Implementation(Receipt);
        Check(Model->FindItem(Item.InstanceId)->Magazine==7&&!WeaponReloadStages::NeedsCycle(*Model->FindItem(Item.InstanceId))&&Model->PouchCount(TEXT("ammo_12g"))==100,
            TEXT("old pawn ammo receipt cannot overwrite the new life"));
        OwnerPS->Super90ClientPawn=Remote;OwnerPS->M870PredictedPumpInterrupts.Add(Item.InstanceId,100);
        Receipt.SourcePawn=Pawn;Receipt.Magazines[0].Count=7;Receipt.Magazines[0].NeedsCycle=false;Receipt.PouchCounts={100,100,100};
        OwnerPS->ClientSuper90Ammo_Implementation(Receipt);
        Check(OwnerPS->M870PredictedPumpInterrupts.IsEmpty()&&!WeaponReloadStages::NeedsCycle(*Model->FindItem(Item.InstanceId)),TEXT("fresh pawn receipt clears stale M870 pump prediction"));
    }
    if(M870)
    {
        // R3 audit revision 2 includes the late-rejection / ordinary-punch case.
#include "M870QuickMeleeAudit.inl"
    }
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);Root->SetArrayField(TEXT("results"),Rows);
    Root->SetStringField(TEXT("mode"),TEXT("isolated authority implementation and asset execution; not socket replication"));
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    const FString Path=FPaths::ProjectSavedDir()/(M870?TEXT("M870CompletionAudit20261017/authority-result.json"):TEXT("Super90AttachmentAudit20261016/authority-result.json"));IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    Model->CurrentPawn.Reset();Shadow->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {
        It->RouteEndPlay(EEndPlayReason::Quit);
        TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);
        for(auto* Component:Components)if(Component->HasBegunPlay())Component->EndPlay(EEndPlayReason::Quit);
    }
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
