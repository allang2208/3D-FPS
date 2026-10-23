#include "ProductionToolComponent.h"
#include "RuneboundHammerTuning.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Weapons/FrostSwordRunes.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/AzureDragonEnergyComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Net/UnrealNetwork.h"

namespace
{
constexpr const TCHAR* MeshPrefix=TEXT("/Game/Weapons/RuneboundWarhammer20261022/");
UE::Geometry::FDynamicMesh3 MakeRuneMotes()
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    auto* UV=Mesh.Attributes()->PrimaryUV();auto* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 I=0;I<RuneboundHammer::MoteBudget;++I)
    {
        const int32 V=I*4;
        for(int32 C=0;C<4;++C)
        {
            Mesh.AppendVertex(FVector3d(0.,I*.1,C*.1));
            UV->AppendElement(FVector2f(float(C&1),float(C>>1)));
            Normals->AppendElement(FVector3f(-1.f,0.f,0.f));
        }
        for(const FIndex3i& T:{FIndex3i(V,V+2,V+1),FIndex3i(V+1,V+2,V+3)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
    return Mesh;
}
}

bool RuneboundHammer::HasSwiftRune(const FColdSteelItem& Item)
{
    if(Item.Definition!=Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
        (*Parts)->TryGetStringField(TEXT("rune"),Rune)&&Rune==ColdSteelFrostRunes::SwiftMana;
}

bool RuneboundHammer::HasDestructionRune(const FColdSteelItem& Item)
{
    if(Item.Definition!=Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
        (*Parts)->TryGetStringField(TEXT("rune"),Rune)&&Rune==ColdSteelFrostRunes::DestructionMana;
}

double RuneboundHammer::AttributeMultiplier(const FColdSteelItem& Item)
{return HasDestructionRune(Item)?DestructionAttributeMultiplier:1.;}

double RuneboundHammer::AttributeMultiplier(const FColdSteelProfile& State,FName Key)
{
    if(Key!=TEXT("intt")&&Key!=TEXT("int")&&Key!=TEXT("wis"))return 1.;
    const auto* Item=State.Items.FindByPredicate([&](const FColdSteelItem& I)
        {return I.Place==1&&I.Cell==State.ActiveWeaponSlot;});
    return Item?AttributeMultiplier(*Item):1.;
}

int32 RuneboundHammer::RequiredHits(const FColdSteelItem& Item)
{return HasSwiftRune(Item)?SwiftHitsToAwaken:HitsToAwaken;}

void UProductionToolComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UProductionToolComponent,RuneboundInstance);
    DOREPLIFETIME(UProductionToolComponent,RuneboundCharge);
    DOREPLIFETIME(UProductionToolComponent,RuneboundActiveUntil);
    DOREPLIFETIME(UProductionToolComponent,FinalTollSealState);
}

double UProductionToolComponent::RuneboundClock() const
{
    const auto* World=GetWorld();
    if(const auto* GS=World?World->GetGameState():nullptr)return GS->GetServerWorldTimeSeconds();
    return World?World->GetTimeSeconds():0.;
}

bool UProductionToolComponent::IsRuneboundAwakened(const FColdSteelItem& Item) const
{
    if(Item.Definition!=RuneboundHammer::Definition||Item.InstanceId!=RuneboundInstance||
        RuneboundActiveUntil<=RuneboundClock())return false;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Profile=Pawn?ColdSteelAuthority::ForPawn(Pawn):nullptr;
    const auto* Equipped=Profile?Profile->ActiveProductionTool():nullptr;
    return Pawn&&(!Health||!Health->IsDead())&&Equipped&&Equipped->InstanceId==Item.InstanceId;
}

void UProductionToolComponent::TickRunebound(float Delta)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority())return;
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const FString Instance=Item&&Item->Definition==RuneboundHammer::Definition&&(!Health||!Health->IsDead())
        ?Item->InstanceId:FString();
    if(Instance!=RuneboundInstance)
    {
        RuneboundInstance=Instance;RuneboundCharge=0;RuneboundActiveUntil=0.;RuneboundRecentAttacks.Reset();RuneboundDetonationHits=0;
        FinalTollMarks.Reset();FinalTollRecentHits.Reset();PublishFinalTollSeals();
        Pawn->ForceNetUpdate();
    }
    if(RuneboundActiveUntil>0.&&RuneboundActiveUntil<=RuneboundClock())
    {RuneboundActiveUntil=0.;RuneboundCharge=0;RuneboundDetonationHits=0;Pawn->ForceNetUpdate();}
    if(!Item||!RuneboundHammer::HasStarOath(*Item))RuneboundDetonationHits=0;
    const int32 PreviousSeals=FinalTollMarks.Num();
    if(!Item||!RuneboundHammer::HasFinalToll(*Item)||RuneboundActiveUntil<=RuneboundClock())
    {FinalTollMarks.Reset();FinalTollRecentHits.Reset();}
    else FinalTollMarks.RemoveAll([&](const FFinalTollMark& Mark)
    {
        const auto* Target=Mark.Target.Get();
        const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        return !Target||Mark.Expires<=RuneboundClock()||(Combat&&Combat->IsDead());
    });
    if(PreviousSeals!=FinalTollMarks.Num())PublishFinalTollSeals();
}

void UProductionToolComponent::RecordRuneboundHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||Shot.ItemDefinition!=RuneboundHammer::Definition||
        !Shot.bMelee||Shot.AttackForm!=EMonsterAttackForm::Blunt||!Shot.MasteryAttackSerial)return;
    TickRunebound(0.f);
    RecordFinalTollHit(Shot,Hit);
    if(RuneboundInstance.IsEmpty()||Shot.ItemInstance!=RuneboundInstance||
        RuneboundRecentAttacks.Contains(Shot.MasteryAttackSerial))return;
    // Every contact of a sweep/shockwave/whirlwind shares one serial, including contacts
    // after awakening expires. Active attacks cannot become a later charge retroactively.
    if(RuneboundRecentAttacks.Num()>=32)RuneboundRecentAttacks.RemoveAt(0);
    RuneboundRecentAttacks.Add(Shot.MasteryAttackSerial);
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(RuneboundActiveUntil>RuneboundClock())
    {
        const bool Detonate=Item&&RuneboundHammer::HasStarOath(*Item)&&
            ++RuneboundDetonationHits>=RuneboundHammer::DetonationHits;
        if(Detonate){RuneboundDetonationHits=0;QueueRuneboundDetonation(Hit,Shot);}
        MulticastRuneboundImpact(RuneboundInstance,Shot.MasteryAttackSerial,RuneboundClock(),Detonate);
        return;
    }
    const int32 Required=Item?RuneboundHammer::RequiredHits(*Item):RuneboundHammer::HitsToAwaken;
    RuneboundCharge=FMath::Min(int32(RuneboundCharge)+1,Required);
    if(RuneboundCharge==Required)
        RuneboundActiveUntil=RuneboundClock()+RuneboundHammer::ActiveSeconds;
    Pawn->ForceNetUpdate();
}

void UProductionToolComponent::MulticastRuneboundImpact_Implementation(const FString& Instance,uint32 AttackSerial,double ServerAt,bool bDetonation)
{
    if(GetNetMode()==NM_DedicatedServer||Instance!=RuneboundInstance||RuneboundClock()-ServerAt>=RuneboundHammer::HitMoteSeconds)return;
    if(RuneboundHitBursts.ContainsByPredicate([&](const FRuneboundHitBurst& Burst){return Burst.AttackSerial==AttackSerial&&Burst.bFinalToll;}))return;
    if(RuneboundHitBursts.Num()!=RuneboundHammer::HitBurstSlots)RuneboundHitBursts.SetNum(RuneboundHammer::HitBurstSlots);
    // Preserve the long drifting tail of a detonation when normal contacts arrive.
    // Expired slots and ordinary-hit slots are reused before a live detonation.
    FRuneboundHitBurst* Oldest=nullptr;
    const double Now=RuneboundClock();
    for(auto& Burst:RuneboundHitBursts)if(Now-Burst.ServerAt>=RuneboundHammer::HitMoteSeconds)
        if(!Oldest||Burst.ServerAt<Oldest->ServerAt)Oldest=&Burst;
    if(!Oldest)for(auto& Burst:RuneboundHitBursts)if(!Burst.bDetonation)
        if(!Oldest||Burst.ServerAt<Oldest->ServerAt)Oldest=&Burst;
    if(!Oldest)
    {
        Oldest=&RuneboundHitBursts[0];
        for(auto& Burst:RuneboundHitBursts)if(Burst.ServerAt<Oldest->ServerAt)Oldest=&Burst;
    }
    Oldest->ServerAt=FMath::Min(ServerAt,RuneboundClock());Oldest->AttackSerial=AttackSerial;
    Oldest->bDetonation=bDetonation;Oldest->bFinalToll=false;
    Oldest->bHasOrigin=false;
    if(const auto* Anchor=RuneboundMoteAnchor.Get())
    {
        const FTransform Frame=Anchor->GetComponentTransform();
        Oldest->Origin=Frame.TransformPosition(FVector(0.f,0.f,RuneboundHammer::HeadHeightCM));
        Oldest->Rotation=Frame.GetRotation();Oldest->bHasOrigin=true;
    }
}

void UProductionToolComponent::UpdateRuneboundPresentation(float Delta,bool Equipped)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||GetNetMode()==NM_DedicatedServer)return;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* LocalProfile=Pawn->IsLocallyControlled()?ColdSteelAuthority::ForPawn(Pawn):nullptr;
    const auto* LocalItem=LocalProfile?LocalProfile->ActiveProductionTool():nullptr;
    const bool LocalSwift=LocalItem&&RuneboundHammer::HasSwiftRune(*LocalItem);
    const bool LocalDestruction=LocalItem&&RuneboundHammer::HasDestructionRune(*LocalItem);
    Equipped=Equipped&&(!Health||!Health->IsDead());
    if(Pawn->IsLocallyControlled())
    {
        Equipped=Equipped&&LocalItem&&LocalItem->Definition==RuneboundHammer::Definition&&LocalItem->InstanceId==RuneboundInstance;
    }
    const bool Active=Equipped&&RuneboundActiveUntil>RuneboundClock();
    ReconcileFinalTollSeals(Active);
    if(Equipped&&Pawn->IsLocallyControlled()&&!RuneboundHud)
    {
        RuneboundHud=NewObject<UAzureDragonEnergyComponent>(Pawn);
        RuneboundHud->ConfigureMaterial(FSoftObjectPath(RuneboundHammer::Hud));
        RuneboundHud->RegisterComponent();
    }
    if(RuneboundHud)
    {
        RuneboundHud->Configure(Equipped);
        const bool Activated=Active&&RuneboundShownActivation!=RuneboundActiveUntil;
        const float Fill=Active?float((RuneboundActiveUntil-RuneboundClock())/RuneboundHammer::ActiveSeconds)
            :float(RuneboundCharge)/(LocalSwift?RuneboundHammer::SwiftHitsToAwaken:RuneboundHammer::HitsToAwaken);
        RuneboundHud->SetEnergy(Equipped?Fill:0.f,Activated,Equipped&&RuneboundShownCharge!=RuneboundCharge);
        RuneboundShownCharge=Equipped?RuneboundCharge:-1;RuneboundShownActivation=Equipped?RuneboundActiveUntil:0.;
    }
    RuneboundVisual=FMath::FInterpTo(RuneboundVisual,Active?1.f:0.f,Delta,Active?7.f:4.f);
    if(!Equipped)RuneboundVisual=0.f;
    if(!Equipped)
    {
        for(const auto& MID:RuneboundRuneMIDs)if(IsValid(MID.Get()))MID->SetScalarParameterValue(TEXT("RuneAwake"),0.f);
        RuneboundRuneMIDs.Reset();RuneboundMoteAnchor.Reset();RuneboundMaterialRefresh=0.f;
        RuneboundHitBursts.Reset();
        bRuneboundSwiftVisual=false;
        if(RuneboundMotes)RuneboundMotes->SetVisibility(false);
        return;
    }
    RuneboundMaterialRefresh-=Delta;
    if(RuneboundMaterialRefresh<=0.f)
    {
        RuneboundMaterialRefresh=.25f;
        RuneboundRuneMIDs.Reset();RuneboundMoteAnchor.Reset();
        bRuneboundSwiftVisual=false;bFinalTollVisual=false;
        TInlineComponentArray<UStaticMeshComponent*> Parts(Pawn);
        for(auto* Part:Parts)
            if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetPathName().StartsWith(MeshPrefix))
            {
                if(Part->ComponentHasTag(TEXT("SwordSlot=head_mount"))&&
                    !(Pawn->IsLocallyControlled()?Part->bOwnerNoSee:Part->bOnlyOwnerSee))RuneboundMoteAnchor=Part;
                if(Part->GetStaticMesh()->GetName().Contains(TEXT("FinalToll"))&&Part->IsVisible()&&!Part->bHiddenInGame&&
                    !(Pawn->IsLocallyControlled()?Part->bOwnerNoSee:Part->bOnlyOwnerSee))bFinalTollVisual=true;
                for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
                    if(auto* Material=Part->GetMaterial(Slot);Material&&
                        (Material->GetMaterial()->GetName()==TEXT("M_RuneboundAwakeSurface")||
                         Material->GetMaterial()->GetName()==TEXT("M_RuneboundSwiftRuneSurface")||
                         Material->GetMaterial()->GetName()==TEXT("M_RuneboundDestructionRuneSurface")||
                         Material->GetMaterial()->GetName()==TEXT("M_FinalToll_Rune_Energy")||
                         Material->GetMaterial()->GetName()==TEXT("M_StarOath_Rune_Energy")||
                         Material->GetMaterial()->GetName()==TEXT("M_StarOath_Optical_Crystal")))
                    {
                        if(Material->GetMaterial()->GetName()==TEXT("M_RuneboundSwiftRuneSurface")&&Part->IsVisible()&&!Part->bHiddenInGame&&
                            !(Pawn->IsLocallyControlled()?Part->bOwnerNoSee:Part->bOnlyOwnerSee))bRuneboundSwiftVisual=true;
                        auto* MID=Cast<UMaterialInstanceDynamic>(Material);
                        if(!MID)MID=Part->CreateDynamicMaterialInstance(Slot,Material);
                        if(MID)RuneboundRuneMIDs.AddUnique(MID);
                    }
            }
    }
    float ImpactPulse=0.f;
    if(Active)for(const auto& Burst:RuneboundHitBursts)
    {
        const float HitAge=float(RuneboundClock()-Burst.ServerAt);
        if(HitAge>=0.f&&HitAge<.45f)ImpactPulse=FMath::Max(ImpactPulse,FMath::Exp(-HitAge*10.f)*(Burst.bDetonation?3.6f:1.f));
    }
    const auto* TintAnchor=RuneboundMoteAnchor.Get();
    auto* TintSurface=TintAnchor?TintAnchor->GetMaterial(0):nullptr;
    const bool RedEnergy=Pawn->IsLocallyControlled()?LocalDestruction:
        TintSurface&&TintSurface->GetBaseMaterial()->GetName()==TEXT("M_RuneboundDestructionRuneSurface");
    for(const auto& MID:RuneboundRuneMIDs)if(IsValid(MID.Get()))
    {
        MID->SetScalarParameterValue(TEXT("RuneAwake"),RuneboundVisual);
        MID->SetScalarParameterValue(TEXT("RuneImpact"),ImpactPulse);
        MID->SetVectorParameterValue(TEXT("EnergyTint"),RedEnergy?FLinearColor(1.f,.008f,.003f):bFinalTollVisual?FLinearColor(1.f,.64f,.22f):FLinearColor(.015f,.27f,1.f));
    }
    if(Equipped&&!RuneboundMoteMaterial&&!RuneboundAssetLoad)
    {
        const FSoftObjectPath Path(RuneboundHammer::Motes);
        const FSoftObjectPath DestructionPath(RuneboundHammer::DestructionMotes);
        TWeakObjectPtr<UProductionToolComponent> Weak(this);
        RuneboundAssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Path,DestructionPath,FSoftObjectPath(RuneboundHammer::FinalTollMotes)},FStreamableDelegate::CreateLambda([Weak,Path,DestructionPath]()
        {if(Weak.IsValid())
        {
            Weak->RuneboundMoteMaterial=Cast<UMaterialInterface>(Path.ResolveObject());
        }}));
    }
    if(Active&&RuneboundMoteMaterial&&!RuneboundMotes)
    {
        RuneboundMotes=NewObject<UDynamicMeshComponent>(Pawn);
        RuneboundMotes->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        RuneboundMotes->SetGenerateOverlapEvents(false);RuneboundMotes->SetCanEverAffectNavigation(false);
        RuneboundMotes->SetCastShadow(false);RuneboundMotes->SetReceivesDecals(false);
        RuneboundMotes->bVisibleInRayTracing=false;RuneboundMotes->bAffectDistanceFieldLighting=false;
        RuneboundMotes->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        RuneboundMotes->SetTranslucentSortPriority(3);RuneboundMotes->RegisterComponent();
        RuneboundMotes->SetMesh(MakeRuneMotes());
        RuneboundMoteMID=UMaterialInstanceDynamic::Create(RuneboundMoteMaterial,this);
        RuneboundMotes->SetMaterial(0,RuneboundMoteMID);
    }
    if(!RuneboundMotes)return;
    const bool Swift=Pawn->IsLocallyControlled()?LocalSwift:bRuneboundSwiftVisual;
    auto* PC=UGameplayStatics::GetPlayerController(Pawn,0);
    const auto* ViewerCamera=PC?PC->PlayerCameraManager.Get():nullptr;
    const auto* Anchor=RuneboundMoteAnchor.Get();
    auto* NativeSurface=Anchor?Anchor->GetMaterial(0):nullptr;
    const bool Destruction=Pawn->IsLocallyControlled()?LocalDestruction:
        NativeSurface&&NativeSurface->GetBaseMaterial()->GetName()==TEXT("M_RuneboundDestructionRuneSurface");
    // The retained streamable handle owns both loaded materials; no per-frame load.
    auto* DestructionSurface=Destruction?Cast<UMaterialInterface>(FSoftObjectPath(RuneboundHammer::DestructionMotes).ResolveObject()):nullptr;
    auto* GoldSurface=bFinalTollVisual?Cast<UMaterialInterface>(FSoftObjectPath(RuneboundHammer::FinalTollMotes).ResolveObject()):nullptr;
    auto* MoteSurface=GoldSurface?GoldSurface:DestructionSurface?DestructionSurface:RuneboundMoteMaterial.Get();
    if(MoteSurface&&RuneboundMoteMID->GetBaseMaterial()!=MoteSurface->GetBaseMaterial())
    {
        RuneboundMoteMID=UMaterialInstanceDynamic::Create(MoteSurface,this);
        RuneboundMotes->SetMaterial(0,RuneboundMoteMID);
    }
    // Capture late-resolving equipment once. Emitted particles remain in world
    // space while the hammer follows through; the ambient motes still follow it.
    if(Anchor)for(auto& Burst:RuneboundHitBursts)if(!Burst.bHasOrigin&&Burst.ServerAt>=0.)
    {
        const FTransform Birth=Anchor->GetComponentTransform();
        Burst.Origin=Birth.TransformPosition(FVector(0.f,0.f,RuneboundHammer::HeadHeightCM));
        Burst.Rotation=Birth.GetRotation();Burst.bHasOrigin=true;
    }
    const bool Show=Anchor&&Anchor->IsVisible()&&!Anchor->bHiddenInGame&&ViewerCamera&&RuneboundVisual>.005f&&
        FVector::DistSquared(ViewerCamera->GetCameraLocation(),Anchor->GetComponentLocation())<FMath::Square(6000.f);
    RuneboundMotes->SetVisibility(Show);
    if(!Show)return;
    RuneboundMoteMID->SetScalarParameterValue(TEXT("Strength"),RuneboundVisual);
    RuneboundMoteMID->SetVectorParameterValue(TEXT("EnergyTint"),Destruction?FLinearColor(1.f,.008f,.003f):FLinearColor(1.f,.64f,.22f));
    const FTransform Frame=Anchor->GetComponentTransform();
    const FQuat View=ViewerCamera->GetCameraRotation().Quaternion();
    const FVector Eye=ViewerCamera->GetCameraLocation();
    const float Age=float(FMath::Fmod(RuneboundClock(),1200.));
    const int32 AmbientCount=Swift?RuneboundHammer::SwiftMoteCount:Destruction?RuneboundHammer::DestructionMoteCount:RuneboundHammer::MoteCount;
    const int32 NormalHitCount=Swift?RuneboundHammer::SwiftHitMotes:Destruction?RuneboundHammer::DestructionHitMotes:RuneboundHammer::HitMotes;
    const double ServerNow=RuneboundClock();
    RuneboundMotes->SetWorldTransform(FTransform(View,Eye));
    RuneboundMotes->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        const auto Billboard=[&](int32 Index,const FVector& World,float Width,float Length,const FVector& Direction)
        {
            const FVector3d C(View.UnrotateVector(World-Eye));
            const FVector Projected=View.UnrotateVector(Direction);
            const FVector3d Along=FVector3d(0.,Projected.Y,Projected.Z).GetSafeNormal(UE_SMALL_NUMBER,FVector3d(0.,0.,1.));
            const FVector3d Across(0.,Along.Z,-Along.Y);
            const FVector3d W=Across*Width,L=Along*Length;
            const int32 V=Index*4;
            Mesh.SetVertex(V,C-W-L);Mesh.SetVertex(V+1,C+W-L);
            Mesh.SetVertex(V+2,C-W+L);Mesh.SetVertex(V+3,C+W+L);
        };
        const auto Quad=[&](int32 Index,const FVector& Local,float Size)
        {Billboard(Index,Frame.TransformPosition(Local),Size,Size,View.RotateVector(FVector::UpVector));};
        for(int32 I=0;I<RuneboundHammer::AmbientMoteCapacity;++I)
        {
            if(I>=AmbientCount){Quad(I,FVector(0.,0.,RuneboundHammer::HeadHeightCM),0.f);continue;}
            const float Phase=I*2.399963f;
            const float U=FMath::Frac(Age*(.18f+.015f*(I%5))+I*.618034f);
            const float A=Phase+Age*(Swift?.95f:Destruction?-.4f:.6f),R=(Destruction?12.f:7.f)+float(I%6)*1.5f;
            Quad(I,FVector(FMath::Cos(A)*R,FMath::Sin(A)*R,Destruction?RuneboundHammer::HeadHeightCM-14.f+U*32.f:40.f+U*67.f),
                (.24f+.08f*(I%4))*(Swift?1.2f:Destruction?1.5f:1.f)*FMath::Sin(U*PI)*RuneboundVisual);
        }
        // A short spray of fast streaks and shards opens the impact, then slower
        // suspended flecks drift upward. Reuse four bounded pools and one mesh.
        for(int32 Slot=0;Slot<RuneboundHammer::HitBurstSlots;++Slot)
        {
            const auto* Burst=RuneboundHitBursts.IsValidIndex(Slot)?&RuneboundHitBursts[Slot]:nullptr;
            const float BurstAge=Burst?float(ServerNow-Burst->ServerAt):RuneboundHammer::HitMoteSeconds;
            const float Seed=Burst?float(Burst->AttackSerial%4096)*.013f:0.f;
            const bool Detonation=Burst&&Burst->bDetonation;
            const int32 HitCount=Detonation?RuneboundHammer::DetonationMotes:NormalHitCount;
            for(int32 I=0;I<RuneboundHammer::HitMoteCapacity;++I)
            {
                const int32 Index=RuneboundHammer::AmbientMoteCapacity+Slot*RuneboundHammer::HitMoteCapacity+I;
                const float A=BurstAge-(I%6)*.003f;
                const float Random=FMath::Frac(I*.754877f+Seed);
                if(Detonation&&I<48)
                {
                    if(!Burst->bHasOrigin||A<=0.f||A>=.62f)
                    {Quad(Index,FVector(0.,0.,RuneboundHammer::HeadHeightCM),0.f);continue;}
                    const float Angle=I*(2.f*PI/48.f)+Seed;
                    const FVector Radial=Burst->Rotation.RotateVector(FVector(FMath::Cos(Angle),FMath::Sin(Angle),0.f));
                    const float Radius=8.f+RuneboundHammer::DetonationRadiusCM*(1.f-FMath::Exp(-6.f*A));
                    const float Fade=FMath::Sin(FMath::Clamp(A/.62f,0.f,1.f)*PI)*RuneboundVisual;
                    Billboard(Index,Burst->Origin+Radial*Radius,.65f*Fade,(2.4f+Random*2.f)*Fade,
                        Burst->Rotation.RotateVector(FVector(-FMath::Sin(Angle),FMath::Cos(Angle),0.f)));
                    continue;
                }
                if(Burst&&Burst->bFinalToll)
                {
                    const float Life=1.1f+Random*1.1f;
                    if(!Burst->bHasOrigin||A<=0.f||A>=Life||I>=192){Quad(Index,FVector::ZeroVector,0.f);continue;}
                    const float Phase=I*2.399963f+Seed,Spread=5.f+(9.f+Random*23.f)*(1.f-FMath::Exp(-A*5.f));
                    const FVector World=Burst->Origin+FVector(FMath::Cos(Phase)*Spread,FMath::Sin(Phase)*Spread,A*(30.f+Random*50.f)-8.f);
                    const float Fade=(1.f-FMath::SmoothStep(.2f,1.f,A/Life))*FMath::SmoothStep(0.f,.02f,A);
                    Billboard(Index,World,(.3f+Random*.45f)*Fade,(I%4==0?8.f:1.1f)*Fade,FVector::UpVector);continue;
                }
                const bool Streak=I%5==0,Fleck=I%5>=3;
                const float Life=Streak?.48f+Random*.2f:Fleck?RuneboundHammer::HitMoteSeconds-(I%5)*.13f:1.05f+Random*.45f;
                if(I>=HitCount||!Burst||!Burst->bHasOrigin||A<=0.f||A>=Life)
                {Quad(Index,FVector(0.,0.,RuneboundHammer::HeadHeightCM),0.f);continue;}
                const float U=A/Life;
                const float Z=2.f*(I+.5f)/HitCount-1.f;
                const float Ring=FMath::Sqrt(FMath::Max(0.f,1.f-Z*Z));
                const float Angle=I*2.399963f+Seed;
                const FVector Direction=Burst->Rotation.RotateVector(FVector(FMath::Cos(Angle)*Ring,FMath::Sin(Angle)*Ring,Z));
                const float Speed=(Streak?190.f+Random*120.f:Fleck?55.f+Random*60.f:115.f+Random*90.f)*
                    (Destruction?1.25f:1.f)*(Detonation?2.5f:1.f);
                const float Drag=Streak?3.8f:Fleck?2.2f:2.8f;
                const float Travel=Speed*(1.f-FMath::Exp(-Drag*A))/Drag;
                const FVector Drift=Burst->Rotation.RotateVector(FVector(
                    FMath::Sin(Angle+A*1.6f)-FMath::Sin(Angle),FMath::Cos(Angle+A*1.3f)-FMath::Cos(Angle),0.f))*(Fleck?5.f:1.8f);
                const FVector World=Burst->Origin+Direction*Travel+Drift+
                    FVector::UpVector*((Fleck?20.f:8.f)*A-(Fleck?0.f:10.f)*A*A);
                const float Fade=FMath::SmoothStep(0.f,.018f,A)*(1.f-FMath::SmoothStep(Fleck?.2f:.35f,1.f,U));
                const float Strength=(Destruction?1.45f:Swift?1.15f:1.f)*(Detonation?1.8f:1.f)*Fade*RuneboundVisual;
                const float Width=(Streak?.4f+Random*.35f:Fleck?.3f+Random*.55f:.75f+Random*.8f)*Strength;
                const float Length=Streak?(.8f+(4.f+Random*5.f)*FMath::Exp(-A*5.f))*Strength:Width;
                Billboard(Index,World,Width,Length,Direction);
            }
        }
        for(int32 I=0;I<RuneboundHammer::SealQuadCapacity;++I)
        {
            const int32 Index=RuneboundHammer::AmbientMoteCapacity+RuneboundHammer::HitMoteCapacity*RuneboundHammer::HitBurstSlots+I;
            const int32 Slot=I/4,Stroke=I%4;
            const auto* Seal=FinalTollVisualMarks.IsValidIndex(Slot)?&FinalTollVisualMarks[Slot]:nullptr;
            const auto* SealCombat=Seal&&Seal->Target.IsValid()?Seal->Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
            if(!bFinalTollVisual||!Seal||!Seal->Target.IsValid()||Seal->Expires<=ServerNow||(SealCombat&&SealCombat->IsDead()))
            {Billboard(Index,Eye,0.f,0.f,FVector::UpVector);continue;}
            const FVector Center=Seal->Target->GetActorLocation()+Seal->LocalPoint;
            const float AgeOfSeal=float(ServerNow-Seal->Started);
            const float Fade=FMath::SmoothStep(0.f,.08f,AgeOfSeal)*FMath::Clamp(float(Seal->Expires-ServerNow)/.35f,0.f,1.f);
            const FVector Right=View.RotateVector(FVector::RightVector);
            const FVector Point=Center+Right*((Stroke%2?1.f:-1.f)*4.f)+FVector::UpVector*(Stroke>=2?9.f:-3.f);
            Billboard(Index,Point,.28f*Fade,(Seal->Complete?14.f:9.f)*Fade,FVector::UpVector);
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
}

void UProductionToolComponent::ClearRuneboundPresentation()
{
    for(const auto& MID:RuneboundRuneMIDs)if(IsValid(MID.Get()))MID->SetScalarParameterValue(TEXT("RuneAwake"),0.f);
    RuneboundRuneMIDs.Reset();RuneboundMoteAnchor.Reset();
    RuneboundHitBursts.Reset();FinalTollVisualMarks.Reset();FinalTollMarks.Reset();
    if(RuneboundAssetLoad)RuneboundAssetLoad->CancelHandle();RuneboundAssetLoad.Reset();
    if(RuneboundHud)RuneboundHud->DestroyComponent();RuneboundHud=nullptr;
    if(RuneboundMotes)RuneboundMotes->DestroyComponent();RuneboundMotes=nullptr;
    RuneboundMoteMID=nullptr;RuneboundMoteMaterial=nullptr;
}
