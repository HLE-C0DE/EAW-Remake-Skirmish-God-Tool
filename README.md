# EAW Remake Skirmish God Tool

**Target Mod:** [STEAM-2794270450] Empire at War Remake 4.0
**Focus:** Skirmish Mode (Space)

## Overview
This utility automates unit availability and resource management for Skirmish mode. It converts Neutral/Underworld units to your elected faction, injects them into build rosters, and boosts Starbase income to ensure a high-intensity "sandbox" experience.

## Features
*   **Unit Conversion**: Converts Neutral/Underworld units to the selected faction.
*   **Roster Injection**: Automatically adds converted units to Shipyards (Frigates/Capitals), Starbases (Squadrons), or Research Facilities (Heroes).
*   **Availability**: Forces technological availability (Tech Level 1) for all injected units.
*   **Income Boost**: Increases Skirmish Starbase income to 100,000 credits per tick.
*   **Safety**: Automatically backs up and restores `Data/Xml` from a clean copy before applying changes.

## Usage
1.  Ensure the script `eaw_remake_skirmish_god.py` is located in the workshop content folder (`.../content/32470`).
2.  Run the script:
    ```bash
    python eaw_remake_skirmish_god.py
    ```
3.  Select your faction (1-4).
4.  Launch the game in Skirmish mode.

*Note: To reset changes, simply run the script again and exit, or let it restore the backup at the start of the next run.*
