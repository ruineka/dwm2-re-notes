# 8. Monsters, records, stats, skills, breeding and items

Reference for a from-scratch port or static recompilation. Code addresses are `$BB:AAAA` (bank:in-bank address); RAM is `$Cxxx`/`$FFxx`; SRAM save-file offsets are `0x…` into a 32 KiB image. Confidence tags follow the source notes: (C2) supported or verified within a stated scope, (C1) hypothesis, `unknown` where no source establishes it.

## 1. Identity spaces

| Space | Range | Where it lives | Notes |
|---|---|---|---|
| Species id | 1–383 (0 and 384 invalid) | `MON_SPECIES` word in a record; species table bank $35 | 323 non-blank, 61 blank |
| Monster (template) id | 0–684 | `MonsterTable` $34:4075 (0–591) + $A2:4070 (592–684) | 26-byte battle template, not the species record |
| Skill id | 0–$AE | `MON_SKILLS`, `MON_SKILL_LIST`, `SkillTable` $1A:40D4 | 0 = plain attack (`ACTION_FIGHT`), 1–$AE = skills |
| Item id | 1–97 (1-based) | bag, vault, `MON_ITEM` = id − $3F | data/name id 0–97 is the same number 0-based |
| Record index | 0–29 | SRAM bank 0 $A000 | 30 × $A5-byte records |
| Party slot | 0–2 | `party_list` at file 0x3C01 | maps to record indexes |

## 2. The 30-slot monster store

- 30 full records of `$A5` (165) bytes at SRAM bank 0 `$A000`; record `i` starts at save-file offset `i*0xA5`, so the array occupies file `0x0000`–`0x1355`.
- `SRAMRecordAddress` (`$00:1FD1`) returns `HL = $A000 + i*$A5 + field offset` for a record index; the mapped variant used by item code first turns a party slot into a record index through `party_list`.
- `MON_STATE` `$00`: 0 = empty, 1 = kept (farm/hibernate), 2 = in the party. The party list holds 3 record indexes (`party_count` at file 0x3C00); battle-ready records are the state-2 ones.
- The list is kept **dense**: `DeleteSRAMRecordAndCompact` (`$14:7E96`, file 0x53E96) closes a gap by shifting later records down, which renumbers record indexes.
- An egg is an ordinary record with `MON_EGG` ≠ 0 — there is no separate egg list and no incubation counter.
- Display-only caches (lossy, never authoritative): 29 × `$6F` bytes at file 0x1356 (farm list) and 30 × `$6F` at 0x206F (bank-1 packed records), produced by `PackRecordFieldsToBank1Slot`; names are truncated to five letters and stat words keep only low byte + 2 high bits. Full `$A5` records stay the source of truth.
- Battle copies are `$4E`-byte battler records: `$00` name 10 B, `$0A` species word, `$0C` family, `$0E` four skills, `$17` level, `$18` 24-bit EXP, `$1B` HP, `$1D` max HP, `$1F` MP, `$21` max MP, `$23` ATK, `$25` DEF, `$27` AGL, `$29` INT, `$2B` WLD, `$2D` personality 4 B (record order `$6F,$70,$72,$71`), `$31` 27 resistances, `$4D` join-chance class.

## 3. The `$A5` record, field by field

| Off | Size | Name | Meaning |
|---:|---:|---|---|
| `$00` | 1 | MON_STATE | 0 empty, 1 kept, 2 party |
| `$01` | 10 | MON_NAME | name, `$F0` terminator and padding |
| `$0B` | 2 | MON_SPECIES | species id word |
| `$0D` | 1 | MON_FAMILY | low nibble = family 0–10; bit 4 = parents stored swapped (parent A was female) |
| `$0E` | 1 | MON_SEX | bit 0: 0 male, 1 female |
| `$0F` | 10 | MON_MASTER_NAME | player name at breeding time |
| `$19` | 1 | MON_MASTER_ID | `wPlayerId` at breeding time |
| `$1A` | 2 | MON_PARENT1_SPECIES | species of parent 1 |
| `$1C` | 2 | MON_PARENT2_SPECIES | species of parent 2 |
| `$1E` | 10 | MON_PARENT1_MASTER | parent 1's master name |
| `$28` | 1 | MON_UNUSED_28 | never read; presets 0, unknown-parent placeholder $FF |
| `$29` | 10 | MON_PARENT2_MASTER | parent 2's master name |
| `$33` | 1 | MON_UNUSED_33 | never read; as `$28` |
| `$34` | 8 | MON_SKILLS | known skills, `$FF` = empty slot |
| `$3C` | 25 | MON_SKILL_LIST | candidate skills (learnable pool), `$FF` = empty |
| `$55` | 1 | MON_STATUS | bit 7 dead, bit 2 poison |
| `$56` | 1 | MON_LEVEL | level |
| `$57` | 1 | MON_MAX_LEVEL | level cap for this monster |
| `$58` | 3 | MON_EXP | 24-bit experience |
| `$5B` | 2 | MON_HP | current HP |
| `$5D` | 2 | MON_MAX_HP | max HP |
| `$5F` | 2 | MON_MP | current MP |
| `$61` | 2 | MON_MAX_MP | max MP |
| `$63` | 2 | MON_ATK | ATK |
| `$65` | 2 | MON_DEF | DEF |
| `$67` | 2 | MON_AGL | AGL |
| `$69` | 2 | MON_INT | INT |
| `$6B` | 2 | MON_WLD | WLD (wildness), shown after INT |
| `$6D` | 1 | MON_PLUS | breeding plus value |
| `$6E` | 1 | MON_EGG | 0 not an egg, 1 unappraised egg, 2 appraised egg |
| `$6F` | 4 | MON_PERSONALITY | four axes; `$6F/$70/$72` are used, `$71` is never read |
| `$73` | 27 | MON_RESISTANCES | one level 0–3 per resistance index |
| `$8E` | 10 | MON_PARENT1_NAME | parent 1's name |
| `$98` | 1 | MON_PARENT1_PLUS | parent 1's plus |
| `$99` | 10 | MON_PARENT2_NAME | parent 2's name |
| `$A3` | 1 | MON_PARENT2_PLUS | parent 2's plus |
| `$A4` | 1 | MON_ITEM | equipped item = item id − $3F, 0 = none |

Resistance index order (27): 0 BLAZE, 1 FIREBAL, 2 BANG, 3 VACUUM, 4 BOLT, 5 ICEBOLT, 6 RADIANT, 7 SLEEP, 8 BEAT, 9 ROBMAGIC, 10 STOPSPELL, 11 PANICALL, 12 SAP, 13 SLOW, 14 SACRIFICE, 15 MEGAMAGIC, 16 FIREAIR, 17 FRIGIDAIR, 18 POISONGAS, 19 PALSYAIR, 20 CURSE, 21 LEGSWEEP, 22 DANCESHUT, 23 MOUTHSHUT, 24 ROCKTHROW, 25 GIGASLASH, 26 WATERSHOT.

## 4. Species table (bank $35)

- `SpeciesRecordPointers` at `$35:403B`: 384 words, one per species id, `$4000`-based within the bank; behind it `SpeciesRecords` at `$35:433B`, 324 distinct 47-byte records laid out contiguously up to `$35:7EB7`. Ids that share a record all point at it; species 0 uses the family-`$FF` record.
- Access helpers: `CopySpeciesRecordPrefix` (B = byte count, DE = destination; the id is **not** range-checked), wrappers `LoadSpeciesRecord` (47 bytes → `wSpeciesRecord`), `LoadSpeciesFamily` (1 byte), `LoadSpeciesRecordWord0` (2 bytes).
- `SpeciesRecordPointers[id]` is the only gate: an out-of-range id reads garbage.

| Off | Size | Name | Meaning |
|---:|---:|---|---|
| `$00` | 1 | SPECIES_FAMILY | family 0–10; `$FF` = unused entry |
| `$01` | 1 | SPECIES_SEX_RATIO | 0 = always male; otherwise `(byte & 3)` indexes the female chance table {0, 10, 50, 90} |
| `$02` | 1 | SPECIES_UNTRIPPABLE | bit 0 → immune to LegSweep/BigTrip |
| `$03` | 1 | SPECIES_METAL | bit 0 → MetalCut ×50; non-zero also raises one stat cap in battle kind 3 |
| `$04` | 1 | SPECIES_JOIN_CLASS | 0–7, `random mod 200` compared with a chance table; 7 = never joins |
| `$05` | 1 | SPECIES_UNUSED_05 | values 0–3 in the data, never read by code |
| `$06` | 1 | SPECIES_MAX_LEVEL | base level cap, copied to `MON_MAX_LEVEL` |
| `$07` | 1 | SPECIES_EXP_CURVE | row of `ExpTable` |
| `$08` | 3 | SPECIES_SKILLS | three natural skills |
| `$0B` | 1 | SPECIES_FIELD_ABILITY | 0 None, 1 Call ship, 2 Call cloud, 3 Smash rock, 4 Burn, 5 Cut, 6 Open door |
| `$0C` | 6 | SPECIES_GROWTH | growth rows for HP, MP, ATK, DEF, AGL, INT |
| `$12` | 27 | SPECIES_RESISTANCES | base resistance levels 0–3, copied into new records |
| `$2D` | 2 | SPECIES_EXP | base EXP word, used as the low word of a foe's 24-bit EXP |

Families and species ranges (non-blank ids only):

| Family | Name | Species ids |
|---:|---|---|
| 0 | Slime | 1–27, 373–378 |
| 1 | Dragon | 36–66 |
| 2 | Beast | 71–102 |
| 3 | Bird | 106–132 |
| 4 | Plant | 141–167 |
| 5 | Bug | 176–201 |
| 6 | Devil | 211–240 |
| 7 | Zombie | 246–272 |
| 8 | Material | 281–312 |
| 9 | Water | 316–347 |
| 10 | ???? | 351–372, 379–382 |

Blank runs with no species: 28–35, 67–70, 103–105, 133–140, 168–175, 202–210, 241–245, 273–280, 313–315, 348–350, 383. Gated specials 27 and 373–379 carry max level 0, EXP curve 0, all growth rows 0, skills `FF FF FF` and base EXP 0 (id 27 is byte-identical to 378). 380 Lamia (cap 99), 381 Dimensaur (cap 9) and 382 Kagebou (cap 99) have base EXP 0 and are not breedable.

Species artwork: battle portraits are LZSS streams of 576 bytes (6×6 tiles) in banks $74–$7B, 315 pictures in monster-id order, first at `$74:4001`. The picture index is `MonsterTable` word 0 (≤ $0179). Stream = u16 output size (LE) + marker byte + body; body bytes ≠ marker are literals, the marker introduces a 2-byte back-reference (length = (b2 & $0F) + 4, $13 = an extra length byte; offset = ((b2 >> 4) << 8) | lo from the start of the output; a source at or past the output end wraps back by $1000, a source before the start reads 0).

## 5. Stats

Two independent stat sources exist; a port must keep both.

**Template stats (`MonsterTable`).** 26-byte records: word 0 = species/picture id, bytes 2–5 = four skills, words 6–7 = EXP (low word of the 24-bit field), byte 8 = join class, byte 9 = level, words 10–21 = base HP, MP, ATK, DEF, AGL, INT, bytes 22–25 = personality axes → `$6F,$70,$71,$72`. `MonsterTable` holds 592 records (ids 0–591, `$34:4075`–`$34:7C95`, then `ds $36b`); ids 592–684 come from `$A2:4070 + 26*(id−$250)` (93 records ending `$A2:49E2`, selected by `LoadMonsterRecordTo_HighIds`). Example: id 1 Slime = EXP 0, join 0, level 1, HP 25, MP 0, ATK 10, DEF 7, AGL 8, INT 7, personality `C8 C8 64 C8`.

**Growth-row stats.** `StatGrowthBase` is a 32-byte table, `StatGrowthTable` 32 rows × 99 bytes at `$1A:6616`–`$1A:72D6` (the sources give the base at `$1A:63F8`, C1). Row `g` byte 0 is always `$00` and byte `k` (k ≥ 1) is the gain from level k to k+1, so

    stat(g, L) = StatGrowthBase[g] + Σ(k = 0 … L−1) StatGrowthTable[g][k]

`StatFromGrowthRow` adds exactly `level` bytes of the row to the base with a 16-bit sum and no rounding, which makes `stat(g, 1) = StatGrowthBase[g]`. `StatGrowthBase[0..31]` = 1, 2, 2, 2, 3, 3, 3, 3, 4, 5, 5, 6, 7, 3, 4, 5, 6, 7, 8, 4, 5, 6, 7, 7, 8, 11, 12, 13, 12, 12, 14, 16 — rows 13 and 19 really dip back down. All six stats use the same table. Example: DrakSlime growth rows 16, 10, 13, 8, 20, 16 give level-1 stats 6, 5, 3, 4, 5, 6.

**Record creation.** `CreateMonsterRecordInSlot_Build` (bank $01) copies species, sex, the player as owner, placeholder parent names, the template's level, the template's HP (a template HP of `$400` or more becomes 999) and MP, the six template stats, family, natural skills, level cap, resistances, a name and the EXP for that level (`LoadTableEntryForRecordBufASpeciesToRecordBufAExp`). Starting records therefore use hand-tuned template stats, not growth rows.

**Wild foes.** Two builders, both from the species growth rows:
- `GameMode4_Init_BuildFoeRecord` (bank $19): level = `wWildLevel[slot]` (minimum 1), stats = `StatFromGrowthRow`, then `ScaleStatAndCapByBattleKind`: value = floor(101·v/100); in battle kind 3 with the HP stat the 101 % value is multiplied by 5 when `wBattleIntroFlag` or `wBattleArg1` is 1, otherwise by 2 (product > 65535 → 10000); otherwise capped at 999, except stat 2 → 600 (700 in kind 3) and stat 3 → 700 (999 in kind 3 when the species is metal). The cap test is a signed 16-bit compare, so a value more than 32767 over its cap is not capped.
- `ApplyLevelScaledStatsToSlots` (bank $A0): level = min(4·`wWildLevel`/5 + 5, 99); stats = `StatFromGrowthRow` then `ScaleStatByWildLevelCapped999`: v = v·(100 + ((`wWildLevel` >> 2) & $3F))/100 floor, capped 999.

**Level-up.** `ComputeLevelUpStatGainsForBattleArg1` (bank $1A) uses the record index raw (not the party list). If `MON_LEVEL` ≥ `MON_MAX_LEVEL` all eight gain bytes stay 0. Otherwise, per stat in order HP, MP, ATK, DEF, AGL, INT, the gain is `StatGrowthTable[growth_row][MON_LEVEL]` plus an item bonus for exactly one stat (`ComputeLevelUpStatGainsForBattleArg1_ItemBonus`), then `ClampLevelUpGainsTo999` limits each gain so the record's word stays ≤ 999 (order `$5D,$61,$63,$65,$67,$69`). `ApplyLevelUpToRecordBattleArg0` adds the gains to `MON_MAX_HP`, `MON_MAX_MP`, `MON_ATK`, `MON_DEF`, `MON_AGL`, `MON_INT`.

The item bonus applies only when `MON_ITEM` is `$1D`–`$22` (War, Mage, Fight, Sailor, Thief, Cleric rings): the target stat = `MON_ITEM − $1D`, and the bonus is half the count of eight values whose bit 0 equals bit 0 of `MON_PLUS` — `MON_LEVEL`, the low bytes of `MON_MAX_HP`, `MON_MAX_MP`, `MON_ATK`, `MON_DEF`, `MON_AGL`, `MON_INT`, `MON_WLD`, and the name length (bytes before `$F0`, `$8D`/`$8E` marks not counted). Integer halved, no rounding up.

**Caps.** Stat words saturate at 999 (`$3E7`). Level is hard-capped at 99; a monster's own cap is `min(species_max_level + 3·MON_PLUS, 99)`.

**EXP.** `ExpTable` at `$19:4E60`–`$19:7380`: 32 rows × 99 × 3-byte little-endian entries; row = `SPECIES_EXP_CURVE`, entry index `L−1` = total EXP to be level `L` (`LoadExpTableEntryToTemp2`, address `$4E60 + $129·row + 3·index`). Every row starts 0, 2, 7, 15, 27, 45, 72, 113, 175, 268, 408 … but rows diverge later (curve 0 ends at 1 521 048; curve 31 at 7 198 692). Entry `MON_LEVEL` is "EXP for the next level". Bank $81 keeps a second copy, `ExpTable81` (`$81:555D`) with the `ExpCurveIndex81` species→row map (215 bytes), used when packing a record for link play.

## 6. Skills

- `SkillTable` at `$1A:40D4`: 228 records × 17 bytes (ends exactly at `$1A:4FF8`), indexed by skill id; only ids < 175 are monster-usable and `$FF` is an empty slot. `LoadSkillRecord` multiplies the index by $11. Fields: first displayed number, skill family string, type string, a byte whose low 2 bits index the usage category (0 None, 1 Battle, 2 Field, 3 Anytime) and whose high nibble is a string category, target string, five display numbers, three 16-bit values (damage estimate and friends).
- `SkillRequirementTable` at `$1A:4FF8`: 170 records × 18 bytes (ends `$1A:5BEC`): one required level byte, six required stat words in battler order max HP, max MP, ATK, DEF, AGL, INT, then five prerequisite skill ids (`$FF` = none).
- `SkillPrerequisitePointers` at `$1A:5BEC`: 170 words into `SkillPrerequisiteLists`, `$FF`-terminated skill lists that share tails (Blaze → Blazemore, Blazemore → Blazemost).
- `AddSkillCToFreeOrWeakerSlot_Data` at `$1A:5EDF`: 170 words of "skills this skill supersedes" lists (Blazemost supersedes Blaze, `db $02`; Blazemore supersedes Blaze, `db $01,$ff`; most lists are empty). `AddSkillCToFreeOrWeakerSlot` writes the new skill into the first of eight working slots that is empty or holds a superseded skill — a slot holding any other skill is skipped (the routine name describes the opposite of what it does), and only `TryAddSkillUnlessBetterKnown`, which has no traced caller, calls it.
- Learning checks: `FindNewlyLearnableSkills` scans the 170 requirement rows in skill order for the level-up record and returns one of three codes — 0 = the skill is in the 25-byte `MON_SKILL_LIST` (that entry is set to `$FF`), 1 = an upgrade, because the row's first prerequisite skill is already in `MON_SKILLS`, 2 = "devised", because the row's later prerequisite skills are all known. A row is skipped when the skill is already known, when `MON_LEVEL + 1` is below the row level, or when any of the six stats is below the required value. Result in `hTemp3` (skill) and `hTemp4` (0/1/2); `hTemp5` = the old skill for an upgrade; `$FF`/`$FF` when nothing is learnable.
- Slots: an SRAM record holds 8 known skills (`$34`) plus 25 candidates (`$3C`); a battler record holds 4 (`$0E`, filled from `MonsterTable` bytes 2–5 for wild monsters). `LoadSlotSkillsFromBattlerRecord` expands a battler's four skills into 8 battle entries (one skill per even byte, 0 for an empty entry). The exact rule choosing which 4 of a party monster's 8 skills go into its battler record is **unknown**.

## 7. Breeding

**Inputs.** The base parent is copied to `wRecordBufA` (`$C986`), the mate to `wRecordBufB` (`$CA2B`), both as full `$A5` records; the tables are asymmetric, so which parent is the base matters. The mate list only offers records with the opposite `MON_SEX` bit and `MON_EGG` = 0. `wArg1` (RAM `$D7F1`) is the breeding kind: 0 = farm, 1 = townsperson, 2 = link.

**`ComputeBreedingChild` (`$0E:5688`)** clears `wChildRecord` (165 bytes) and tries four rule stages in order; the first match wins. Each stage selects a pointer array by **parent A**, walks a rule list, and indexes a result array by the number of "next result" markers consumed (`c`):

| Stage | Selector | Rule table | Result table |
|---:|---|---|---|
| 1 species + species | A species | `BreedSpeciesRuleTable` `$0E:6208` | `BreedSpeciesResultTable` `$0E:6E14` |
| 2 species + family | A species | `BreedFamilyRuleTable` `$0E:734E` | `BreedFamilyResultTable` `$0E:774F` |
| 3 family + species | A family | `FamilyBreedRuleTable` `$0E:7B83` | `FamilyBreedResultTable` `$0E:7DBF` |
| 4 family + family | A and B family | `FamilyPairResultTable` `$0E:7E83`, rows of 11 words at `$0E:7E99`–`$0E:7F8B` | the row itself |

Stages 1 and 3 entry grammar (2-byte little-endian words, marker in the high byte):

| Entry | Effect |
|---|---|
| `$FFxx` | end of list → next stage |
| `$FDxx` | `c += 1`, continue (this entry begins the next result group) |
| `$FBxx` | in link breeding (kind 2) acts as `$FD`; otherwise end of list → next stage |
| `$FExx` | match if parent B's `MON_PLUS` ≥ low byte **and** both parents have the same species |
| `$FCxx` | match if parent A's `MON_PLUS` ≥ low byte **and** both parents have the same species |
| species id | match if parent B's species equals the word |

Stage 2 entry grammar: one byte per entry — the mate's **family**; `$FE` consumes a result slot only in link breeding, `$FF` ends the list. Each entry (matched or not) advances the result index, so the result is `BreedFamilyResultTable[A.species][byte_position]`. Stage 4: the word at `FamilyPairResultTable[A.family][B.family]`; high byte `$FF` → the child is parent A's own species, high byte `$FE` → **no child** (sets `wArg6/wArg7 = $FFFF`, `wNameEntryState = 6`, `wArg5 = $FF` and returns with the record untouched); otherwise the word is the child's species id. Retail data contains no `$FE` entry in stage 4.

Verified example: DrakSlime (1) × Swordgon ($2B) → SlimeBorg (14). A 443 514-case lookup comparison against a full table extraction found no mismatch, and 336 243 cases matched an emulator model; the one known divergence is that family 15 (blank species records) reads out of bounds in the ROM.

**Bank $81 is not the child lookup.** `CheckBreedingRecipes` (`$81:4001`) validates a record received over the link against `SpeciesPairCheckTable` (`$81:4167`, 321 words, lists at `$81:43E9`–`$81:5453`): it reads the record's own species/family plus both parents' species/family, then runs `CheckBreedingRecipes_CompareHLToBC` twice, once with the parents in order and once swapped. A rule is a kind byte, a count byte, a key word and that many partner words: kind 0 matches the record's family against the key's low byte, kind 1 matches the first parent's species; a partner word with bit 15 set must match a species, otherwise a family; the `$FF` terminator matches when parent 1's species equals the record's species and parent 2's family equals the record's family. C = 0 on a match, C = `$FF` otherwise, and a match only in the swapped order sets bit 4 of the received record's `MON_FAMILY`. DrakSlime's check is `00 01 00 00 01 00 ff 00`, i.e. (family 0 and family 1) or the same species. The child lookup itself is entirely in bank $0E.

**Child record fill, in order** (`wArg6/wArg7` = child species):

1. `MON_SPECIES` ← child species.
2. `MON_FAMILY` ← `FamilyForSpeciesIdArg6(child) | ((A.MON_SEX & 1) << 4)`; `FamilyForSpeciesIdArg6` (`$0E:615A`) maps species to family by id ranges (high byte 0: <$1B→0, <$43→1, <$67→2, <$85→3, <$A8→4, <$CA→5, <$F1→6, else 7; high byte 1: <$11→7, <$39→8, <$5C→9, else 10).
3. `MON_STATUS` = 0, `MON_ITEM` = 0, `MON_EXP` = 0 (3 bytes), `MON_MASTER_ID` ← `wPlayerId`, `MON_LEVEL` = 1, `MON_STATE` = 1, `MON_EGG` = 1. The name is left empty for the naming screen.
4. `CopyFourNamesByChildRecordFamilyBit4Table`: parents' names → `$8E`/`$99`, parents' master names → `$1E`/`$29`, swapped when bit 4 of the child's `MON_FAMILY` is set; `CopyPlayerNameToChildRecordMasterName` → `$0F`; `CopySixBytesByChildRecordFamilyBit4Table` writes the parents' species and plus values to `$1A`,`$1C`,`$98`,`$A3` (also swapped by bit 4).
5. Stats: for the eight words at offsets `$5D,$5D,$61,$61,$63,$65,$67,$69` (max HP, HP, max MP, MP, ATK, DEF, AGL, INT): after `AdjustStatForRecordBufAAndBItems` subtracts the parents' equipped-item bonuses, the word = `(A + B) >> 2` (two logical shifts, round down). HP/MP therefore start full. `MON_WLD` (`$6B`) stays 0.
6. Personality: each of the four bytes `$6F`–`$72` = `(A + B) >> 1` (8-bit add, logical shift).
7. `MON_PLUS` = (kind ≠ 0 ? A's plus : max(A's plus, B's plus)) + bonus, where bonus = 5 if the parents' level sum ≥ 100, 4 if ≥ 76, 3 if ≥ 60, 2 if ≥ 40, else 1; a result ≥ 100 becomes 99 (`$63`).
8. `MON_MAX_LEVEL` = species max level + 3·plus; a high byte ≠ 0 or a low byte ≥ 100 becomes 99.
9. `RollChildSexFromSpecies` (`$0E:61C1`): species byte `$01` = 0 → male, no roll. Otherwise chance = {0, 10, 50, 90}[byte & 3] (`SexChanceByClass`, `$0E:61FC`) and one 0–99 roll; **female when chance ≥ roll**, so the classes are 11/100, 51/100 and 91/100 female, not 10/50/90.
10. `ApplyBreedingBonusToChildStats` (`$0E:5EE8`): pct = 5 when `PersonalityPairValueToArg5` is 0, +5 when both parents are at their level cap, +2 when both plus values are ≥ 5 and their sum is even, +3 when `wArg1` ≠ 0. Each of the eight stat words then gains `ceil(word · pct / 100)` and is clamped to 999.
11. `RollChildResistancesToChildRecordResistances` (below), then `BuildChildRecordSkillListCandidateList`.
12. `wNameEntryState += 1`, `wArg5 = $FF`, return.

**Item bonus removal (`AdjustStatForRecordBufAAndBItems`).** Per stat class the routine lists which `MON_ITEM` values add to it — HP/max HP {1, 2}, MP/max MP {3, 4}, ATK {5, 6}, DEF {7, 8, $14}, AGL {9, $A}, INT {$B, $C} — and subtracts `{0, 30, 80, 30, 80, 10, 50, 10, 50, 10, 50, 50, 100, 0, …, 0, 5, 0}[item]` from that parent's word with 16-bit wraparound (no floor), skipping the subtraction when the word is already ≥ 999.

**Personality compatibility (`PersonalityPairValueToArg5`).** Each parent's personality index = `9·grade($6F) + 3·grade($72) + grade($70)` where grade = 0 if the byte is ≥ `$C0`, 1 if `$40`–`$BF`, 2 if < `$40`. The 2-bit result is read from `PersonalityPairMatrix` (`$0E:603F`, 27 rows × 8 bytes, `$FF`-padded): byte = matrix[8·A + B/4], masked with `{c0, 30, 0c, 03}[B & 3]`, shifted right by 6/4/2/0. Value 0 gives the +5 % child-stat bonus. Whether the value is used outside breeding is **unknown**.

**Resistance inheritance.** For each index k in 0–26 the child starts from the species level s (`LoadSpeciesResistanceArg4`):
- s = 3 → kept, no roll.
- s = 2 → requires the parents' levels at k to sum to ≥ 5; then roll.
- s = 0 or 1 → requires the sum ≥ 3; then roll.
- Sum = A's level + B's level at k (each 0–3). A parent's level counts as invalid (and the roll for k is cancelled) when that level is 2 and the parent's `MON_ITEM` is 1–$1B with `TestResistanceEntry_Data[item − 1]` = k. The table is `00 01 02 03 04 05 06 0e 0f 07 10 11 12 13 14 08 09 0a 0b 15 16 17 18 19 1a 0c 0d`.
- Rolls need the **child's** `MON_PLUS` ≠ 0; a child with plus 0 inherits the species level only. The stored value is `level & 3`.

| Situation | Rule |
|---|---|
| s ≤ 1, sum = 3 | factor 1 |
| s ≤ 1, sum = 4 | factor 3 |
| s ≤ 1, sum = 5 | factor 10; if that raised, factor 3 again (second roll) |
| s ≤ 1, sum ≥ 6 | level += 1 first, then factor 5 |
| s = 2, sum = 5 | one 0–199 roll; raise when plus ≥ roll |
| s = 2, sum ≥ 6 | factor 2 |

A factor roll sets chance = factor · child plus; when chance ≥ 100 it raises without consuming a random number, otherwise it draws 0–99 and raises when chance ≥ roll.

**RNG order inside `ComputeBreedingChild`** (must match): (1) one `RandomModulo29` draw with mask `$0F` for the sex; (2) the 27 resistance slots in ascending index order, each drawing zero, one or two numbers as the conditions above dictate. `RandomModulo29` (`$0E:2823`) advances the ROM byte table (`NextTableByte`, new value in `wRandomLo`), then builds `HL = (((wRandomLo rl) & B) << 8) | wRandomLo` and divides it by 41 ($29), returning the **quotient** in L (0–99 for B = `$0F`, 0–199 for B = `$1F`); the remainder is discarded. The table address and the counter were not captured here.

**Skills of the child (`$0E:5AA4`).** `MON_SKILLS[8]` is set to `$FF`, then `MON_SKILL_LIST[25]` is filled in this order: child species' 3 natural skills, A's species' 3, B's species' 3, A's 8 known skills, B's 8 known skills. Every non-`$FF` entry is mapped through `SkillLineBaseTable` (176 entries, skill → first skill of its upgrade line, e.g. 1–3 → 1, 4–6 → 4), zeros and duplicates become `$FF`, the list is compacted, and duplicates are cleared again.

**Egg creation, appraisal, hatching.**

- `BreedMenu_ChooseParents_Breed` (`$15:4E47`) runs breeding from the menu; `BreedMenu_ChooseParents_PayAndMakeEgg` (`$15:5030`) charges the fee, deletes both parents, and writes the child into the slot freed by the first parent. The child appears as `MON_STATE` = 1, `MON_EGG` = 1, `MON_LEVEL` = 1.
- Fee = 10·`MON_PLUS` + 10 gold (`TenTimesTemp0PlusTen`, `$15:680F`), used for both breeding and hatching.
- `EggServiceMenu_Appraise` (`$0D:4988`) charges 20 gold and sets `MON_EGG` = 2 (`$0D:4AFE`); only then does the list show the egg's sex mark.
- A separate **blessing** service charges 20·plus + 20 gold and flips the egg's `MON_SEX` byte (0 ↔ non-zero) in the record (`EggServiceMenu_ChooseAndPay_CheckPrice`, bank $0D). It consumes no random numbers.
- `BreedMenu_ChooseEgg_Hatch` (`$15:556A`) charges the fee and sets `MON_EGG` = 0; hatching is a paid menu action, never timed.
- `BreedMenu_NameEntry` (`$15:55D2`) deletes the child record and re-inserts it, so a named child moves to the end of the record list and the indexes shift.
- The no-child path sets `wArg6/wArg7 = $FFFF` and `wNameEntryState = 6` and returns before any field is written; what the menu then does was not traced, and retail stage-4 data never reaches it.

## 8. Items

- Ids: name/data/table index 0–97 are the same number. The bag and the vault store **1-based** ids (1–97). Item data lives at `0x58CCF`: 98 records × 13 bytes = category, price (16-bit LE), battle-usable flag, flag, two unknown bytes, target, icon, two effect ids, var_a, var_b. Name ids 0–82 hold the item names (many entries blank), 83–88 are "None" placeholders, 89–96 are the rings Life, Divine, War, Mage, Fight, Sailor, Thief, Cleric; 111–222 are descriptions (description id = item id + 112).
- Bag: 24 slots at file 0x3B20, one 1-based id each, `$FF`/0 = empty. Vault: 100 `{id, count}` pairs at file 0x3B38, id 0 = empty entry.
- `MON_ITEM` stores item id − `$3F`, so only ids 64–97 can be equipped (values 1–$22). Equipping (`EquipItemOnRecordTargetRecord`, bank $16) consumes the item when the slot was empty; otherwise it swaps the old item back into the bag slot of the new one, runs `CompactInventory`, removes the old bonus and reports the old item's name.
- Equipment effects (item ids): 64 VITbelt +30 max HP, 65 DracoBelt +80 max HP, 66 MagicBelt +30 max MP, 67 OddBelt +80 max MP (HP/MP pairs raise current and max together), 68 StoneFang +10 ATK, 69 SteelFang +50 ATK, 70 MermScale +10 DEF, 71 DrakScale +50 DEF, 72 +10 AGL, 73 +50 AGL, 74 Smart +50 INT, 75 Wise +100 INT (all clamp 999), 76–82 MagicCape, DracoCape, SilvrCape, GoldCape, PltnmCape, OrcaCape, BraveCape (equip only), 83 D-Scale +5 DEF, 84–89 no effect, 90–97 the eight rings (equip only). The seven capes' real effect is applied when a battler record is packed: `ApplyEquippedItemIncrements` (bank $A0) reads row `MON_ITEM − $0D` of `IncrementOffsetRows_A0` (16 bytes per row, `$80` terminator) and raises each named resistance byte by 1 unless it is already ≥ 3; other `MON_ITEM` values change nothing there. The six rings War–Cleric also give the level-up parity bonus described in section 5; no other effect of the rings was found.

## 9. Values a reimplementation must match exactly

- All stat words saturate at 999; a child's stat is `(A + B) >> 2` with the item bonus already removed from the parents; the percentage bonus rounds **up** (`ceil`), while level-up gains and wild scaling round **down**.
- `MON_PLUS` does not add to stats directly: it raises the level cap by 3 per point, gates resistance inheritance, sets the breeding/hatching fee (10·plus + 10) and the blessing fee (20·plus + 20), and feeds the ring parity bonus. It saturates at 99, and the level cap at 99.
- Sex is a single bit; the species ratio class is a female chance where **chance ≥ roll** wins, and class 0 skips the roll entirely (no RNG consumed).
- Resistance inheritance depends on the parents' item-cancelled levels, the sums 3/5, the child's plus, and consumes its random numbers in index order after the sex roll.
- Level-up uses `StatGrowthTable[row][MON_LEVEL]` — the current level is the row index, because the level-L stat already consumed bytes 0…L−1 — and refuses to run when `MON_LEVEL` ≥ `MON_MAX_LEVEL`: gains are all-zero, not clamped.
- `MON_FAMILY` bit 4 is part of the child's family byte and swaps every stored parent field; it is not a spare bit.
- `MON_EXP` is 24-bit little-endian; `ExpTable` entries are also 3-byte values indexed by level − 1.

## 10. Known gaps

- Critical-hit, pain, size (S/M/L/LL/G) and rarity classes exist in the game but are **not** in the 47-byte species record; their storage and derivation are unknown.
- `MON_UNUSED_28` and `MON_UNUSED_33` are never read; their intended content is unknown (presets hold 0, the unknown-parent placeholder `$FF`).
- The farm cache holds 29 `$6F` entries while there are 30 records; the reason is not established.
- The RNG table address and counter behind `NextTableByte` were not recorded.
- `RefreshRecordResistancesFromSpecies` exists but has no caller in the current source tree, so when a record's resistances are refreshed from the species is unresolved.

## Sources

Notes: `re/notes/monster_data.md`, `re/notes/monster_stats.md`, `re/notes/species_reference.md`, `re/notes/species_names.json` (sampled), `re/notes/level1_stats.md`, `re/notes/breeding.md`, `re/notes/breeding_pair.md`, `re/notes/breeding_egg.md`, `re/notes/item_mapping.md`, `re/notes/monster_sprites.md`, `re/notes/save_format.md`. Source: the reference disassembly — `records.inc` and `data/bank34_monster_table.asm`,
  `bank35_species.asm`, `bank0e_breeding_data.asm`, `bank81_species_pairs.asm`,
  `bank1a_skill_prereqs.asm`.
