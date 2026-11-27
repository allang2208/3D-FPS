#pragma once
#include "../Skills/ColdSteelSkillRules.h"
namespace ColdSteelSkillPagePrivate
{
inline bool Additional(FName Id){return ColdSteelSkills::IsMeleeMastery(Id)||Id==TEXT("machineGunMastery")||Id==TEXT("shotgunMastery")||Id==TEXT("bowMastery")||Id==TEXT("heartPiercingArrow")||Id==TEXT("magicArrowRain")||Id==TEXT("elementalArrow")||Id==TEXT("illuminationArrow");}
}
