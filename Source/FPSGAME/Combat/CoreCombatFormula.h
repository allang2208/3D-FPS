#pragma once
#include <algorithm>
#include <cmath>
#include <vector>

// World-122 combat-formulas.json + player/base.js + combat/defense-formula.js.
// Double precision and rounding order intentionally match JavaScript numbers.
namespace CoreCombatFormula
{
struct Attributes { double Str=10, Dex=10, Int=10, Con=10, Wis=10, Luck=10; };
struct Stats { double Atk, Def, Matk, Mdef, Crit, CritRes, AttackSpeed, Speed, MaxHp, MaxMp, StaminaRegen, MpRegen; };
inline double Round(double X) { return std::floor(X+.5); }
struct WeaponTerm { double Value, Base, PerEnhance; };
inline double Weapon(double Base,double Flat,double Level,const std::vector<WeaponTerm>& Terms)
{
    double Damage=Base+Level*Flat;
    for(const auto& T:Terms)Damage+=T.Value*(T.Base+T.PerEnhance*Level);
    return Round(Damage);
}
inline Stats Player(const Attributes& A,int Level=1)
{
    return {Round(10+A.Str*.05+A.Dex*.1),std::floor(A.Con*1.2+A.Str*.3),
        std::floor(A.Int*1.5+A.Wis*.5),std::floor(A.Wis*1.2+A.Int*.3),
        std::floor(2+A.Luck),std::floor(A.Con),
        1+A.Dex*.02,std::floor(130.528125+A.Dex*.05),100+A.Con*10+(Level-1)*10,
        100+A.Wis*10+A.Int*5+(Level-1)*10,1+A.Dex*.015,
        std::max(0.,Round((1+A.Wis*.08+A.Int*.02)*100)/100)};
}
inline Stats Enemy(const Attributes& A)
{
    Stats S=Player(A);S.Atk=Round(A.Str*.5+A.Dex*.5);S.Def=std::floor(A.Con*1.5+A.Str*.3);
    S.Matk=std::floor(A.Int*.5+A.Wis*.5);S.MaxHp=100+A.Con*5;return S;
}
inline double Defense(double Damage,double Def,bool Magic=false,double Penetration=0,double Shred=0,double Corrosion=1)
{
    if(Damage<=0)return Damage;
    if(Magic)Def=std::floor(Def*(1-std::clamp(Shred,0.,.95)));
    if(Penetration!=0)Def=std::floor(Def*(1-std::clamp(Penetration,0.,1.)));
    if(!Magic)Def=std::max(0.,std::floor(Def*Corrosion));
    return std::max(std::floor(Damage*(1-Def/(Def+60))),std::floor(Damage*.1));
}
inline double CriticalChance(double Chance,double Resistance) { return std::max(0.,Chance-Resistance); }
inline double CriticalDamage(double Damage,double Bonus) { return std::floor(Damage*(1+Bonus)); }
}
