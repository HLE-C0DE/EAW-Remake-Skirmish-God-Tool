
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import sys

# ============================================================
# DEBUG MODE: Set to True to see detailed unit conversion logs
# ============================================================
DEBUG = False

# Configuration
# Path to the specific mod folder we are targeting
# Since script is now in root (32470), we target the subdirectory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_FOLDER_NAME = "2794270450"
WORKING_DIR = os.path.join(SCRIPT_DIR, MOD_FOLDER_NAME)

# Fallback in case __file__ fails or we want hardcoded absolute assurance
if not os.path.exists(WORKING_DIR):
    WORKING_DIR = r"G:\SteamLibrary\steamapps\workshop\content\32470\2794270450"
    SCRIPT_DIR = os.path.dirname(WORKING_DIR)

# Dynamically find or create backup directory
def find_or_create_backup():
    """Search for existing backup folder (- copy or - copie) or create one."""
    parent_dir = SCRIPT_DIR
    
    # Search for existing backups
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        if os.path.isdir(item_path):
            # Check if it matches pattern: "2794270450 - copy" or "2794270450 - copie"
            if item.lower().startswith(MOD_FOLDER_NAME.lower()):
                if " - copy" in item.lower() or " - copie" in item.lower():
                    print(f"Found existing backup: {item}")
                    return item_path
    
    # No backup found, create default one
    backup_name = f"{MOD_FOLDER_NAME} - copy"
    backup_path = os.path.join(parent_dir, backup_name)
    print(f"No backup found. Will create: {backup_name}")
    return backup_path

BACKUP_DIR = find_or_create_backup()

XML_DIR = os.path.join(WORKING_DIR, "Data", "Xml")

# Faction Mapping
FACTIONS = {
    "1": ("Republic", r"Republic"),
    "2": ("CIS", r"CIS|Confederacy"),
    "3": ("Rebellion", r"Rebel"),
    "4": ("Empire", r"Empire")
}

def print_header(msg):
    print(f"\n{'='*60}")
    print(f" {msg}")
    print(f"{'='*60}")

def restore_backup():
    print_header("Step 1: Restoring from Clean Backup")
    print(f"Using backup: {BACKUP_DIR}")
    
    if not os.path.exists(BACKUP_DIR):
        print(f"Backup does not exist yet. Creating initial backup from current state...")
        print(f"Copying {WORKING_DIR} -> {BACKUP_DIR}...")
        try:
            shutil.copytree(WORKING_DIR, BACKUP_DIR)
            print("Initial backup created successfully!")
            print("NOTE: This backup will be used for all future restores.")
            print("      To refresh the backup, delete it and run the script again.")
            return  # Don't restore on first run, just create backup
        except Exception as e:
            print(f"ERROR: Failed to create backup: {e}")
            sys.exit(1)
        
    print(f"Mirroring {BACKUP_DIR} -> {WORKING_DIR}...")
    cmd = ['robocopy', BACKUP_DIR, WORKING_DIR, '/MIR', '/NFL', '/NDL', '/NJH', '/NJS', '/NC', '/NS', '/NP']
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode > 7:
        print(f"CRITICAL ERROR: Robocopy failed with code {result.returncode}")
        sys.exit(1)
    print("Restore completed.")

def apply_fixes():
    print_header("Step 2: Applying Critical XML Fixes")
    
    replacements = [
        (os.path.join(XML_DIR, "Upgrades", "Vanilla.xml"), r'^\s+<\?xml', r'<?xml'),
        (os.path.join(XML_DIR, "Upgrades", "Skirmish", "Space", "Republic", "Mines_Defense.xml"), r'^\s+<\?xml', r'<?xml'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Space_First_Order_Supremacy.xml"), r'</Reserve_Spaned_Units_Teh_0>', r'</Reserve_Spawned_Units_Tech_0>'),
        (os.path.join(XML_DIR, "Buildings", "Ground", "Skirmish_Rework", "Mine.xml"), r'(<Affiliation>CIS</Affiliation>)\s*(<GroundBuildable Name="Republic_Mineral_Processor">)', r'\1\n\t</GroundBuildable>\n\n\t\2'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Empire_181st_Fighter_Wing.XML"), r'<181st>', r'<_181st>'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Empire_181st_Fighter_Wing.XML"), r'</181st>', r'</_181st>'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Empire_181st_Fighter_Wing_BU.xml"), r'<181st>', r'<_181st>'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Empire_181st_Fighter_Wing_BU.xml"), r'</181st>', r'</_181st>'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Minors_CSA_Tagge.XML"), r'<\?xml version="1.0"\?>\s*<80s_Visor_Man>', r'<?xml version="1.0"?>\n<_80s_Visor_Man>'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Minors_CSA_Tagge.XML"), r'</80s_Visor_Man>', r'</_80s_Visor_Man>'),
        (os.path.join(XML_DIR, "Units", "Space", "Units_Hero_Minors_CSA_Tagge.XML"), r'^<80s_Visor_Man>', r'<?xml version="1.0"?>\n<_80s_Visor_Man>')
    ]

    fixed_count = 0
    for file_path, pattern, replacement in replacements:
        if not os.path.exists(file_path): continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(new_content)
                fixed_count += 1
        except Exception as e: print(f"Error fixing {file_path}: {e}")

    print(f"Applied fixes to {fixed_count} locations.")

# --- SMART MODIFIER ---
# Tags to remove from Neutral/Underworld units (all prerequisites except Tech_Level)
PREREQUISITE_TAGS = [
    "Required_Special_Structures",
    "Required_Planets",
    "Required_Orbiting_Units",
    "Tactical_Build_Prerequisites"
]

def process_xml_content(content, faction_name, faction_pattern, file_path):
    """
    Parses top-level blocks via Regex (simulating XML traversal) and injects/updates tags.
    Also converts Neutral/Underworld units to the selected faction for skirmish mode.
    Returns: (modified_content, list of converted units, conversion_stats)
    """
    # FILE-LEVEL EXCLUSION: Skip files with OTHER major faction keywords in name
    # e.g., if faction_name="Republic", skip files with "_Rebel_", "_Empire_", "_CIS_"
    # This prevents modifying Republic variants inside other faction files
    other_factions = {
        "Republic": ["Rebel", "Empire", "CIS", "Confederacy"],
        "Empire": ["Rebel", "Republic", "CIS", "Confederacy"],
        "Rebellion": ["Empire", "Republic", "CIS", "Confederacy"],  # Rebellion matches Rebel
        "CIS": ["Rebel", "Empire", "Republic"]
    }
    
    # EXCLUDED FILES: Critical system files that should NEVER be converted or modified
    # Modifying these breaks the AI because they are base classes for ALL factions
    EXCLUDED_FILES = [
        "_Default_Base.xml",
        "_Attrition.xml",
        "BuildPads.xml",  # Critical: Fixes AI economy/defense construction
        "Research_Facilities_Default.xml",  # Critical: Fixes AI tech progression
        "Shipyards_Default.xml",  # Critical: Fixes AI ship production
        "Units_Space_Neutral_Freighters.xml", # Preserves base freighter classes
        "Units_Space_Neutral_CEC_YT.xml"      # Preserves base YT classes
    ]

    filename = os.path.basename(file_path)
    if filename in EXCLUDED_FILES:
        return content, [], {
            'squadrons': 0,
            'frigates': 0,
            'capitals': 0,
            'heroes': 0,
            'research': 0,
            'neutral_converted': 0,
            'faction_modified': 0,
            'units_with_cheats': []
        }

    if faction_name in other_factions:
        for other_faction in other_factions[faction_name]:
            # Check for faction keyword with separator (avoid matching "Old_Republic", "Old_Empire")
            # Match patterns like "_Rebel_", "_Empire_", etc.
            if re.search(fr'(?<!Old)[_\\]{other_faction}[_\\]', filename, re.IGNORECASE):
                # This file belongs to another faction - skip entirely
                return content, [], {
                    'squadrons': 0,
                    'frigates': 0,
                    'capitals': 0,
                    'heroes': 0,
                    'research': 0,
                    'neutral_converted': 0,
                    'faction_modified': 0,
                    'units_with_cheats': []
                }
    
    # CHEATS CONFIG: Time set to "1" to avoid game logic erors (infinity/disabled)
    # CHEATS CONFIG: Cost disabled, but Time/Limits enabled as requested
    CHEATS = {
        # "Build_Cost_Credits": "1",
        # "Tactical_Build_Cost_Multiplayer": "1",
        "Build_Time_Seconds": "1",
        "Tactical_Build_Time_Seconds": "1",
        "Population_Value": "0",  # Pop remains 0
        "Build_Limit_Current_Per_Player": "-1",
        "Build_Limit_Lifetime_Per_Player": "-1",
        "Build_Max_Instances_Per_Planet": "-1"
    }

    types = "SpaceUnit|GroundUnit|Structure|SpaceBuildable|GroundBuildable|UpgradeObject|UniqueUnit|HeroUnit|Squadron|GroundCompany"
    block_pattern = re.compile(fr'(<({types})\b[^>]*>)(.*?)(</\2>)', re.DOTALL | re.IGNORECASE)
    
    converted_units = []  # Track converted units for shipyard injection
    conversion_stats = {
        'squadrons': 0,
        'frigates': 0,
        'capitals': 0,
        'heroes': 0,
        'research': 0,
        'neutral_converted': 0,
        'faction_modified': 0,
        'units_with_cheats': []  # List of (unit_name, unit_type) that had cheats applied
    }
    
    def modify_block(match):
        start_tag = match.group(1)
        tag_type = match.group(2)
        inner_content = match.group(3)
        end_tag = match.group(4)
        
        # Check if this is a Neutral or Underworld unit (for skirmish mode conversion)
        is_neutral_or_underworld = bool(re.search(r'<Affiliation>.*?(Neutral|Underworld).*?</Affiliation>', inner_content, re.IGNORECASE | re.DOTALL))
        
        # Check if the filename or path contains a faction identifier (to skip faction-specific files)
        # Examples to SKIP: 
        #   - \Empire\Air_LAAT.xml (directory has Empire)
        #   - Units_Space_Neutral_CIS_* (filename has _CIS_)
        #   - Units_Hero_Republic_* (filename has _Republic_)
        # Examples to CONVERT:
        #   - Units_Space_Neutral_Hapan_* (no main faction)
        #   - Units_Hero_Underworld_* (no main faction)
        # Exclude Old_Republic, Old_Empire etc using negative look behind
        # We ensure the separator (\ or _) is NOT preceded by "Old"
        faction_keywords = r'(?<!Old)(\\|_)(Republic|Empire|Rebel|CIS|Confederacy)(\\|_|\\.|_)'
        file_has_faction = bool(re.search(faction_keywords, file_path, re.IGNORECASE))
        
        # Only convert truly neutral/underworld units (not faction-specific variants or files in faction directories)
        should_convert_neutral = is_neutral_or_underworld and not file_has_faction
        
        # SPECIAL HANDLING FOR UPGRADEOBJECTS:
        # UpgradeObjects don't have <Affiliation> tags - they're organized by directory
        # Check if this is an UpgradeObject in a faction-specific directory
        is_upgrade_object = tag_type.lower() == "upgradeobject"
        upgrade_in_faction_dir = False
        if is_upgrade_object:
            # Check if file path contains faction-specific directory
            # e.g., /Upgrades/Skirmish/Space/Republic/ or /Upgrades/GC/Republic/
            if faction_name.lower() in file_path.lower():
                upgrade_in_faction_dir = True
        
        # UNIVERSAL UNIT NAME SUFFIX FILTER: Skip units with OTHER faction suffixes
        # This applies to ALL block types (units, buildings, structures, upgrades)
        # Extract unit name
        name_match = re.search(r'Name="([^"]+)"', start_tag, re.IGNORECASE)
        unit_name = name_match.group(1) if name_match else None
        
        if unit_name:
            # Map factions to their common suffixes/keywords
            faction_keywords_map = {
                "Republic": ["Republic", "Rep"],
                "Empire": ["Empire", "E"],
                "Rebellion": ["Rebel", "R"],
                "CIS": ["CIS", "Confederacy"]
            }
            
            # Get other faction keywords (not the selected one)
            other_keywords = []
            for fac, keywords in faction_keywords_map.items():
                if fac != faction_name:
                    other_keywords.extend(keywords)
            
            # Add additional faction/group keywords
            other_keywords.extend(["U", "Underworld", "HC", "Cartels", "CSA", "Warlords", "Hapan", "Mand", "Mandalorian", "H", "S", "Sith", "Naboo"])
            
            # Check if this unit has an other-faction keyword ANYWHERE in the name
            # Look for keywords as standalone segments (between underscores or at start/end)
            has_other_faction_keyword = False
            for keyword in other_keywords:
                # Check for keyword as:
                # - At start: "CIS_Something"
                # - In middle: "Something_CIS_Something"  
                # - At end: "Something_CIS"
                patterns = [
                    f"^{keyword}_",      # Starts with keyword_
                    f"_{keyword}_",      # Contains _keyword_
                    f"_{keyword}$"       # Ends with _keyword
                ]
                for pattern in patterns:
                    if re.search(pattern, unit_name, re.IGNORECASE):
                        has_other_faction_keyword = True
                        break
                if has_other_faction_keyword:
                    break
            
            # Skip this unit - it belongs to another faction
            if has_other_faction_keyword:
                return match.group(0)
        
        # STRICT BLOCK-LEVEL MATCHING: Only modify this block if:
        # 1. It's a neutral/underworld unit eligible for conversion, OR
        # 2. This specific block has the selected faction's affiliation tag, OR
        # 3. It's an UpgradeObject in the selected faction's directory
        block_matches = False
        if should_convert_neutral:
            # Convert truly Neutral/Underworld units to selected faction for skirmish mode
            block_matches = True
        elif is_upgrade_object and upgrade_in_faction_dir:
            # UpgradeObject in faction-specific directory - process it
            block_matches = True
        elif re.search(fr"<Affiliation>.*{faction_pattern}.*</Affiliation>", inner_content, re.IGNORECASE):
            # This block specifically has the selected faction - modify it
            block_matches = True
        
        if not block_matches:
            return match.group(0)
            
        new_inner = inner_content
        
        # If this is a truly Neutral/Underworld unit and we have a specific faction selected, convert it
        if should_convert_neutral:
            conversion_stats['neutral_converted'] += 1
            
            # Extract CategoryMask to determine shipyard type
            category_match = re.search(r'<CategoryMask>([^<]+)</CategoryMask>', inner_content, re.IGNORECASE)
            category_mask = category_match.group(1) if category_match else ""
            
            # Only track SpaceUnit, Squadron, and Hero types (NOT SpaceBuildable/buildings)
            unit_type = tag_type.lower()
            valid_types = ["spaceunit", "squadron", "genericherounit", "herounit", "uniqueunit"]
            
            if unit_name and unit_type in valid_types:
                # Filter out non-buildable units (DUMMY structures, Garrison units, etc.)
                # Added extensive filter for "junk" objects like Crates, Ammo, Spawners, Debuffs, etc.
                non_buildable_keywords = r'DUMMY|ORBITAL|DELETE_STRUCTURE|UPGRADE|DOWNGRADE|_Garrison(_|$)|_G(_|$)|Cost|UC_|Crate|Container|Ammo|Spawner|Debuff|Penalty|Death|Walker|Trooper|Infantry|Prop|Structure|Test|Marker|Loot|Treasure'
                if re.search(non_buildable_keywords, unit_name, re.IGNORECASE):
                    # Skip this unit - it's not meant to be buildable by players
                    pass
                else:
                    # Separate Squadron (goes to Starbase) from SpaceUnit (goes to Shipyard)
                    if unit_type == "squadron":
                        # Squadron always goes to Starbase (all levels)
                        converted_units.append((unit_name, "squadron"))
                        conversion_stats['squadrons'] += 1
                    else:
                        # SpaceUnit goes to Frigate or Capital Shipyard
                        # Heroes/Uniques go to Research Facility as requested by user
                        if unit_type in ["genericherounit", "herounit", "uniqueunit"]:
                             converted_units.append((unit_name, "research"))
                             conversion_stats['heroes'] += 1
                        else:
                             # Fallback check for capital ships
                             is_capital = bool(re.search(r'Capital|Destroyer|Cruiser|Carrier|Battleship|Dreadnought', category_mask, re.IGNORECASE))
                             converted_units.append((unit_name, "capital" if is_capital else "frigate"))
                             if is_capital:
                                 conversion_stats['capitals'] += 1
                             else:
                                 conversion_stats['frigates'] += 1
            
            # Change affiliation to the selected faction
            affiliation_regex = re.compile(r'(<Affiliation>).*?(</Affiliation>)', re.IGNORECASE | re.DOTALL)
            new_inner = affiliation_regex.sub(fr'\g<1>{faction_name}\g<2>', new_inner, count=1)
            
            # Use correct skirmish shipyard names
            faction_shipyard = f"{faction_name}_Frigate_Shipyard" # Default
            if faction_name == "Empire": faction_shipyard = "E_Frigate_Shipyard"
            elif faction_name == "Rebel": faction_shipyard = "R_Frigate_Shipyard"
            elif faction_name == "CIS": faction_shipyard = "CIS_Frigate_Shipyard"
            elif faction_name == "Republic": faction_shipyard = "Republic_Frigate_Shipyard"
            
            # Check if tag exists
            if re.search(r'<Required_Special_Structures>', inner_content, re.IGNORECASE):
                 # Replace existing
                structures_regex = re.compile(r'(<Required_Special_Structures>).*?(</Required_Special_Structures>)', re.IGNORECASE | re.DOTALL)
                new_inner = structures_regex.sub(f'<Required_Special_Structures>{faction_shipyard}</Required_Special_Structures>\n\t\t', new_inner)
            else:
                # Inject new tag after Affiliation
                affiliation_inject_regex = re.compile(r'(</Affiliation>)', re.IGNORECASE)
                new_inner = affiliation_inject_regex.sub(fr'\1\n\t\t<Required_Special_Structures>{faction_shipyard}</Required_Special_Structures>', new_inner, count=1)
            
            # Remove other build prerequisites (but keep Tech_Level and Required_Star_Base_Level)
            for prereq_tag in PREREQUISITE_TAGS:
                if prereq_tag != "Required_Special_Structures":  # Skip, we already handled it above
                    prereq_regex = re.compile(fr'<{prereq_tag}>.*?</{prereq_tag}>\s*', re.IGNORECASE | re.DOTALL)
                    new_inner = prereq_regex.sub('', new_inner)
            
            # FORCE Level 5 Starbase Requirement for Converted Squadrons/Neutral Units (RP style)
            if should_convert_neutral:
                 # Update or Inject Required_Star_Base_Level -> 5
                 level_regex = re.compile(r'(<Required_Star_Base_Level>)\s*\d+\s*(</Required_Star_Base_Level>)', re.IGNORECASE)
                 if level_regex.search(new_inner):
                     new_inner = level_regex.sub(r'\g<1>5\g<2>', new_inner)
                 else:
                     new_inner += '\n\t\t<Required_Star_Base_Level>5</Required_Star_Base_Level>'
            
            # Change Tech_Level from ANY to 1 (enabled) for converted units to ensure availability
            tech_level_regex = re.compile(r'(<Tech_Level>).*?(</Tech_Level>)', re.IGNORECASE)
            if tech_level_regex.search(new_inner):
                new_inner = tech_level_regex.sub(r'\g<1>1\g<2>', new_inner)
            else:
                new_inner += '\n\t\t<Tech_Level>1</Tech_Level>'
            
            # Force Build Tab and Unlock
            if re.search(r'<Build_Tab_Space_Units>', new_inner, re.IGNORECASE):
                new_inner = re.sub(r'(<Build_Tab_Space_Units>).*?(</Build_Tab_Space_Units>)', r'\g<1>Yes\g<2>', new_inner, flags=re.IGNORECASE)
            else:
                new_inner += '\n\t\t<Build_Tab_Space_Units>Yes</Build_Tab_Space_Units>'

            if re.search(r'<Build_Initially_Locked>', new_inner, re.IGNORECASE):
                new_inner = re.sub(r'(<Build_Initially_Locked>).*?(</Build_Initially_Locked>)', r'\g<1>No\g<2>', new_inner, flags=re.IGNORECASE)
            else:
                  new_inner += '\n\t\t<Build_Initially_Locked>No</Build_Initially_Locked>'
        else:
            # Not a neutral conversion, just a regular faction modification
            conversion_stats['faction_modified'] += 1
        
        # Apply standard cheats to all matching units
        # Skip build limits for Research/Upgrades/UpgradeObject (they don't make sense for technologies)
        is_research_or_upgrade = bool(re.search(r'(Research|Upgrades)', file_path, re.IGNORECASE)) or tag_type.lower() == "upgradeobject"
        
        # Extract unit name for debug tracking
        name_match = re.search(r'Name="([^"]+)"', start_tag, re.IGNORECASE)
        unit_name = name_match.group(1) if name_match else "Unknown"
        
        # Track that this unit had cheats applied
        conversion_stats['units_with_cheats'].append(unit_name)
        
        for tag, value in CHEATS.items():
            final_value = value
            
            # Special handling for Research/Upgrades
            if is_research_or_upgrade:
                if tag == "Build_Limit_Lifetime_Per_Player":
                    final_value = "1" # Force limit of 1 for research
                elif tag.startswith("Build_Limit"):
                    continue # Skip other build limit tags for research
                
            tag_regex = re.compile(fr'(<{tag}>)(.*?)(</{tag}>)', re.IGNORECASE | re.DOTALL)
            
            if tag_regex.search(new_inner):
                # FIX: Use \g<1> and \g<3> to avoid ambiguity with numeric values
                new_inner = tag_regex.sub(fr'\g<1>{final_value}\g<3>', new_inner)
            else:
                new_inner += f"\n\t\t<{tag}>{final_value}</{tag}>"
                
        return f"{start_tag}{new_inner}{end_tag}"

    new_content = block_pattern.sub(modify_block, content)
    return new_content, converted_units, conversion_stats

def inject_units_into_shipyard_rosters(faction_name, converted_units):
    """
    Injects converted Neutral/Underworld unit names into the faction's shipyard/starbase build rosters.
    
    Args:
        faction_name: Selected faction (Republic, CIS, Empire, Rebellion)
        converted_units: List of (unit_name, unit_type) tuples where unit_type is "squadron", "frigate", or "capital"
    """
    if not converted_units:
        return
    
    # Map faction names to file paths and build location names
    faction_config = {
        "Republic": {
            "shipyard_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Republic/Shipyards.xml"),
            "starbase_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Republic/Starbases.xml"),
            "research_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Republic/Research_Facilities.xml"),
            "frigate_name": "Republic_Frigate_Shipyard",
            "capital_name": "Republic_Capital_Shipyard",
            "starbase_name": "Skirmish_Republic_Star_Base_1",
            "research_name": "Republic_Research_Facility"
        },
        "Empire": {
            "shipyard_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Empire/Shipyards.xml"),
            "starbase_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Empire/Starbases.xml"),
            "research_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Empire/Research_Facilities.xml"),
            "frigate_name": "E_Frigate_Shipyard",
            "capital_name": "E_Capital_Shipyard",
            "starbase_name": "Skirmish_Empire_Star_Base_1",
            "research_name": "Empire_Research_Facility"
        },
        "Rebellion": {
            "shipyard_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Rebel/Shipyards.xml"),
            "starbase_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Rebel/Starbases.xml"),
            "research_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Rebel/Research_Facilities.xml"),
            "frigate_name": "R_Frigate_Shipyard",
            "capital_name": "R_Capital_Shipyard",
            "starbase_name": "Skirmish_Rebel_Star_Base_1",
            "research_name": "Rebel_Research_Facility"
        },
        "CIS": {
            "shipyard_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/CIS/Shipyards.xml"),
            "starbase_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/CIS/Starbases.xml"),
            "research_path": os.path.join(XML_DIR, "Buildings/Space/Skirmish/CIS/Research_Facilities.xml"),
            "frigate_name": "CIS_Frigate_Shipyard",
            "capital_name": "CIS_Capital_Shipyard",
            "starbase_name": "Skirmish_CIS_Star_Base_1",
            "research_name": "CIS_Research_Facility"
        }
    }
    
    config = faction_config.get(faction_name)
    if not config:
        return
    
    # Categorize units by type
    squadron_units = [name for name, unit_type in converted_units if unit_type == "squadron"]
    frigate_units = [name for name, unit_type in converted_units if unit_type == "frigate"]
    capital_units = [name for name, unit_type in converted_units if unit_type == "capital"]
    research_units = [name for name, unit_type in converted_units if unit_type == "research"]
    
    # Remove duplicates
    squadron_units = list(set(squadron_units))
    frigate_units = list(set(frigate_units))
    capital_units = list(set(capital_units))
    research_units = list(set(research_units))
    
    print(f"\nInjecting {len(squadron_units)} squadrons (Starbase), {len(frigate_units)} frigates, {len(capital_units)} capitals, and {len(research_units)} heroes into {faction_name} rosters...")
    
    # Inject Squadrons into Starbase (ONLY Level 5 as requested by user for RP)
    if squadron_units:
        try:
            with open(config["starbase_path"], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find Skirmish StarBase Level 5 definitions in the file
            # e.g., <StarBase Name="Skirmish_Republic_Star_Base_5"> ... </StarBase>
            starbase_pattern = re.compile(r'(<StarBase Name="Skirmish_.*?_Star_Base_5">)(.*?)(</StarBase>)', re.IGNORECASE | re.DOTALL)
            
            def inject_into_starbase(match):
                sb_start = match.group(1)
                sb_inner = match.group(2)
                sb_end = match.group(3)
                
                # Check if it has a buildable object list
                roster_pattern = re.compile(r'(<Tactical_Buildable_Objects_Multiplayer>)(.*?)(</Tactical_Buildable_Objects_Multiplayer>)', re.IGNORECASE | re.DOTALL)
                
                if roster_pattern.search(sb_inner):
                     # Inject units into existing list
                     # Check which units are already present to avoid duplicates
                     existing_roster = roster_pattern.search(sb_inner).group(2)
                     units_to_add = [u for u in squadron_units if u not in existing_roster]
                     
                     if units_to_add:
                         injection_str = "\n\t\t\t\t" + ",\n\t\t\t\t".join(units_to_add) + ","
                         new_sb_inner = roster_pattern.sub(fr'\g<1>\g<2>{injection_str}\g<3>', sb_inner)
                         return f"{sb_start}{new_sb_inner}{sb_end}"
                
                return match.group(0) # Return unchanged if no roster found or no units needed
            
            new_content = starbase_pattern.sub(inject_into_starbase, content)
            
            if new_content != content:
                with open(config["starbase_path"], 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Successfully injected squadrons into Starbase Level 5 in {config['starbase_path']}")
            else:
                print(f"Warning: Could not find suitable Starbase Level 5 blocks or rosters in {config['starbase_path']}")
                
        except Exception as e:
            print(f"Error injecting into Starbase: {e}")
    
    # Inject Frigates and Capitals into Shipyards
    try:
        with open(config["shipyard_path"], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Inject units into Frigate Shipyard
        if frigate_units:
            frigate_pattern = rf'(<SpaceBuildable Name="{config["frigate_name"]}">.*?<Tactical_Buildable_Objects_Multiplayer>)(.*?)(</Tactical_Buildable_Objects_Multiplayer>)'
            def inject_frigate(match):
                start, roster, end = match.groups()
                unit_list = ",\n\t\t\t\t" + ",\n\t\t\t\t".join(frigate_units)
                return f"{start}{roster}{unit_list}\n\t\t\t{end}"
            
            content = re.sub(frigate_pattern, inject_frigate, content, flags=re.DOTALL | re.IGNORECASE)
        
        # Inject units into Capital Shipyard
        if capital_units:
            capital_pattern = rf'(<SpaceBuildable Name="{config["capital_name"]}">.*?<Tactical_Buildable_Objects_Multiplayer>)(.*?)(</Tactical_Buildable_Objects_Multiplayer>)'
            def inject_capital(match):
                start, roster, end = match.groups()
                unit_list = ",\n\t\t\t\t" + ",\n\t\t\t\t".join(capital_units)
                return f"{start}{roster}{unit_list}\n\t\t\t{end}"
            
            content = re.sub(capital_pattern, inject_capital, content, flags=re.DOTALL | re.IGNORECASE)
        
        with open(config["shipyard_path"], 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully injected units into {config['shipyard_path']}")
        
    except Exception as e:
        print(f"Error injecting units into shipyard rosters: {e}")

    # Inject heroes into Research Facility
    if research_units and "research_path" in config:
        try:
            with open(config["research_path"], 'r', encoding='utf-8') as f: content_res = f.read()
            
            # Pattern for research facility roster
            res_pattern = rf'(<SpaceBuildable Name="{config["research_name"]}">.*?<Tactical_Buildable_Objects_Multiplayer>)(.*?)(</Tactical_Buildable_Objects_Multiplayer>)'
            
            def inject_res(match):
                start, roster, end = match.groups()
                # Check for existing units to avoid dupes logic could go here, but simple join is fast
                unit_list = ",\n\t\t\t\t" + ",\n\t\t\t\t".join(research_units)
                return f"{start}{roster}{unit_list}\n\t\t\t{end}"
            
            if re.search(res_pattern, content_res, re.DOTALL | re.IGNORECASE):
                content_res = re.sub(res_pattern, inject_res, content_res, flags=re.DOTALL | re.IGNORECASE)
                with open(config["research_path"], 'w', encoding='utf-8') as f: f.write(content_res)
                print(f"Successfully injected {len(research_units)} heroes into Research Facility")
            else:
                print(f"Warning: Could not find Research roster for {config['research_name']}")
                
        except Exception as e:
            print(f"Error injecting into Research Facility: {e}")

def boost_starbase_income(faction_name):
    """
    Injects massive income into the selected faction's Skirmish Starbase.
    """
    faction_config = {
        "Republic": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Republic/Starbases.xml"),
        "Empire": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Empire/Starbases.xml"),
        "Rebellion": os.path.join(XML_DIR, "Buildings/Space/Skirmish/Rebel/Starbases.xml"),
        "CIS": os.path.join(XML_DIR, "Buildings/Space/Skirmish/CIS/Starbases.xml")
    }

    # TARGET ALL FACTIONS to ensure AI fights back with equal resources
    targets = list(faction_config.values()) 
   
    if not targets:
        return

    print_header(f"Step 3b: Boosting Starbase Income for ALL FACTIONS")
    
    for path in targets:
        if not os.path.exists(path):
            print(f"Skipping {path}: File not found")
            continue
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Boost Base_Income_Value to 100,000 (Massive Income)
            # Regex targets numeric values inside the tag
            new_content = re.sub(r'<Base_Income_Value>[\d.]+</Base_Income_Value>', r'<Base_Income_Value>100000</Base_Income_Value>', content)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Massively increased income in {os.path.basename(path)}")
            else:
                print(f"No income tags found to boost in {os.path.basename(path)}")
                
        except Exception as e:
            print(f"Error boosting income in {path}: {e}")

def apply_cheats(faction_name, faction_pattern):
    print_header(f"Step 3: Applying Modifications for '{faction_name}'")
    target_dirs = ["Units", "Buildings", "Research", "Upgrades"]
    processed_count = 0
    all_converted_units = []  # Collect all converted units
    
    # Debug tracking
    total_stats = {
        'squadrons': 0,
        'frigates': 0,
        'capitals': 0,
        'heroes': 0,
        'neutral_converted': 0,
        'faction_modified': 0
    }
    files_with_conversions = []  # Track files that had neutral conversions
    
    for rel_dir in target_dirs:
        abs_path = os.path.join(XML_DIR, rel_dir)
        if not os.path.exists(abs_path): continue
        
        for root, dirs, files in os.walk(abs_path):
            if "Story" in root or "Campaign" in root: continue
            
            # Exclude Ground units from Space Skirmish injection (unless user wants ground modding too)
            if "Units\\Ground" in root or "Units/Ground" in root: continue
            
            for file in files:
                if not file.lower().endswith(".xml"): continue
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                    
                    new_content, converted_units, file_stats = process_xml_content(content, faction_name, faction_pattern, file_path)
                    all_converted_units.extend(converted_units)  # Collect converted units
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f: f.write(new_content)
                        processed_count += 1
                        
                        # Track stats for debug output
                        for key in total_stats:
                            if key in file_stats:  # Skip units_with_cheats list
                                total_stats[key] += file_stats[key]
                        
                        # Track ALL modified files for debug (not just neutral conversions)
                        rel_path = os.path.relpath(file_path, XML_DIR)
                        files_with_conversions.append({
                            'file': rel_path,
                            'stats': file_stats.copy()
                        })
                except Exception as e:
                    print(f"Skipping {file}: {e}")

    print(f"Modified {processed_count} files for {faction_name}.")
    
    # Display detailed debug info if enabled
    if DEBUG and files_with_conversions:
        print("\n" + "="*80)
        print(" DEBUG: DETAILED FILE MODIFICATION REPORT")
        print("="*80)
        
        # Separate files into categories
        neutral_files = []
        faction_files = []
        
        for item in files_with_conversions:
            if item['stats']['neutral_converted'] > 0:
                neutral_files.append(item)
            else:
                faction_files.append(item)
        
        # Show Neutral/Underworld conversions first
        if neutral_files:
            print("\n" + "-"*80)
            print(" NEUTRAL/UNDERWORLD UNIT CONVERSIONS:")
            print("-"*80)
            for item in neutral_files:
                file_name = item['file']
                stats = item['stats']
                
                parts = []
                if stats['neutral_converted'] > 0:
                    parts.append(f"{stats['neutral_converted']} neutral converted")
                if stats['squadrons'] > 0:
                    parts.append(f"{stats['squadrons']} squadron(s)")
                if stats['frigates'] > 0:
                    parts.append(f"{stats['frigates']} frigate(s)")
                if stats['capitals'] > 0:
                    parts.append(f"{stats['capitals']} capital(s)")
                if stats['heroes'] > 0:
                    parts.append(f"{stats['heroes']} hero(es)")
                
                detail = ", ".join(parts) if parts else "modified"
                print(f"\n  File: {file_name}")
                print(f"    Type: {detail}")
                
                # Show units that had cheats applied
                if stats['units_with_cheats']:
                    print(f"    Units modified (time/pop/limits): {len(stats['units_with_cheats'])} units")
                    if len(stats['units_with_cheats']) <= 10:  # Show unit names if not too many
                        for unit in stats['units_with_cheats']:
                            print(f"      - {unit}")
                    else:
                        # Show first 5 and last 5
                        for unit in stats['units_with_cheats'][:5]:
                            print(f"      - {unit}")
                        print(f"      ... ({len(stats['units_with_cheats']) - 10} more) ...")
                        for unit in stats['units_with_cheats'][-5:]:
                            print(f"      - {unit}")
        
        # Show regular faction modifications
        if faction_files:
            print("\n" + "-"*80)
            print(" FACTION UNIT MODIFICATIONS (Build Time/Pop/Limits):")
            print("-"*80)
            for item in faction_files:
                file_name = item['file']
                stats = item['stats']
                
                print(f"\n  File: {file_name}")
                print(f"    Faction units modified: {stats['faction_modified']}")
                
                # Show units that had cheats applied
                if stats['units_with_cheats']:
                    print(f"    Units modified (time/pop/limits): {len(stats['units_with_cheats'])} units")
                    if len(stats['units_with_cheats']) <= 10:  # Show unit names if not too many
                        for unit in stats['units_with_cheats']:
                            print(f"      - {unit}")
                    else:
                        # Show first 5 and last 5
                        for unit in stats['units_with_cheats'][:5]:
                            print(f"      - {unit}")
                        print(f"      ... ({len(stats['units_with_cheats']) - 10} more) ...")
                        for unit in stats['units_with_cheats'][-5:]:
                            print(f"      - {unit}")
        
        # Overall summary
        print("\n" + "="*80)
        print(" TOTAL SUMMARY:")
        print("="*80)
        print(f"  Total files modified: {processed_count}")
        print(f"  Files with neutral conversions: {len(neutral_files)}")
        print(f"  Files with faction modifications: {len(faction_files)}")
        print(f"\n  Neutral units converted: {total_stats['neutral_converted']}")
        print(f"    - Squadrons: {total_stats['squadrons']}")
        print(f"    - Frigates: {total_stats['frigates']}")
        print(f"    - Capitals: {total_stats['capitals']}")
        print(f"    - Heroes/Research: {total_stats['heroes']}")
        print(f"\n  Faction units modified: {total_stats['faction_modified']}")
        print("="*80)
    
    # Inject converted units into shipyard rosters if any were found
    if all_converted_units:
        inject_units_into_shipyard_rosters(faction_name, all_converted_units)
    
    return target_dirs

def validate_xml_content(content):
    try:
        ET.fromstring(content)
        return True
    except:
        clean_content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        try:
            ET.fromstring(clean_content)
            return True
        except:
            return False

def validate_final(target_dirs):
    print_header("Step 4: Validating Modified Files Only")
    warning_count = 0
    checked_count = 0
    
    for rel_dir in target_dirs:
        abs_path = os.path.join(XML_DIR, rel_dir)
        if not os.path.exists(abs_path): continue
        for root, dirs, files in os.walk(abs_path):
            if "Story" in root or "Campaign" in root: continue
            for file in files:
                if file.lower().endswith(".xml"):
                    checked_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                        if not validate_xml_content(content):
                             print(f"WARNING: {file} syntax check failed. Game may still load it.")
                             warning_count += 1
                    except Exception as e:
                         print(f"ERROR reading {file}: {e}")

    print(f"\nChecked {checked_count} file(s). Found {warning_count} warnings (usually harmless comments).")

def main():
    print_header("EAW Remake Skirmish God Tool (Unit Injector & Income Booster)")
    print("1. Republic")
    print("2. CIS")
    print("3. Rebellion")
    print("4. Empire")
    print("\nNote: Neutral and Underworld units will be converted to your selected faction for skirmish mode.")
    
    choice = input("\nSelect Faction to apply God Mode to [1-4]: ").strip()
    if choice not in FACTIONS:
        print("Invalid selection.")
        return
        
    faction_name, faction_pattern = FACTIONS[choice]
    
    restore_backup()
    apply_fixes()
    target_dirs = apply_cheats(faction_name, faction_pattern)
    boost_starbase_income(faction_name)
    validate_final(target_dirs)
    print("\nDone. Press Enter to exit.")
    input()

if __name__ == "__main__":
    main()
