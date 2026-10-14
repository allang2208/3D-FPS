#pragma once
#include "ColdSteelInventoryTypes.h"

namespace ColdSteelProfileRecovery
{
void LoadedAmmo(FColdSteelItem& Into,const FColdSteelItem& From);
inline void MartialCooldowns(FColdSteelProfile& Into,const FColdSteelProfile& From,float Age=0.f)
{
    if(From.MartialCooldownRevision<Into.MartialCooldownRevision)return;
    const bool Newer=From.MartialCooldownRevision>Into.MartialCooldownRevision;
    const float Whirlwind=FMath::Max(0.f,From.WhirlwindCooldown-Age);
    const float Uppercut=FMath::Max(0.f,From.SwordUppercutCooldown-Age);
    Into.WhirlwindCooldown=Newer?Whirlwind:FMath::Min(Into.WhirlwindCooldown,Whirlwind);
    Into.SwordUppercutCooldown=Newer?Uppercut:FMath::Min(Into.SwordUppercutCooldown,Uppercut);
    if(Newer)
    {
        Into.WhirlwindCooldownDuration=From.WhirlwindCooldownDuration;
        Into.SwordUppercutCooldownDuration=From.SwordUppercutCooldownDuration;
        Into.MartialCooldownRevision=From.MartialCooldownRevision;
    }
}

// Only these spells use the server cast RPC. Melee action clocks keep their existing owner.
inline void NetworkSpells(FColdSteelProfile& Into,const FColdSteelProfile& From,float Age=0.f)
{
    const auto Remaining=[Age](float Value,bool Reserved=false){return FMath::Max(0.f,Value-(Reserved?0.f:Age));};
    Into.FireballCooldown=Remaining(From.FireballCooldown,From.bFireballReserved);Into.FireballCooldownDuration=From.FireballCooldownDuration;
    Into.IceSpikeCooldown=Remaining(From.IceSpikeCooldown,From.bIceSpikeReserved);Into.IceSpikeCooldownDuration=From.IceSpikeCooldownDuration;
    Into.LightningCooldown=Remaining(From.LightningCooldown);Into.LightningCooldownDuration=From.LightningCooldownDuration;
    Into.HolyLightCooldown=Remaining(From.HolyLightCooldown);Into.HolyLightCooldownDuration=From.HolyLightCooldownDuration;
    Into.MeteorCooldown=Remaining(From.MeteorCooldown);Into.MeteorCooldownDuration=From.MeteorCooldownDuration;
    Into.FlameArmorCooldown=Remaining(From.FlameArmorCooldown);Into.FlameArmorCooldownDuration=From.FlameArmorCooldownDuration;
    Into.DragonBreathCooldown=Remaining(From.DragonBreathCooldown,From.bDragonBreathReserved);Into.DragonBreathCooldownDuration=From.DragonBreathCooldownDuration;
    Into.IceWallCooldown=Remaining(From.IceWallCooldown,From.bIceWallReserved);Into.IceWallCooldownDuration=From.IceWallCooldownDuration;
    Into.BlizzardCooldown=Remaining(From.BlizzardCooldown,From.bBlizzardReserved);Into.BlizzardCooldownDuration=From.BlizzardCooldownDuration;
    Into.bFireballReserved=From.bFireballReserved;
    Into.bIceSpikeReserved=From.bIceSpikeReserved;
    Into.bDragonBreathReserved=From.bDragonBreathReserved;
    Into.bIceWallReserved=From.bIceWallReserved;
    Into.bBlizzardReserved=From.bBlizzardReserved;
    Into.DragonBreathReservedMana=From.DragonBreathReservedMana;
    Into.IceWallReservedMana=From.IceWallReservedMana;
    Into.BlizzardReservedMana=From.BlizzardReservedMana;
    Into.ElectricCooldowns=From.ElectricCooldowns;Into.ElectricCooldownDurations=From.ElectricCooldownDurations;
    Into.ElectricReservedMana=From.ElectricReservedMana;
    for(auto& Pair:Into.ElectricCooldowns)Pair.Value=Remaining(Pair.Value,Into.ElectricReservedMana.Contains(Pair.Key));
}

inline bool InterruptedSpells(FColdSteelProfile& Clean,float MaxMana)
{
    const bool AbandonedFireball=Clean.bFireballReserved;Clean.bFireballReserved=false;
    const bool AbandonedIce=Clean.bIceSpikeReserved;Clean.bIceSpikeReserved=false;
    const bool AbandonedIceWall=Clean.bIceWallReserved;Clean.bIceWallReserved=false;
    if(AbandonedIceWall)
    {
        Clean.Mana=FMath::Min(MaxMana,Clean.Mana+Clean.IceWallReservedMana);
        Clean.IceWallCooldown=Clean.IceWallCooldownDuration=0;
    }
    Clean.IceWallReservedMana=0;
    const bool AbandonedBlizzard=Clean.bBlizzardReserved;Clean.bBlizzardReserved=false;
    if(AbandonedBlizzard)
    {
        Clean.Mana=FMath::Min(MaxMana,Clean.Mana+Clean.BlizzardReservedMana);
        Clean.BlizzardCooldown=Clean.BlizzardCooldownDuration=0;
    }
    Clean.BlizzardReservedMana=0;
    const bool AbandonedElectric=!Clean.ElectricReservedMana.IsEmpty();
    for(const auto& Reserved:Clean.ElectricReservedMana)
    {
        Clean.Mana=FMath::Min(MaxMana,Clean.Mana+Reserved.Value);
        Clean.ElectricCooldowns.Add(Reserved.Key,0);Clean.ElectricCooldownDurations.Add(Reserved.Key,0);
    }
    Clean.ElectricReservedMana.Reset();
    const bool AbandonedDragon=Clean.bDragonBreathReserved;
    if(AbandonedDragon)
    {
        Clean.Mana=FMath::Min(MaxMana,Clean.Mana+Clean.DragonBreathReservedMana);
        Clean.DragonBreathCooldown=Clean.DragonBreathCooldownDuration=0;
    }
    Clean.bDragonBreathReserved=false;Clean.DragonBreathReservedMana=0;
    const bool AbandonedQuick=Clean.bQuickCombatReserved||Clean.QuickCombatCooldown>0.f||Clean.QuickCombatCooldownDuration>0.f;
    Clean.bQuickCombatReserved=false;Clean.QuickCombatCooldown=Clean.QuickCombatCooldownDuration=0.f;
    return AbandonedFireball||AbandonedIce||AbandonedIceWall||AbandonedBlizzard||AbandonedElectric||AbandonedDragon||AbandonedQuick;
}

// A slow profile mirror must not rewind newer station RPC progress for the same paid job.
inline void StationProgress(FColdSteelProfile& Into,const FColdSteelProfile& Other)
{
    auto& Forge=Into.ForgeJob;const auto& PreviousForge=Other.ForgeJob;
    if(!Forge.Id.IsEmpty()&&Forge.Id==PreviousForge.Id)
    {
        if(PreviousForge.bFinished&&!Forge.bFinished)Forge=PreviousForge;
        Forge.Hits=FMath::Max(Forge.Hits,PreviousForge.Hits);
    }
    auto& Assembly=Into.GunAssemblyJob;const auto& PreviousAssembly=Other.GunAssemblyJob;
    if(!Assembly.Id.IsEmpty()&&Assembly.Id==PreviousAssembly.Id)
    {
        if(PreviousAssembly.bFinished&&!Assembly.bFinished)Assembly=PreviousAssembly;
        for(int32 I=0;I<Assembly.Scores.Num()&&I<30;++I)
            if(!(Assembly.InstalledMask&(1<<I))&&(PreviousAssembly.InstalledMask&(1<<I))&&PreviousAssembly.Scores.IsValidIndex(I))
                Assembly.Scores[I]=PreviousAssembly.Scores[I];
        Assembly.InstalledMask|=PreviousAssembly.InstalledMask;
        for(int32 I=0;I<Assembly.Misses.Num();++I)if(PreviousAssembly.Misses.IsValidIndex(I))
            Assembly.Misses[I]=FMath::Max(Assembly.Misses[I],PreviousAssembly.Misses[I]);
        if(PreviousAssembly.CalibrationTime>Assembly.CalibrationTime)
        {
            Assembly.CalibrationSeconds=PreviousAssembly.CalibrationSeconds;
            Assembly.CalibrationTime=PreviousAssembly.CalibrationTime;
            Assembly.CalibrationError=PreviousAssembly.CalibrationError;
        }
    }
    auto& Wood=Into.WoodworkingJob;const auto& PreviousWood=Other.WoodworkingJob;
    if(!Wood.Id.IsEmpty()&&Wood.Id==PreviousWood.Id&&
        ((PreviousWood.bFinished&&!Wood.bFinished)||(!Wood.bFinished&&PreviousWood.Elapsed>Wood.Elapsed)))Wood=PreviousWood;
}
}
