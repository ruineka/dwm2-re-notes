# 2. Memory map

The annotated disassembly defines **957 named WRAM/HRAM/SRAM symbols**; this
file lists the ones a reimplementation actually needs. Names are the
disassembly's (`w…` = work RAM, `h…` = high RAM, `s…` = cartridge RAM).

Quick orientation: `$C000`–`$DFFF` is WRAM (bank 0 default), `$A000`–`$BFFF` is
cartridge RAM (see `03-sram-save-format.md`), `$FF80`–`$FFFE` is HRAM.

## Boot, modes, frame control

| Address | Name | Meaning |
|---|---|---|
| `$C5DB` | `wGameMode` | index into the 9-entry game-mode tables (see `04-engine-core.md`) |
| `$C5DC` | `wModeState` | which screen or step runs inside that mode; the debug menu and the pause menu reuse it as their own sub-screen index |
| `$C5DD` | `wWorldMapState` | world-map screen state (field state 8) |
| `$C5DF` | `wModeChangeRequest` | non-zero asks the main loop to leave its mode wait and run `RunGameModeInit` again |
| `$C5DE` | `wGameMode2Arg` | argument for game mode 2 |
| `$DFFF` | `wStackTop` | stack starts here (`ld sp,$DFFF`) |
| `$C525` | `wIsCGB` | 1 when boot found CGB hardware |
| `$C524` | `wSGBActive` | 1 at boot; cleared on CGB or when SGB detection fails |
| `$C526` / `$C527` | `wBGPaletteUploadRequest` / `wOBJPaletteUploadRequest` | ask the VBlank handler to upload the palette buffers |
| `$C49F` | `wBGPaletteBuffer` | 8 CGB BG palettes (64 B) used by the fade routines |
| `$C4DF` | `wOBJPaletteBuffer` | 8 CGB OBJ palettes (64 B) |
| `$C0F0` | `wBGPaletteCopy` | BG palette copy for screen-flash effects; the STAT scroll wave indexes it with `rLY` up to `$8F`, so it is at least `$90` bytes and overlaps `$C130` onward |
| `$C5E9`–`$C5EB` | `wDMGPaletteBGP` / `wDMGPaletteOBP0` / `wDMGPaletteOBP1` | the three DMG palette bytes `CopyDMGPalettesToHardware` pushes to `rBGP`/`rOBP0`/`rOBP1` |

## VBlank queues and OAM

| Address | Name | Meaning |
|---|---|---|
| `$C000` | `wShadowOAM` | 40 OAM entries (4 B each), copied by the HRAM DMA routine |
| `$FF80` | `hOAMDMARoutine` | the OAM-DMA stub the boot code installs |
| `$C0C0`–`$C0C4` | `wBGWrite*` | queued BG-map write: destination lo/hi, vertical flag, count, data (≤20 tiles) |
| `$C0D8`–`$C0DC` | `wAttrWrite*` | queued CGB attribute write (VRAM bank 1), same shape |

## Text printer

| Address | Name | Meaning |
|---|---|---|
| `$C528`–`$C52A` | `wStringCategory` / `wStringIndex` / `wStringBank` | which string `LookupString` resolved (table of tables) |
| `$C52B` / `$C52C` | `wTextFlags` / `wTextControl` | non-zero = text is live; control bits (bit 7 continues, bit 0 = prompt) |
| `$C52D`–`$C530` | `wTextWindowTile(Lo/Hi)`, `wTextWindowRows` (default 2), `wTextWindowWidth` (default 18) | where the printer draws |
| `$C531`/`$C532` | `wTextGlyphDestLo/Hi` | current glyph destination in VRAM |
| `$C533`/`$C534` | `wTextPosLo/Hi` | pointer to the next string byte |
| `$C535`–`$C538` | `wTextLineStart*`, `wTextStartPos*` | line start and prompt-return position |
| `$C539` | `wTextControlArg` | argument byte after a control code |
| `$C53C` | `wTextDelayCounter` | countdown before the next glyph |
| `$C54F` | `wTextGlyphTimer` | frames since the last glyph (reveal speed) |
| `$C552` | `wTextYesNoResult` | result of a yes/no prompt |
| `$C554`/`$C555` | `wTextCursorLo/Hi` | BG address where the next text row starts |
| `$C556` | `wTextBeepSound` | sound effect per character (`$6B`) |
| `$C130`–`$C160` | `wTextBuf0`–`wTextBuf3` | 16-byte name slots substituted into messages (actor, skill, target, extra) |
| `$C17E` | `wTextNumber` | formatted number string |

## Input

| Address | Name | Meaning |
|---|---|---|
| `$C55D` | `wJoypadReadFlag` | cleared before a direct joypad read |
| `$C55E` / `$C55F` | `wJoypadHeld` / `wJoypadHeldPrev` | current and previous buttons |
| `$C560` | `wLinkJoypadHeld` | the other player's buttons (link or SGB pad 2) |
| `$C474`/`$C476` | `wSGBJoypad1/2` | SGB pad bytes |

## Player and field (HRAM)

| Address | Name | Meaning |
|---|---|---|
| `$FF90` | `hMapId` | current map (index into `MapTable`, bank `$11`) |
| `$FF8F` / `$FF92` | `hMapScreenX` / `hMapScreenY` | current screen within the map |
| `$FF8E` / `$FF91` | `hPlayerX` / `hPlayerY` | player position in **pixels** within the screen |
| `$FF98` | `hPlayerFacing` | 0 down, 1 right, 2 up, 3 left |
| `$FF8B` | `hPlayerSpriteMode` | sprite mode 0–2 (from story flags) |
| `$FF8A` | `hPlayerSpriteVariant` | part of the saved HRAM block; drives the hero-sheet choice |
| `$FF93`–`$FF97` | `hPlayerSpriteOverride`, `…GfxIdLo/Hi`, `…TimerLo/Hi` | temporary graphics override |
| `$FF99` | `hPlayerAnimCounter` | animation counter (+1/frame, +3 more while moving) |
| `$FF9A` | `hPlayerTurnDelay` | frames to wait after turning in place (4) |
| `$FF9B`–`$FF9E` | `hPlayerStepDX/DY (Lo/Hi)` | 16-bit step delta per frame |
| `$FF9F`/`$FFA0` | `hWindowX` / `hWindowY` | copied to `rWX`/`rWY` |
| `$FFA1`/`$FFA5` | `hScrollX` / `hScrollY` | 16-bit scroll origins (hi bytes at `+1`), copied by the LCD handler |

Map header copies (loaded by `LoadMapHeader` from the map record):

| Address | Name | Meaning |
|---|---|---|
| `$C190`/`$C191` | `wMapWidthScreens` / `wMapHeightScreens` | map size in screens |
| `$C192` | `wMaxBlockingTile` | highest tile id that blocks the player |
| `$C193` | `wMapHeaderByte7` | read by `CheckInteractionInFront` |
| `$C194` | `wMapMoveType` | selects the player movement routine |
| `$C195` | `wMapSpriteKind` | high nibble = script sprite set, low nibble 1 = follower-style sprite |
| `$C196` | `wMapTallTileMin` | tall-tile threshold: tile ids strictly **above** it are tall (the comparison is `tile > min`) |
| `$C197` | `wMapEventTile` | tile that fires the header talk event when faced |
| `$C198` | `wScreenTileBuffer` | `$240`-byte tile buffer of the current screen; field code indexes it with 20-byte rows (`(Y>>3)*20 + (X>>3)`), while the 32-byte row copies are the menu/window path |
| `$C300` | `wWindowTileBuffer` | 20×18 window/menu tile buffer |
| `$D000` | `wScreenAttrBuffer` | WRAM bank 2: CGB attributes for the screen buffer |
| `$D168` | `wWindowAttrBuffer` | WRAM bank 2: attributes for the window buffer |

Field actions and triggers:

| Address | Name | Meaning |
|---|---|---|
| `$C468`–`$C46A` | `wFieldActionRequest`, `wFieldActionStep`, `wScreenScrollDir` | screen-scroll / field-action request |
| `$C900` | `wTriggerIndex` | index of the active trigger entry |
| `$C90D`–`$C90F` | `wFieldEventKind`, `wFieldEventTimer`, `wFieldEventArg` | per-map field event |
| `$C910` | `wTilesUnderPoint` | the 2×2 tile block under a point (collision) |
| `$C916`/`$C917` | `wTalkEventGroup` / `wTalkEventIndex` | which talk event to dispatch |
| `$C918` | `wStepTriggerFlag` | step triggers already scanned for this step |
| `$CC47` / `$CC48` | `wMapObjectCount` / `wMapObjects` | map objects (8 B each) for town and key-world maps |
| `$CCE9` / `$CCEB` | `wScreenTriggerCount` / `wScreenTriggers` | 4-byte screen trigger entries |
| `$CCEA` | `wWarpPending` | set by the warp routines |
| `$C88B` | `wLastWarpIndex` | index of the last warp taken |
| `$C901`/`$C902` | `wEncounterRate` / `wEncounterCountdown` | random-encounter pacing |
| `$D091` | `wEncounterDelay` | delay before encounters count again |

## Sprites / meta-sprites

| Address | Name | Meaning |
|---|---|---|
| `$FFAD` | `hSpriteSetIndex` | first-level index into the meta-sprite table |
| `$FFAE` | `hSpriteSubIndex` | second-level index (frame) |
| `$FFA9`/`$FFAB` | `hSpriteOriginX` / `hSpriteOriginY` | 16-bit object origin (added to every entry) |
| `$FFAF` | `hSpriteTileOffset` | added to each entry's tile number |
| `$FFB0` | `hSpriteAttrXor` | XORed into each attribute byte (flips/palette) |
| `$FFB1` | `hOamNextEntry` | next OAM entry the builder writes |
| `$FFB3`–`$FFB8` | `hMetaSprite*` | meta-sprite builder work (origin ± scroll, flipped origin) |
| `$FFD2`–`$FFD5` | `hSpriteScrollX/Y (Lo/Hi)` | scroll offsets for sprites, computed per frame |
| `$CB7D`/`$CB7F` | `wSpriteSlotCount` / `wSpriteSlots` | object slot array, **16-byte slots in field mode** (the 8-byte layout is the bank-`$E0` intro drawer) |
| `$CB8F`–`$CBBF` | `wObject1`–`wObject4` | four 16-byte field objects |
| `$CBCF` | `wObject5` | script meta-sprite object (byte 0 bit 7 = shown) |
| `$CB75`/`$CB76` | `wSequencePtrLo/Hi` | running animation sequence |

## Records, party, inventory, money, story

| Address | Name | Meaning |
|---|---|---|
| `$C60C` | `wPlayerName` | 10-byte player name |
| `$C616` | `wPlayerId` | random id chosen at new-game |
| `$C617`–`$C619` | `wGoldLo/Mid/Hi` | 24-bit gold |
| `$C61A`–`$C61C` | `wBankedGold*` | second 24-bit amount (bank) |
| `$C61D` | `wInventory` | 24 one-based item ids |
| `$C635` | `wItemStorage` | the vault: 100 × `{id, count}` |
| `$C6FD` | `wPartyCount` | 0–3 |
| `$C6FE` | `wPartyList` | record indices of the party (`$FF` terminated) |
| `$C707` | `wKeyList` | up to 32 four-byte key entries (`$FF` ends) |
| `$C787` | `wKeySeeds` | two bytes per key: the seed the world is generated from |
| `$C7C7` | `$C7C7` `wFarmLevel` | how many SRAM records the farm holds |
| `$C7CC` | `wSpeciesFlags` | owned-species bitmap (47 B); the library's per-family counts are its set bits, and nothing reads a separate "seen" bit |
| `$CBD7` | `wStoryFlags` | story flags: flag *n* = bit `n&7` of byte `$CBD7 + n/8` |
| `$C82D`–`$C831` | `wPlayFrames/Seconds/Minutes/Hours` | play time |
| `$C833` | `wCurrentKeyIndex` | key entry in use |
| `$C834` | `wBattleTextSpeed` | saved text speed |
| `$C837` | `wGameCompleted` | set when the ending shows |
| `$C838`/`$C839` | `wTinyMedals` | TinyMedal count |
| `$C832` | `$C832` `wTownEventTimer` | periodic field-event timer (0–99) |

The 30 monster records themselves live in SRAM, not WRAM; working copies are
the `$A5`-byte buffers `wRecordBufB $CA2B` (second parent / partner) and
`wChildRecord $CAD0` (breeding result).

## Script VM

| Address | Name | Meaning |
|---|---|---|
| `$C919` | `wScriptStartRequest` | bit 7 = start the script at `wScriptPointer` |
| `$C91A`/`$C91B` | `wScriptPointerLo/Hi` | next script byte |
| `$C91C`–`$C91E` | `wScriptReturn*` | saved script position for a return |
| `$C91F` | `wScriptRunning` | non-zero while a script runs |
| `$C920`–`$C922` | `wScriptCommandType`, `wScriptParam0/1` | the command being run |
| `$C923` | `wScriptStep` | step counter inside the command |
| `$C924`/`$C925` | `wMessageIndex` / `wMessageGroup` | message selection (group bits 0–5, bit 7 skips box) |
| `$C926` | `wMessageState` | message box state (`$FF` idle) |
| `$C927` | `wFieldInitFlag` | set by script command `$9F`, read by `InitFieldScreen` |
| `$C928`–`$C92A` | `wStepPtr*`, `wStepTarget` | coordinate stepping used by movement commands |

## Generic menu / list state (shared by nearly every screen)

`wMenuState $C46B`, `wMenuSubState $C46C`, `wMenuSelectedMember $C46D`,
`wMenuCursor $C46E`, `wSubMenuCursor $C46F`, `wSubMenuCursor2 $C470`,
`wMenuOption $C471`, `wMenuOption2 $C472`; and for paged lists:
`wListCursor $D7AB`, `wListPageIndex $D7AF`, `wListPages $D7B0`,
`wListLastRow $D7B1`, `wListCount $D7A9`, `wListEntries $D789`.
Screen-level state: `wScreenState $D780`, `wScreenStep $D781`,
`wScreenSubStep $D782`, `wScreenCounter $D783`, `wReturnScreenState $D7B2`.
Pause menu: `wPauseMenuScreen $C0A4`, `wPauseMenuStep $C0A8`,
`wPauseListCount $D0C7`.

## Battle state (summary — see `07-battle-system.md` for semantics)

| Address | Name |
|---|---|
| `$CFC5` | `wBattleKind` (0–1 ordinary, 2–5 special) |
| `$CFC8`–`$CFCB` | `wBattlePhase`, `wBattleStep`, `wBattleSubPhase`, `wBattleResolveStep` |
| `$D0D5` | `wBattlerRecords` — six 78-byte battler records |
| `$D90F`/`$D91F`/`$D92F` | `wBattleDEF` / `wBattleAGL` / `wBattleINT` (one word per slot) |
| `$D958` | `wBattleMonsterId` (word per slot) |
| `$D989` | `wBattleSkills` (16 B per slot) |
| `$DA1C` | `wBattleActionChoice` (word per slot: action, target) |
| `$DA72` | `wSlotResistances` (7 B per slot: 27 two-bit levels) |
| `$D80C` | `wBattleStatus` (9 B per slot) |
| `$D872`/`$D873` | `wBattleDamage` (16-bit) |
| `$DA6B` | `wBattleExpAward` (24-bit) |
| `$D2AD` | `wAIWeights` (ten words) |

## Key worlds

`wKeyWorldSlot $CC42`, `wKeyWorldArea $CC43`, `wMapType $CC44`,
`wKeyWorldFloor $CC45`, `wKeyWorldActive $C88E`, `wKeyWorldGoal $C88F`,
`wKeyWorldKey $C891`, `wKeyWorldBand $CD0F`, `wKeyWorldWidth/Height $CD0D/$CD0E`,
`wKeyWorldMonsters $CD10` (32 entries), `wKeyWorldChunks $CD60`,
`wKeyWorldAreas $CD70`, `wKeyWorldRoomTable $CE2C`, `wKeyWorldEncounterTable $CE7B`,
`wVisitedScreens $CE93`.

## Link cable

`wLinkRole $C57F`, `wLinkStatus`/`wLinkMode` (`$C57F` onward), `wLinkSetting $C894`,
`wLinkPartnerName $C5B7`, `wLinkTradeByte $C5C6`, `wLinkFightInfo $C963`,
`wLinkExchangeBuffer $D200`, `wLinkRules $D043`, `wLinkRuleTurnLimit $D04B`,
`wLinkReceivedByte $D065`, `wLinkSeedCopy $D05A`.

## Sound

`wCurrentMusic $C608`, `wMusicRequest $C60A`, `wSoundEffectRequest $C60B`;
six $20-byte channel slots `wSoundChannelSlots $DC00` … `wSoundChannel5 $DCA0`;
the engine copies the active channel into HRAM (`$FFD8`–`$FFF6`) while it runs.
