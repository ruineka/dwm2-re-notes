# 10. Menus, towns and services

All addresses were re-read from *Tara's Adventure* (USA), sha256 `fc6809c31ff69c889dee80c5f39f4d8069042a2b4d933edd83d1627c32e013cc`; `file = bank*0x4000 + (addr - 0x4000)`. Confidence tags from the notes: **C1** one routine read, **C2** reference listing *and* this ROM agree, **C3** verified on a running cartridge; untagged = byte-verified table data. **UNKNOWN** marks what the notes explicitly do not know.

## 1. Pause menu (game mode 2)
`wGameMode` (`$C5DB`) = 2 → `GameMode2_Init` / `GameMode2_Update` (bank `$03`). Init sets `wDataBankSave` = 0, text cursor `vBGMap0 + $1C1`, then `ResumeAfterModeChange`; Update builds the page and dispatches on `wModeState & 7`, and `GameMode2_Update_OpenPage_BuildPage` dispatches the same five values to the builders. B on PLAN runs `ExitPauseMenuToField` (mode 1).

| `wModeState & 7` | Screen | Routine | Builder | Heading |
|---|---|---|---|---|
| 0 | INFO | `PauseMenu_Info` | `BuildInfoPage` | tiles only |
| 1 | ITEMS | `PauseMenu_Items` | `BuildItemPage` | `String_09_00_00` |
| 2 | SKILLS | `PauseMenu_Skills` | `BuildSkillsPage` | `String_09_00_01` |
| 3 | PLAN | `PauseMenu_Plan` | `BuildPlanPage` | `String_09_00_02` |
| 4 | GIFT | `PauseMenu_State4` | `BuildItemPage` | far-call bank `$F1` |

Heading glyph runs (bank `$09`, category 0): files `0x24232`, `0x24259`, `0x24263`, one occurrence each — single-letter glyph runs, **not** readable text.

`PauseMenu_Plan` dispatches on `wTemp0` (`$C0A0`); the list sets `wMenuRowCount` = 6, `wMenuPageCount` = 1; A sets `wTemp0 = (wMenuSelectedMember & 7) + 1`, i.e. entry `i` opens sub-page `i+1`.

| Cursor | Sub-page | Kind | Data |
|---|---|---|---|
| 0 | 1 Keys | list | `wKeyList` `$C707` (32 × 4 B) |
| 1 | 2 Tactics | cycle ×4 | `MON_SEX` bits 4–5 |
| 2 | 3 Text speed | cycle ×8 | `wBattleTextSpeed` `$C834` |
| 3 | 4 Re-order | edit | `wPartyList` `$C6FE` |
| 4 | 5 Player record | info | `wPlayerName` `$C60C`, play time `$C830/$C831/$C82F` |
| 5 | 6 Journal | save | `RunPauseMenuSave` → `RunSaveGameSteps_2` |

The six labels are **graphics**: compressed screen block `$21` (`LoadScreenBlock21`) plus the `String_09_00_02` heading. No "KEYS"/"TACTICS"/"RE-ORDER"/"JOURNAL" string exists in any text bank, so those English words are inferred from routine names and a text-rendering port diverges visually here.

Journal gate `SaveForbiddenHere` (bank `$16`): on a special map (`wMapType` bit 7) it refuses iff `wEncounterRate & $7F != 0`; otherwise it refuses iff bit 4 of `MapItemUseFlags[hMapId]` is clear (256 B at file `0x591C9`, `$16:$51C9`). Refusal shows `String_08_08_0D` instead of the save flow.

**Pagination** (`SetupInventoryMenuPages_Bank03`): 4 rows/page, `page_count = ceil(n/4)` min 1, `last_page_rows = n%4 || 4`. Skills (`PauseMenu_Skills_ChooseMember_CountSkills`): 0 skills → 0 pages, 1–4 → 1, 5–8 → 2; rows via `SetMenuRowsForPage` (last page → `last_page_rows`, else 4). The item list is **not** category-grouped: the count stops at the first empty `wInventory` byte.

**Cursor** (`UpdateMenuCursor`), exact behaviour: `wMenuCursor` (`$C46E`) low nibble = row, bit 7 = page-changed. Up/Down (`wJoypadPressedRepeat` bits 7/6) move the row and **wrap** over `wMenuRowCount`; old cell tile `$C3` erased, sound `$69`, tile `$BB` drawn. Left/Right (bits 5/4) step `wMenuPage` with wrap only when `wMenuPageCount >= 2`, and clamp the row to `wMenuLastPageRows - 1` on the last page. Blink: drawn when `(wFrameCounterLo & $1F) == $10`, erased at 0. PLAN cells `61 98 a1 98 e1 98 21 99 61 99 a1
99` at file `0xc60b` (`$03:$460B`), copies at `0x1d088`, `0x3c4a5e`; item-member cells `$03:$4617`, speed cells `$03:$4649`.

| Address | Name / meaning |
|---|---|
| `$C5DB`–`$C5DE` | wGameMode, wModeState (low 3 bits = screen), wWorldMapState (bit 7 = open), wGameMode2Arg |
| `$C0A0`–`$C0A3` | wTemp0 (PLAN sub-page), wTemp1, wMenuRowCount, wMenuPageCount |
| `$C0A4`–`$C0A8` | wPauseMenuScreen, wMenuLastPageRows, wMenuPage, wMenuItemCount, wPauseMenuStep |
| `$C46B`–`$C472` | wMenuState, wMenuSubState, wMenuSelectedMember, wMenuCursor, wSubMenuCursor(2), wMenuOption(2) |
| `$C945`–`$C948` | wCursorCellX/Y/W/H (cursor hit box) |

Item records are 13 bytes, block at `$16:$4CC2` (file `0x58CC2`); game id `g` at `0x58CCF + 13*(g-1)`. Menu-relevant bytes: rec[3] consume chance %, rec[4] bit 1 = "use does nothing", rec[6] 0/4 → choose a party member, 7 → field item, other → no target, rec[8] bit 1 = key item (discard refused), rec[9] eff_a, rec[10] eff_b (4 heal HP, 7 heal MP), rec[11..12] min/max, 255 = full. Herb heals 30–40 HP, Potion 20–30 MP, ElfWater full MP. Use `$03:$538D` (34 steps), discard `$03:$572D`, sort `$16:$590C` with tables
`$16:$599E` / `$16:$5A0E`; every sort call flips `wInventorySortFlags` (`$C836`) bit 0 (bit 7 keeps the table and clears itself) and the table is picked *after* the flip. WorldDew (id 3) is the only party heal (slots 0–2 to full HP, then consumed by chance); SageRock's rec[4] bit 1 means it never reaches an apply.

Field skills: `FieldSkillNumberBySkillId` `$03:$6700` (ids `$16-$1F`, `$21`, `$24`, `$A2-$A9` → field 0–19), `UseFieldSkill` `$03:$61CE`, `FieldSkillUsable` `$16:$52C9` (table `$16:$52D7`), `FieldSkillEffect` `$16:$53E6` (0–11 heal/MP/revive/cure, 12–19 field return plus talk groups); `PayMP` `$03:$62B2` handles the `$FF` all-MP cost and the skill-30 fizzle `$13`. Text speed: 8 values, ROM default 4, saved as one byte at file `0x3D37` (one past `key_index`); A writes it, Left/Right only move the live copy. GIFT
(bank `$F1`, link gift egg) is **not decoded** — only the far-call entry.

## 2. Name entry

| Item | Value |
|---|---|
| Keyboard | `NameEntryKeyboard` `$14:$6F4E` (cursor table `$14:$61E2`) |
| Rejected list | `$14:$70F0` |
| Tile rectangle | bank `$1F`; layout tables bank `$16` off `0x19C0` (file `0x599C0`), 2 pages, `0xFF`-terminated rows |
| Length | **5 glyphs**; `wNameEntryLength` caps at 4 but the screen has 5 places |
| Monster names | `MON_NAME` record offset `$01`, 10 bytes, `$F0`-padded |
| Default | empty name → Cobi (0) / Tara (1), chosen by `wArg2` = `MON_SEX` |
| Confirm | START, then A on END |

Grid captured live: BG rows 5/7/9/11/13 starting at column 6, tile ids ascending `0x2F..0x5E` in runs of 12/10/13/9/4 (`2F-3A`, `3B-44`, `45-51`, `52-5A`, `5B-5E`), filler `0x0E`. Window map bank `0x33` off `0x0800` (file `0xCC800`) holds window keys `0x23-0x58` as three 18-wide rows over frame tiles `B0-B7/7E/7F/40`, filler `0xC3`; the screen-def stream is `0xE1:0x45A7` (file `0x3845A7`) with palette writes (`68 01`) and `03 xx 0f` row records. **UNKNOWN**: the tile-id → dialogue-charset mapping (the keyboard's
tile ids are its own graphics indices; the dialogue charset is `0x00-0x09` digits, `0x0A-0x23` A–Z, `0x24-0x3D` a–z), so a port must keep the keyboard table; `CheckName`'s in-use/censored rejection and its yes-no prompt are also undecoded. Rename entry (`$0D:$52AB`, mode 3) passes `wArg2 = MON_SEX`; the write-back `$0D:$534E` copies glyphs into `MON_NAME` of the chosen **party** monster.

## 3. Item shop
Script command `$E2` → `ShopMenu` `$1C:$4696` (file `0x70296`). Shop NPCs write `wScreenTableIndex` (`$D7FB`) and `wDataBank` (`$D7FE`) = `$10`, then start the shop script; five handlers are reachable from the talk table — (3,7) `$04:$5A24` → shop 4, (3,32) `$04:$5B99` → 6, (2,18) `$04:$634E` → 3, (7,10) `$04:$6DC9` → 16, (7,60) `$04:$73C7` → 17 — and two (`$04:$7B5F` → 15, `$04:$7B76` → 19) run only from field scripts. Pattern: `3e xx ea fb d7 3e 10 ea fe d7`.

`ShopMenu` jumptables on `wScreenState`: 0 init (clears 0x70 B from `wScreenState`, `wMessageMode` = 2, `wNumberTens` = 0, `wNumberOnes` = 1, `wNumberEditPos` = 1), 1 setup (5 substeps), 2 ChooseAction, 3 Buy, 4 Sell. ChooseAction: `wListLastRow` 0–2 = Buy/Sell/Exit with up/down wrap; A copies the row to `wTwoChoiceCursor`, row 0 → state+1, row 1 → state+2 unless `wListPages == 0` (empty bag) which refuses via `wTwoChoiceCursor = 4`, row 2 → exit; B sets `wTwoChoiceCursor = 2`. Buy runs `wScreenStep` 0–16:
WriteWindowMap, DrawWindow, CountItems, DrawItemNames, PassOneFrame, DrawPrices, ItemCursor, CheckRoom, StartQuantity, EnterQuantity, WriteTotal, DrawYesNo, YesNoCursor (`IsAmountInArg1AboveGold`), DrawTwoBoxes, Pay (`SubtractArg1AmountFromGold`), ClearBoxes, BlankCursors. Sell mirrors it with `ComputeSellPrice` and `AddArg1ToGoldCapped99999`.

| Table | File | Layout |
|---|---|---|
| `ShopItemListTable` | `0x72158` (`$1C:$6158`) | 24 pointers → `$FF`-terminated lists of **1-based** ids |
| `ShopPercentTable` | `0x72320` (`$1C:$6320`) | 24 sell rates |
| `ItemValueTable` | `0x72338` (`$1C:$6338`) | 99 u16 base values |
| `ScreenNumberListTable` | `0x3C9643` (`$F2:$5643`) | 24 pointers → 3 bytes per id (24-bit buy prices) |

**Sell** = `value * percent / 100` (integer). **Buy** comes only from `ScreenNumberListTable` — not derivable from the base value (id 33: 1000 @ shop 2 vs 1500 @ shop 17; id 45 GoldPass 20000 @ shops 2 and 9; max 20000; 497 of 2376 entries non-zero). Rates: 75 for shops 0, 1, 2, 15; 80 for 3, 4, 6–14, 16–23; **0 for shop 5** (empty, like 20–22). Shop 23 stocks 74 items and sells every one for **1 G**. The item record's price field is unused (differs at data ids 83–88, 97). GoldPass in any bag slot multiplies the
**buy** price by 9/10; sell is never discounted. Stock (1-based ids; shop 23 = `01..2E 40..53 5A..61`):

| shop | items | shop | items |
|---|---|---|---|
| 0 | `01 02 06 19 1A 29 2B 53` | 12 | `02 07 0A 1B 28 2A 2B 2E` |
| 1 | `03 04 07 08 09 0A 1B 2E 2B` | 13 | `02 03 04 1B 1C 20 28 2A` |
| 2 | `05 0C 1C 22 23 24 25 1F 21 2D` | 14 | `02 03 04 0C 1C 20 28 2A 2B 2E` |
| 3 | `01 06 09 19 29` | 15 | `01 02 03 04 06 07 08 0A 1B 20 28 2A` |
| 4 | `01 02 06 09 1A 29 2B` | 16 | `01 02 03 05 06 07 08 27` |
| 6 | `02 06 09 1A 1B 28 2A` | 17 | `02 04 0B 1C 20 21` |
| 7 | `02 06 07 08 1A 1B 28 2A 2E` | 18 | `02 03 05 1C 20 24 28 2A` |
| 8 | `02 03 04 0A 1A 28 2A` | 19 | `01 02 04 06 1B 20 28 2A` |
| 9 | `08 0C 1B 2B 2E 1F 21 2D` | 5, 20–22 | *(empty)* |
| 10 | `13 14 15 16 17 18` (books) | 11 | `02 07 0A 1B 29 2A 2E` |

Pinned (game id / base / buy @ shop 0 / sell @75 %): Herb 1/10/10/7, LoveWater 2/50/50/37, WorldDew 3/500/–/400 @80 %, Potion 4/200/–/150, Antidote 6/4/4/3, ShinyHarp 33/1200/1000 @shops 2/900, GoldPass 45/1/20000/0 (18000 discounted). Bag `wInventory` = 24 slots, one instance per slot (`>= $18` = "no room"; 0 items → sell refused). Gold 24-bit `$C617-$C619`, cap 99999 (`AddGoldCapped`: sum ≥ `$0186A0` → `$01869F`), new game 100. SRAM (file = `0x3B0F + (WRAM - $C60C)`): gold `0x3B1A`, banked gold `0x3B1D`, bag
`0x3B20`, vault `0x3B38`, party count `0x3C00`.

## 4. Key services
Appraisal only — no key-combining or key-generating shop exists. `SCRIPT_KEY_APPRAISAL` (bank `$0D`); `KeyAppraisalMenu` states 0 init, 1 DrawGoldBox, 2 ReadAnswer, 3 ChooseKey (18 steps): pick key → "Appraisal will cost 0G. OK?" → pay → appraised; repeats say it was already appraised.

- Price = `10 * (wKeyList[4*i + 3] + 1)` gold.
- `wKeyList` (`$C707`) = 32 × 4 B: byte 0 kind (`$FF` empty, `$FE` generated-unappraised, 0 appraised; fixed/story keys carry their own kinds), bytes 1–2 rolled name bytes, byte 3 level or `$80`|level for fixed/story keys. `PayAndAppraise` clears byte 0 and saves.
- Generation (`GenerateNewKeyEntry`, bank `$12`): first slot with byte 0 = `$FF` (`FindFreeKeySlotToTemp0`; returns `$80` at 32 keys or 20 generated), writes kind `$FE`, then `ComputePartyStrengthForKey` + `RollKeyContentsForLevelTemp0`.

## 5. Breeding and egg services
`BreedMenu` `$15:$40FA` (command `$ED`) is the **party-pair** menu, 19 states: 0 Init, 1 Setup, 2 OptionCursor (Breed/Hatch/Exit via `HandleThreeOptionMenuInput`), 3 DoOption, 4 ChooseParents, 5 ChooseEgg, 6 NameEntry, 7 ReturnToMap, 8 TalkEvent17ThenNameEntry, 9 CopyToChild…, 10 TalkEvent15, 11 RestoreScreen, 12/13 RunStatsScreen, 15 RedrawListScreen, 16 ClearListMarks, 17 ListMonsters, 18 ShowSelectedRecord. State 4 (66 steps): farm monsters (not eggs) → base `wSelectedRecord` → CheckBase → mate list →
`BreedMenu_CopyParentRecords` (`sRecords` → `wRecordBufA`/`wRecordBufB`) → `ComputeBreedingChild` (step 28, kind 0) → yes/no → CheckMate / ChildIsNew / ChildSeen → Breed (step 54) → fee steps 60–65.

Breed deletes both parents (`DeleteSRAMRecordAndCompact`), writes `wChildRecord` into the freed slot and sets the species-seen bit in the library. **Fee = 10 × (`MON_PLUS` + 1)**, same for hatching (`$15:$5504`); `SubtractArg1AmountFromGold` has no floor, so the caller must test `IsAmountInArg1AboveGold`. Egg service (command `$EF`) `EggServiceMenu_Appraise` `$0D:$4988`: **20 G**, then `MON_EGG := 2` (`$0D:$4AFE`), switching the list mark from `$C9` to `$CC + sex`. Field breeders (command `$F4` → `NpcBreedMenu`,
bank `$0D`) take the preset mate from `PresetMonsterRecordTable[wScreenTableIndex]`; `(1,102)` only chats.

Monster record (`$A5` B, SRAM `$A000`, `addr = $A000 + i*$A5 + off`): state `$00`, name `$01`, status `$55`, level `$56`, max level `$57`, HP `$5B`/`$5D`, MP `$5F`/`$61`, ATK `$63`, DEF `$65`, AGL `$67`, INT `$69`, plus `$6D`, egg `$6E`, personality `$6F`, resistances `$73`.

## 6. Inn, vault, swap, hibernate, rename
A handler sets `wDataBank`, then `StartScriptAtHL_B04` `$04:$5603` or `$13:$4049` (19 bytes: HL → `wScriptPointerLo/Hi` `$C91A/B`, `wScriptStartRequest` `$C919` = `$80`, `wModeState` `$C5DC` = 1). Scripts start in bank `$10`; `$E7` continues in `wDataBank`; command table at **`$10:$46F5`** (entry `N` at `$46F5 + 2*(N-1)`; `event_scripts.md`'s `$46F6` is one byte late). Screen routines are state machines on `wScreenState` `$D780` + `wScreenStep` `$D781`, ending with `wScriptCommandType` `$C920` = 0 and
`wScriptStartRequest` = `$80`.

| cmd | stub (file) | Service | Screen routine (file) |
|---|---|---|---|
| `$E0`/`$E1` | `$10:$65BF` (0x425BF) | inn / close | `$1C:$4075` / `$1C:$4001` (0x70075 / 0x70001) |
| `$E2` | `$10:$65CD` (0x425CD) | shop | `$1C:$4696` (0x70296) |
| `$E5`/`$E6` | `$10:$65DB` (0x425DB) | vault / close | `$1C:$6CEF` / `$1C:$6CEB` (0x72CEF / 0x72CEB) |
| `$E8`/`$E9` | `$10:$65E9` (0x425E9) | swap / close | `$1E:$4069` / `$1E:$4001` (0x78069 / 0x78001) |
| `$EB`/`$EC` | `$10:$65F7` (0x425F7) | hibernate / close | `$14:$40CC` / `$14:$4001` (0x500CC / 0x50001) |
| `$ED` | `$10:$6605` (0x42605) | breed | `$15:$40FA` (0x540FA) |
| `$F0`/`$F1` | `$10:$661A` (0x4261A) | rename / close | `$0D:$5159` / `$0D:$50E5` (0x35159 / 0x350E5) |
| `$F7` | `$10:$664B` (0x4264B) | arena | `$0C:$659F` (0x3259F) |

**Inn** — one shared routine, flat **10 G** in every town. `InnMenu_Init_SetPrice` `$1C:$4463` writes `wDigits` = 0,1,0 and the 24-bit price `$D7F7:$D7F8:$D7F9` = 0,0,10 (literal operand of `2e 0a` at `$1C:$446D`). 14 bank-`$10` scripts jump to `$10:$690B` (`e0 | 00 00 c0 | 06 05 | 00 02 80 | e1 ff` …); 13 are reachable from talk handlers — (3,20) (3,44) (2,10) (2,31) (7,61) (9,2) (5,14) (5,40) (5,63) (4,18) (4,54) (4,94) (4,134) — and one (`$10:$608A`) has no known entry point. `$06` = `ScriptFetchSkipIfNo` (skip
N bytes when `wTextYesNoResult` ≠ 0). A stay restores **HP and MP to max** for every party monster whose `MON_STATUS` bit 7 is clear, skips the dead, and does **not** clear the status byte (poison is not cured); nothing checks the party before taking the gold.

**Vault** (`wItemStorage` `$C635`, file `0x3B38`, 200 B): **100 slots** of `{id, count}`, empty = id 0 or `$FF`, count **1..99** (store tests the *sum* against `cp $64`); take-out checks bag slots (`bag + qty > 24` fails; > 24 → message `$C030`). Store scans for the same id or a free slot (`$FF` = full, `$C019`), rejects quantity 0 at the A-confirm, and removes the quantity from the bag at step 14. Take-out addresses a slot `8*row + 2*col` (4 per row), list rows `ceil(count/4)`; quantity is 2 BCD digits, gold 3.
`VaultMenu` states: init, setup, choose action (3 rows), store, take out. Gold side: store refuses a resulting banked total ≥ **999,901** (999,900 fits); take-out accepts a resulting hand total ≤ **99,999**; guards reject a store when hand < 100 or banked ≥ 999,900 and a take-out when banked = 0 or hand ≥ 99,900; the box clamps to 9-9-9 at ≥ 99,900. Banked gold `$C61A-$C61C` (file `0x3B1D`). One talk handler opens it: category 10 group 7 → `$04:$56BD`, flag-gated on `$0025/$0002/$000C/$0007`, ending in `$12:$6B98`
+ script `$10:$4F88`; the vault is `Script_Vault` `$10:$67B5` (371 B).

**Swap** — `SwapMonstersMenu` `$1E:$4069`, **5 option rows** (Drop off / Pick up / Check / Release / Exit, answer 4 = exit; only the row count and exit re-read). Handler `(1,28)` → `$13:$66ED` sets `wDataBank = $1F`; 14 greetings jump to `Script_SwapMonsters` `$1F:$5A3A` (475 B). Drop off writes the chosen party monster as a farm record with `MON_STATE` = 1 and clears its status; pick up searches state-1 non-egg records **inside the farm capacity**. Capacity is `wRecordCapacity` from `wFarmLevel` (`$C7C7`) via
`$1D:$6D81` (identical copy `$16:$75EB`): **10 / 20 / 30** for levels 0/1/2 (`0a 14 1e`); `BattleEnd_AskToJoin_CheckFarmRoom` uses the same table (room iff monsters + eggs < cap). Party list `wPartyList` `$C6FE` = three indexes + `$FF`. **UNKNOWN**: the pick-up/drop-off party-capacity compare and where "Release" leads.

**Hibernate** — `HibernateMenu` `$14:$40CC`, 4 rows (0 hibernate, 1 wake, 3 quit; row 2 undecoded), listing farm monsters that are not eggs. Sleepers become **compact `$6F`-byte records in SRAM bank 1**: **30 slots**, slot `n` (0–28) at file `0x1356 + 0x6F*n`, slot 29 at file `0x2000`; a slot is occupied iff **bit 7 of byte 0** is set. Hibernating swaps one `$A5` record for one `$6F` slot (the full record is zeroed by design); waking needs a free record inside capacity. Pack/unpack `$1D:$6E39` / `$1D:$7492`.

**Rename** — `RenameMenu` `$0D:$5159`: init / draw frame / read answer / draw list / party cursor / enter name (mode 3) / write back. **Party monsters only**, a yes/no prompt first, names ≤ **10 glyphs** (`MON_NAME`, `$F0`-padded). **UNKNOWN**: accepted glyphs, and whether eggs can be listed.

## 7. Arena
Talk `(1,97)` receptionist `$13:$6CB3` starts dialogue chosen by `wArenaRank` (`$C82C`) and flag `$0000` (ranks 0–4 → `$10:$54CE/$550F`, `$54DB/$551C`, `$54E8/$5529`, `$54F5/$5536`, `$5502/$5543`; rank ≥ 5 → message `$0B78`); `(1,101)` class choice `$13:$6D68` sets `wDataBank = $0C`, `wScreenTableIndex` = 0, far-calls `$0C:$6692`. Screen: command `$F7` → `ArenaMenu` `$0C:$659F`, started by `$0C:$7A51` (`f7 e4 08 04 00 …`). Which map trigger runs that script is **UNKNOWN**.

| `wArenaRank` | Flavour | Fee | Reward |
|---|---|---|---|
| 0 | kiddie (states 29–33), fixed teams | free (gold never read/written) | scripted first Magic Key |
| 1–4 | class C/B/A/S (only class `rank-1` enterable) | 100 / 500 / 1000 / 5000 | new random key |
| ≥ 5 | champion loop (state 11), random ladder | 1000 / 2000 / 3000 / 5000 | key / item / gold |

`ArenaMenu_Init` `$0C:$6704` does the branching (`cp $05`, `and a`). A tournament is **3 rounds**, one 3-vs-3 battle each; round counter via `wRecordCapacity` `cp $02` (`$0C:$6A6A`) or `wArenaRound` `cp $02` (`$0C:$6E59`). A round is won iff `wBattleScene` (`$D092`) = 0 (1 = party wiped or foes left, 2 = foes left the scene, 3 = gave up). Each round puts **three foe ids** (6 bytes) into `wEncounterMonsters` (`$CFDD`). Every team value is a **16-bit MonsterTable record id**, not a species id — the 26-byte record
carries level and all six stats, so there is no arena stat table.

| Table | File | Content |
|---|---|---|
| rank-0 teams | `0x3387D`/`0x33885` | word `0x787F`, then {131,132,131} {133,134,135} {136,137,136} |
| `GridEncounterTable` | `0x33897` | C/B/A/S rows → `$789F/$78B7/$78CF/$78E7`; teams at `0x338A5/BD/D5/ED` |
| `ArenaEncounterListSizes` | `0x338FF` | 6 × `$27` (39 drawable) |
| `ArenaEncounterLists` | `0x33905` | L0,L0,L0,L1,L2,L3 → `0x7911/0x7961/0x79B1/0x7A01` |
| ladder lists | `0x33911/61/B1`, `0x33A01` | 40 u16 ids each |
| class fees | `0x33871` | `64 00 F4 01 E8 03 88 13` = 100/500/1000/5000 |
| champion fees | `0x32D44` | `E8 03 D0 07 B8 0B 88 13` = 1000/2000/3000/5000 |
| prize thresholds | `0x335D2` | 6 ptrs + `19 23 2D 37 41 4B 5F 64 FF`, `14 1F 2A 35 40 4B 5A 64 FF`, `0F 17 1F 27 2F 37 50 64 FF`, `0A 15 20 2B 36 41 50 64 FF` |
| prize outcomes | `0x33602` | 6 ptrs + `01 53 05 0C 24 0B 1C 44`, `02 18 0F 10 13 15 45 FE`, `03 0D 11 12 17 2C FD FE`, `23 2C 0D 0E 17 FD 1E FE` |
| random prize items | `0x33538` | 4 ptrs (`$7540/47/4E/55`) + 28 inline bag ids, 7 per list |

The fee is taken **before** the first battle (`$0C:$6A29` → `SubtractArg1AmountFromGold` `$15:$683C`); `wScreenArea = wGridCursorX + 2`, `wAreaGraphicsIndex = wScreenArea`, so class C/B/A/S uses ladder 0/1/2/3 (class letters `$0C:$7037` = C,C,C,B,A,S for areas 0–5). Affordability is `IsAmountInArg1AboveGold` (strictly greater); refusal shows `$C006`.

Ladder draw `$0C:$7326`, byte-exact: (1) clear the 40 usage counters at `$D589`; (2) `RandomModulo52` `$0C:$73B3` = `NextTableByte`, `b = wRandomLo` (`$C5E7`), `q = (((b<<1) & $1F) << 8 | b) / $52` → **0..96**, the quotient not the remainder; (3) `index = q mod 39`, and if that index already appears **3× in this rebuild** advance and fold again; (4) increment the counter, read `u16[list + 2*index]`, store at `$D5B1 + 6*round + 2*slot`. Counters are cleared per rebuild, and the rebuild covers rounds
`wArenaRound..2`, so later rounds are re-drawn after every battle.

Winning all three: `wArenaRank++` (`$0C:$6A8B`, the only store to `$C82C` in the ROM) then `ArenaMenu_GiveRankReward`. The branch tests the **incremented** rank against 1, so the first win (from rank 0) gives the scripted key (`CountKeysOrFull` + `WriteKeyEntryTemp0` kind `$03`, flag `EVENT_ARENA_RANK1_KEY_GIVEN`); later class wins call `GenerateNewKeyEntry` (full ring → `$802B`). Champion `ArenaMenu_PickPrize` (state 39): roll `q`, walk the area's thresholds to the first ≥ `q`, take that position's outcome byte —
`$FE` → new key or **6000 G** (`$0C:$75BC`), `$FD` → one more `RandomModulo52` (`list = q & 3`, `index = q % 7` over `0x33538`), 1..98 → that item, `$FF` → 6000 G. `GiveItem` fills the first empty bag slot; a full bag pays 6000 G instead. Prize ids are bag game ids: items 64–83 and rings 90–97; 84–89 (the six "None" records) never appear.

Losing: `wTwoChoiceCursor` = 2, script ends, `wAreaGraphicsIndex` / `wScreenTableIndex` / `wRecordCapacity` cleared; **rank unchanged**, **no refund**, no prize ("Too bad you didn't make it" `$0025`/`$0026`), and the arena heals the whole party on the way out (bank `$12` `ArenaScene_HealAndLeaveArena`: max → current HP/MP, `MON_STATUS` = 0). No level gate — `ArenaMenu_JudgePartyStrength` only picks one of five sentences from bands ≥80/60/40/30/<30 and writes nothing — and no party-size gate was found.

Result storage: **`wArenaRank` persists as one raw byte at SRAM file `0x3D2F`** (`0x3B0F + ($C82C - $C60C)`), with no clamp, validation or per-field checksum on load (C3: battery 3 → 3, 200 → 200 via a SameBoy harness). Nothing else about a tournament is stored; a new game zero-fills `$C60C`, so rank 0. **UNKNOWN**: `0x33A51–0x33C46` (script-like region pointing into bank-`$0C` code, interpreter not located); the older "{species, level} pairs" reading of `0x33A01` is superseded by the record-id reading.

## 8. Card game and casino ship
Both are traveler events, not menus. **Card game** (kind 6, `$73:$4647`): no entry fee; mark starts at 6 (displays 7); each round draws `wKeyRandomLo & $0F`, re-drawn while ≥ `$0D` (0–12 shown 1–13); a **tie always loses to the house**; five rungs, 5 prizes max. Prizes `0x1CC822` = `03 22 28 2A / 0B 25 05 2B / 0C 23 27 2C / 11 12 26 1E / 0D 0E 0F 10` (row picked by wins, column by `wKeyRandomLo & 3`); stakes `0x1CC836` = 100/300/600/1000/1500. A loss subtracts the current stake with a bare 24-bit `sub/sbc`
**without a floor** (wraps below zero); quitting pays the last won prize.

**Casino** (kind 10, `$73:$411F`): **100 G** charged first through `SubtractGoldFloorZero` (`$12:$7E84`), which floors only when `wGoldHi != 0` — so accepting with < 100 G wraps the purse to ~`$FFxxxx`. Three reels, each a byte = symbol index (high nibble) + scroll offset (low nibble), seeded `(wKeyRandomHi & 7) << 4`; 30 free frames (A ignored), then each A press advances the stop cursor; `AdvanceReels` runs on odd frames (+2/+1/+4), a reel locks when its low nibble is 0. Payout is by **symbol**
(`0x1CC53A/44/4E`): reels 1–2 differ → nothing (`$35`); first two equal → sym0 +100 G (`$46`), sym1 +50 G (`$47`); all three equal → sym0 MeteOrb `$1E`, sym1 TinyMedal `$2C`, sym2 +1000 G, sym3 +500 G, sym4 +200 G.

## 9. Town events that open services
`RunPeriodicFieldEventChecks` (`$12:$75E0`) runs after every completed field step and bails if `wScriptRunning` (`$C91F`) ≠ 0 or `wPendingFieldEvent` (`$C935`) bit 7 is set. It rolls only on `hMapId` `$20 $30 $48 $70 $A8 $B0 $B8 $C8`, or on the key world (`wMapType` bit 7 and `& $7F` = `$80`). `wTownEventTimer` (`$C832`) counts up per qualifying step; at `cp $63` (99) it resets to 0 and the chain runs — a deterministic **once per 100 steps**, not a random roll. The chain is a fixed priority list of 14 `call … ; ret
c`, first hit wins:

| # | kind | gate | # | kind | gate |
|---|---|---|---|---|---|
| 1 | `$CC` | flags `$192`/`$193`, gold ≥ 10000 | 8 | `$C3` | gold ≥ 5000, last slot free, gold digit-sum ≥ 30 |
| 2 | `$CD` | flags `$195`/`$196`, ΣHP < 100 | 9 | `$C6` | `wEventItemSlot` free, gold ≥ 5000 |
| 3 | `$CE` | flags `$198`/`$199`, ΣMP < 100 | 10 | `$CB` | gold ≥ 1000, member status bit 7/2/0 |
| 4 | `$CF` | flags `$19B`/`$19C`, Σlevel < 100 | 11 | `$C7` | slot free, gold ≥ 1000, no `$19-$1C` in bag |
| 5 | `$C0` | a member's HP digits all equal | 12 | `$C8` | slot free, gold ≥ 1000, ΣHP ≤ (ΣmaxHP/100)*30 |
| 6 | `$C1` | gold ≥ 1000, last slot free, gold digit-sum ≤ 12 | 13 | `$C9` | gold ≥ 1000, a member's EXP last 3 digits equal |
| 7 | `$C2` | gold ≥ 1000, first `min(3,n)` HP end same digit | 14 | `$C4`/`$C5` | gold ≥ 1000, last slot free, `NextTableByte` parity |

`wEventItemSlot` (`$C627`) is **bag slot 10** (`$C627 - $C61D`): `$C6/$C7/$C8` need *that* slot empty; "last slot free" is `$C634` (`wInventory+$17`). The `$19-$1C` scan stops at the first empty byte, so items behind a hole are invisible. Placement (`$12:$7BFF`): kinds 1/3/4/5/7 with the last slot taken cancel and re-run the chain; otherwise one of four spots (`wRandomHi & 3` over `20 20 70 60 20 60 70 20`), sprite from `0x4BD46` (`12 15 3d 3e 10 11 17 15 14 13 57 12 15 12 14 10`), then the tall-tile roll
(`$12:$7CD9`: 1-in-8 `wKeyRandomHi & 7`, needs TinyMedal `$2C` **present**, last slot free, gold ≥ 100) which stores `($C935 & $F0) | $0A`.

Dispatch `TravelerEvents` `$73:$4001` (`ld a,[$C935]; and $0F; rst $00`), table `$73:$4007`, 16 entries → 13 scenes: 0 Healer `$4E03` · 1 Merchant `$4D8D` · 2 PaidHealer `$4D20` · 3 PriceyMerchant `$4CA0` · 4 WanderingMaster `$4BC3` · 5 TravelingMaster `$4B68` · 6 CardGame `$4647` · 7 RewardBattle `$4A82` · 8 MapSeller `$45D0` · 9 MedicineMaster `$4840` · 10 CasinoShip `$411F` · 11 HealerBattle `$4098` · 12–15 Thief `$4027`. Entry is through the script interpreter: talk category 8 → `$13:$593A` →
`Script_TravelerEvent` `$10:$512D` = opcode `$82` → `farcall TravelerEvents`. Effects: Healer free full heal; Merchant one item at 1× price; PaidHealer −1000 G + heal; PriceyMerchant 5×; MapSeller −200 G and all 8 `wVisitedScreens` bytes ← `$FF`; MedicineMaster +20 to each survivor's lowest stat (cap 999, offsets `$5D/$61/$63/$65/$67/$69`); Thief sets flag `$193/$196/$199/$19C` by kind. Any lost battle runs `DeductGoldPenalty`: gold < 150 → lose all, 150–1499 → 150, ≥ 1500 → `floor(gold/10)`. Merchant item pick,
first affordable: dead member → WorldLeaf `$0C`; status bit 0 → Laurel `$08`; poison → Antidote `$06`; party < 3 → meat by record count (<3 BeefJerky `$19`, 3–5 PorkChop `$1A`, 6–10 Rib `$1B`); missing MP ≥101 ElfWater `$05`, 1–100 Potion `$04`; missing HP ≥101 WorldDew `$03`, 51–99 LoveWater `$02`; else Herb `$01` (no price gate). `CanAffordItem` multiplies by 5 except for kind 1.

## 10. Library, medals, priest — not decoded
Commands `$F3` medal_prizes, `$F6` library and `$F8` priest exist as command types, but no screen decode for the monster library, the medal exchange or the priest exists. Known only: library text is a 498-string block (pointer table `0x2C03E`, strings `0x2C422`, bank `$0B`); library aux tables at `0x03136A` (sizes, `0x175B` B), `0x031562` (rarities), `0x03199F`/`0x031C9F` (upper breed partner + copy) and `0x031F9F`/`0x03229F` (lower, `0x300B` each), never extracted or validated; the species-seen bit is set by
`SetSpeciesFlag`; egg marks are `$C9` (unappraised) / `$CC + sex` (appraised). TinyMedal is item `$2C`, base value 1, exchange prices undecoded. A port must treat these screens as **unknown**, not as absent.

## 11. Exact-match checklist
1. Pagination: 4 rows/page, `page_count = ceil(n/4)` min 1, `last_page_rows = n%4 || 4`; skills 0/1–4/5–8 → 0/1/2 pages.
2. Cursor: row wrap over `wMenuRowCount`; page wrap only when `wMenuPageCount >= 2`; row clamped to `wMenuLastPageRows - 1` on the last page; bit 7 = page changed; blink at `(wFrameCounterLo & $1F) == $10`.
3. PLAN order Keys, Tactics, Text speed, Re-order, Info, Journal; A opens `entry+1`; B exits to the field; labels are graphics.
4. Journal gate: special map → `wEncounterRate & $7F`; else `MapItemUseFlags[hMapId]` bit 4.
5. Shops: 24 shops, buy price only from `ScreenNumberListTable`, sell = `value * percent / 100`, GoldPass 90 % buy-only, shop 5 empty at 0 %, shop 23 everything at 1 G, bag 24, gold cap 99999.
6. Inn: flat 10 G, HP/MP to max, skip the dead, never touch the status byte.
7. Vault: 100 × `{id, 1..99}`, bag 24, limits 999,900 banked / 99,999 hand, slots `8*row + 2*col`, 2-digit quantity, 3-digit gold.
8. Keys: appraisal `10 * (level + 1)`; `wKeyList` 32 × 4 with kinds `$FF/$FE/0` and level-or-`$80` byte 3; ceiling 20 generated / 32 total.
9. Breeding: fee `10 * (plus + 1)` for laying and hatching; both parents deleted and compacted; child into the freed slot; egg appraisal 20 G sets `MON_EGG` = 2.
10. Arena: 3 rounds, win iff `wBattleScene` = 0; fees 100/500/1000/5000 and 1000/2000/3000/5000, rank 0 free; ladder = quotient (not remainder) mod 39 with a 3-use cap per rebuild; rank byte `0x3D2F` unclamped; first win from rank 0 gives the scripted key; 6000 G fallback; a loss costs the fee, keeps the rank and heals the party.
11. Gambling: card ties lose, stakes 100/300/600/1000/1500, 24-bit subtract without a floor; casino charges 100 G up front and wraps the purse if short.
12. Town events: once per 100 counted steps, only on the eight town maps plus key world `$80`, in the fixed 14-check priority order.
13. RNG: everything above consumes `NextTableByte`/`NextRandomSeed` and reads `wRandomLo/Hi` (`$C5E7/$C5E8`) or `wKeyRandomLo/Hi` (`$CD03/$CD04`). Draws are `& $0F` (cards), `& 3` (spots, prize column), `& 7` (casino seed, tall-tile 1-in-8) and the `RandomModulo52` quotient. Matching the addresses without matching this byte stream desynchronises every random shop, prize and event.
14. Name entry: 5 glyphs, keyboard `$14:$6F4E`; `MON_NAME` 10 B `$F0`-padded; empty name → Cobi/Tara by `MON_SEX`; confirm is START then A on END.

## Sources
- `re/notes/pause_menu.md`, `re/notes/pause_menu_handoff.md`
- `re/notes/shop_ui.md`, `re/notes/shop_key_breeding.md`
- `re/notes/town_services.md`, `re/notes/town_events.md`, `re/notes/traveler_events.md`
- `re/notes/name_entry.md`, `re/notes/card_casino.md`
- `re/notes/arena_tournament.md`, `re/notes/arena_rank.md`, `re/notes/arena_teams.md`, `re/notes/arena_data.md`, `re/notes/arena_tail.md`, `re/notes/arena_remap.md` (superseded: that cluster is `ComputeBreedingChild`, not an arena remap)
- `re/notes/event_scripts.md`, `re/notes/breeding_egg.md`, `re/notes/text_encoding.md`, `re/notes/graphics.md`, `re/notes/game_data.md`
