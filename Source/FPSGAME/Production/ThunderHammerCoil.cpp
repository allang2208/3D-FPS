#include "ThunderHammerCoil.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerRunes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "GameFramework/Actor.h"

bool ThunderHammerCoil::Installed(const FColdSteelItem* Item)
{
    if(!Item||Item->Definition!=ThunderHammer::Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item->Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Selected;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)
        &&(*Parts)->TryGetStringField(TEXT("grip"),Selected)&&Selected==Grip;
}

void ThunderHammerCoil::Commit(FColdSteelSkillShot& Shot,const FColdSteelItem* Item,const UColdSteelStatusModel* Profile)
{
    Shot.bHammerCoil=Profile&&Installed(Item);
    if(!Shot.bHammerCoil)return;
    // Keep this weapon's level/damage/runes through delayed strikes and weapon swaps.
    // A passive proc neither changes the saved skill level nor consumes a cast focus.
    Shot.HammerCoilLightning=Profile->LightningStats(FMath::Max(10,Profile->LightningProgress().Level),false);
    ThunderHammerRunes::Configure(Shot.HammerCoilLightning,Item);
    Shot.HammerCoilLightning.ElectrifyStacks=ThunderHammer::ElectrifyStacks;
}

void ThunderHammerCoil::Released(AActor* Source,const FColdSteelSkillShot& Shot,bool ReplacedHeavy)
{
    if(Source&&!ReplacedHeavy)Discharge(Source,Source->GetActorLocation(),Shot,RadiusCM,1);
}

void ThunderHammerCoil::Discharge(AActor* Source,const FVector& Center,const FColdSteelSkillShot& Shot,float Radius,int32 Bolts)
{
    if(!Source||!Source->HasAuthority()||!Shot.bHammerCoil)return;
    if(auto* Lightning=Source->FindComponentByClass<UFPSMeleeLightningComponent>())
        Lightning->QueueRandomLightning(Center,Radius,Shot.HammerCoilLightning,Bolts);
}
