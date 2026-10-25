// Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp
// Replace existing sprint lift branch inside the committed tool action, preserving other action consumers.
            if(SprintLift)
            {
                State.ActionVariant=TEXT("WarhammerSprintLift");
                Timed(EFPSBodyAction::Charge,Tool->Elapsed*Tool->HasteActionRate,WarhammerSprint::LiftSeconds,Tool->HasteActionRate);
            }
