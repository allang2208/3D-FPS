// Source/FPSGAME/Production/ProductionToolMotion.cpp
// Select complete Slash1 windup for Final Toll; preserve other motion and floor-contact consumers.
    if(bBluntCharging||bBluntReturningCharge)
    {
        if(bFinalTollHead)
            SampleMotion(TEXT("Slash1"),FinalTollHeavy::ChargeSource(BluntChargePoseSeconds()/WarhammerHeavy::ChargeSeconds));
        else SampleMotion(TEXT("HeavyCharge"),BluntChargePoseSeconds());
    }
