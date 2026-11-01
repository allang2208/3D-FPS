#include "ThunderHammerStaticField.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerRunes.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

bool ThunderHammerStaticField::Installed(const FColdSteelItem* Item)
{
    if(!Item||Item->Definition!=ThunderHammer::Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item->Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Selected;
    if(Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))(*Parts)->TryGetStringField(TEXT("grip"),Selected);
    return Selected==Grip;
}

void ThunderHammerStaticField::Commit(FColdSteelSkillShot& Shot,const FColdSteelItem* Item)
{Shot.bHammerStaticField=Installed(Item);}

void ThunderHammerStaticField::Released(AActor* Source,const FColdSteelSkillShot& Shot,bool ReplacedHeavy)
{
    if(Source&&!ReplacedHeavy)Pulse(Source,Source->GetActorLocation(),Shot,RadiusCM,2);
}

void ThunderHammerStaticField::Pulse(AActor* Source,const FVector& Center,const FColdSteelSkillShot& Shot,float Radius,int32 Stacks)
{
    if(!Source||!Source->HasAuthority()||!Shot.bHammerStaticField)return;
    auto* World=Source->GetWorld();if(!World)return;
    ColdSteelAuthority::FScope Scope(ColdSteelAuthority::ForPawn(Cast<APawn>(Source)));
    TArray<FOverlapResult> Nearby;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(ThunderStaticField),false,Source);
    World->OverlapMultiByObjectType(Nearby,Center,FQuat::Identity,FCollisionObjectQueryParams::AllDynamicObjects,
        FCollisionShape::MakeSphere(Radius),Query);
    TSet<AActor*> Seen;
    for(const auto& Hit:Nearby)
    {
        auto* Target=Hit.GetActor();
        if(Seen.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,Source))continue;
        Seen.Add(Target);
        // A field pulse adds exactly its advertised stacks. It is not a new
        // weapon hit and cannot roll LeiMing, deal slam damage or gain mastery.
        // Five stacks still use the shared overload/echo receipt below.
        ThunderHammerRunes::ApplyStacks(Source,Target,Shot,Stacks);
    }
}
