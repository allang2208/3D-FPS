#pragma once
#include "CoreMinimal.h"

/** Target-independent weapon panel. Damage type and source remain separate. */
struct FWeaponDamageParts
{
    double BasePhysical=0,BaseMagic=0,AddedPhysical=0,AddedMagic=0;
    double Base()const{return BasePhysical+BaseMagic;}
    double Additional()const{return AddedPhysical+AddedMagic;}
    double Total()const{return Base()+Additional();}
    FWeaponDamageParts Scaled(double Multiplier)const
    {return {BasePhysical*Multiplier,BaseMagic*Multiplier,AddedPhysical*Multiplier,AddedMagic*Multiplier};}
    // Apply the base receipt first, then the additional receipt, within remaining HP.
    FWeaponDamageParts LimitedTo(double Health)const
    {
        FWeaponDamageParts R;
        auto Take=[&](double Amount){const double V=FMath::Clamp(Amount,0.,FMath::Max(0.,Health));Health-=V;return V;};
        R.BasePhysical=Take(BasePhysical);R.BaseMagic=Take(BaseMagic);
        R.AddedPhysical=Take(AddedPhysical);R.AddedMagic=Take(AddedMagic);return R;
    }
};

/** One accepted contact, containing two independently calculated damage receipts. */
struct FWeaponDamageResult
{
    FWeaponDamageParts BeforeDefense,AfterDefense,Applied;
    bool bResolved=false,bCritical=false;
    bool HasAdditional()const{return BeforeDefense.Additional()>0;}
};
