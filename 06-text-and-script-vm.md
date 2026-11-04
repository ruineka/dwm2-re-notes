# 6. Text, the script VM, talk events and story flags

Two byte-code layers drive dialogue and events. The **bank-0 text printer** walks a `$F0`-terminated string byte by
byte, runs `$E0`–`$FF` commands and copies 16-byte glyph tiles into VRAM (one glyph per N frames). The **event-
script VM** in bank `$10` runs one opcode per frame and drives movement, messages, warps, flags and the
shop/inn/vault/arena screens. Text is **not** compressed. Addresses are `$BB:AAAA` (file = `bank*0x4000 +
addr-$4000`), RAM `$Cxxx`/`$FFxx`, SRAM `.sav` offsets `0x…`; *unconfirmed* = inferred only.
## 6.1 Character set
One byte = one glyph. `$00`–`$B8` is text, `$B9`–`$DF` is unused in the US build, `$E0`–`$FF` are commands (§6.3).
`src/charmap.inc` is the authority.

| Codes | Contents |
|---|---|
| `$00`–`$09` | digits `0`–`9` |
| `$0A`–`$23` / `$24`–`$3D` | `A`–`Z` / `a`–`z` |
| `$3E`–`$47` | contractions `'s 'm 'r 't 'v 'l 'd` (one byte each), `*:` (two characters), `(I)`, `(II)` |
| `$50`–`$5E` | pictures `[1]`–`[15]` (US build only) |
| `$88`–`$91` | `°`, `◦`, `$8A`–`$8F` unused, space (`$90`), cloud |
| `$92`–`$9D` | `%`, `..`, `;`, `'`, `「`, `」`, `?`, `!`, full-width comma, `•`, `-`, `~` |
| `$9E`–`$A8` | `/`, `*`, `(`, `)`, `+`, `:`, `…`, `Lv`, `Ex`, `♂`, `♀` |
| `$A9`–`$B8` | `↑`, `"`, half-width comma, `★`, `↓`, `←`, `→`, `↖`, `↗`, `↙`, `↘`, `zz` (sleep), `.`, `&`, `’`, `©` |
| `$8D`/`$8E`, `$E5`/`$E9` | combining marks OR-ed into the previous tile (the overlay also clears bit 1 of byte 4); `[`/`]` bracket glyphs, e.g. `E5 58 F7 E9` = "[icon]" around a wait |

* `$00` is `'0'`, so **zero is never a blank/pad glyph**; unused digit cells stay undrawn instead of being filled with
  `$00`.
* Japan uses `$50`–`$8C` for kana and `$8D`/`$8E` as dakuten/handakuten; the US build replaced that range
  with the pictures above.
* Glyph tiles: `GlyphFont = $1F:4010`, 256 tiles × 16 B, 2bpp, `tile(c) = $1F:4010 + 16*c`
  = `bank1F[$4010 + (c>>4)*$100 + (c&$0F)*$10]`. Bank-`$24` scene text has its own proportional path (`$24:$7045` per-
  glyph string renderer, `$24:$64AB`+ box state machine, layout tables `$25:401E`/`$25:411E`, terminator `cp $80`);
  that bank is `$24`, not `$18`.
## 6.2 The text engine (bank `$00`)

| Routine | Address | Job |
|---|---|---|
| `StepTextPrinter` / `PrintTextStep` | `$00:$2620` / `$00:$2637` | per-frame entry (one step if `wTextControl` bit 7 clear, else one step per loop while it stays set); one frame of the printer |
| `BeginStringDisplay` / `LookupString` | `$00:$25C9` / `$00:$2E40` | blank window, set cursors from the window tile, resolve the string, `wTextFlags = 1`, `wTextControl = 0`; resolver: bank byte at CPU `$4000` → `wStringBank`, category word, string word |
| `FillTilesFromRequest` / `RunTextCommand` | `$00:$290E` / `$00:$2950` | blank the window tiles; `ld [wTextLastChar],a; sub $E0; rst $00` → 32-word table at `$00:$2956` |
| `DrawTextGlyph` / `DrawTextMarkGlyph` / `GlyphTileSourceForL` | `$00:$287F` / `$00:$28AB` / `$00:$28F4` | copy glyph `A`'s 16 bytes to `wTextGlyphDest` and advance it by `$10`; overlay `$8D`/`$8E` at `dest-$10`; `DE = $1F:4010 + 16*A` |
| `HLToDecimalDigits` / `Number24ToPackedBCD` / `WritePackedBCDNoLeadingZeros` | `$00:$16F5` / `$00:$173A` / `$00:$23CA` | `HL` (0–999) → three digit codes at `wDigits`; 24-bit `wDigits` → packed BCD in `hTemp0`–`hTemp3`; write as digit codes + `$F0` to `DE`, no leading zeros |

The VBlank handler calls `StepTextPrinter` while `wTextFlags` is non-zero. `PrintTextStep` pushes the bank-number
byte (`ld a,[$4000]; push af`), maps `wStringBank`, and on every exit restores the bank and increments
`wTextGlyphTimer`. One step, in order: (1) `wTextControl` bit 2 = sound wait, cleared only when every channel slot
in the `$DC00` block reads `$FF`; (2) `wTextFlags` = 0 → nothing; (3) bit 5 → blink the wait arrow (tile `$BD`/`$B4`
by `wFrameCounterLo` bit 4, three rows below the cursor, nine columns in); (4) bit 2 → choice input: up/down toggles
`wTextYesNoResult` (sound `$69`), `A` or `B` accepts (`B` = 1) and the screen buffer is redrawn, while after
`<WAIT>` any newly pressed button except bit 3 ends the wait; (5) bit 6 counts `wTextRepeatCount` down or ends on a
button, bit 7 counts `wTextDelayCounter` down; (6) else the next byte: `$8D`/`$8E` → mark, `$E0`–`$FF` → command,
else a glyph.

Reveal speed (must match): a glyph is drawn only when `wTextGlyphTimer` reaches `wTextSpeed` (`$C964`; **0 acts as
1**) or the `<SPEED>` argument, and not under `<FAST>`. New game = 1; battle setup copies
`wBattleTextSpeed` (`$C834`, saved; 3 in link battles); battle end sets 1.

`<PAUSE>` does **not** use `wTextSpeed`. It indexes a seven-entry table of frame counts at `$2A66` —
`$06 $0C $14 $1A $20 $28 $30` for arguments 1–7 — so short pauses are 6–48 frames, and only the
seventh argument waits for a button. A button pressed while waiting for a glyph turns on `<INSTANT>` (`wTextControl` bit 7),
printing the rest at once. Each 16-byte copy waits on `rSTAT` bit 1, so writes land in the VBlank-safe window.
Window defaults: 2 rows × 18 columns at `vTiles1 = $8800`.

| Var | Meaning |
|---|---|
| `wStringCategory` `$C528`, `wStringIndex` `$C529`, `wStringBank` `$C52A` | resolved string / its bank |
| `wTextFlags` `$C52B` | non-zero = text live; bit 1 fast/active, bit 2 prompt, bit 5 arrow, bits 3/4/6/7 per command |
| `wTextControl` `$C52C` | bit 0 beep, bit 2 sound wait, bit 6 repeat, bit 7 instant/continue (bit 1 is unused) |
| `wTextWindowTile` `$C52D/E`, rows `$C52F`, width `$C530` | where the box draws (next row = `dest + 16*width`, `$00:$2C21`) |
| `wTextGlyphDest` `$C531/2`, `wTextPos` `$C533/4`, `wTextLineStart` `$C535/6`, `wTextStartPos` `$C537/8` | next glyph VRAM address, next string byte, row start, prompt return |
| `wTextControlArg` `$C539`, `$C53B`, `wTextDelayCounter` `$C53C`, `wTextGlyphTimer` `$C54F`, `wTextLastChar` `$C550`, `wTextYesNoResult` `$C552`, `wTextCursor` `$C554/5`, `wTextBeepSound` `$C556` | control-code operands, glyph timer, last command, choice result, BG row cursor, per-glyph beep |

Paging: an 18-wide box advances `$120` per line. `<NEXT>` (`EF EE`) moves from line 1 to line 2, or scrolls the box
up one row, waits 4 frames and clears; `<CLEAR>` blanks the box and returns to line 1.
## 6.3 Text commands `$E0`–`$FF`
Table at `$00:$2956`, indexed by `byte-$E0`.

| Code | Operands | Effect |
|---|---|---|
| `$E0`–`$E4` | id | play SFX, then wait until all sound channels are idle |
| `$E5` | id | queue music, then wait until idle |
| `$E6` / `$E7` | — | yes/no choice (E7 starts with the cursor on "no", `wTextYesNoResult = 1`), no confirm sound for E6: opens the choice window and stops the printer |
| `$E8` | col, row | glyph destination = window tile + `16*(row*width+col)` |
| `$E9` | id | play sound: `< $60`, `$CC`, `$CF`, `$D6` = music, else SFX; no wait; `E9 FF` restarts map music |
| `$EA`/`$EB` | — | voice beep on, `wTextBeepSound = $6B`/`$6A` |
| `$EC` | — | pause: clears bit 7; length from `wTextSpeed`; at speed 7 waits for a button |
| `$ED` | — | `<INSTANT>`: set `wTextControl` bit 7 (bulk print) |
| `$EE` / `$F3` | — | clear the second line, back to the line start / move to the window's first line (not the line start) |
| `$EF` | — | first half of `<NEXT>`; on line 1 it swallows the following byte |
| `$F0` | — | end of string (or of an inserted buffer → return to `wTextStartPos`) |
| `$F1` / `$F2` | — | `<LINE>` next line, no scroll / `<CLEAR>` blank the box, back to line 1 |
| `$F4` / `$F5` | — | end `<INSTANT>`/`<FAST>` (clear `wTextControl` bit 7, `wTextFlags` bit 1) / `<FAST>`: no per-glyph wait |
| `$F6` | — | copy `wPlayerName` (`$C60C`, 10 B) to `wPlayerNameText` (`$C53F`) |
| `$F7` | — | wait for a button: set `wTextFlags` bit 2, clear `wTextControl` bit 7 |
| `$F8` | frames | per-glyph delay from here on (`wTextControlArg`) |
| `$F9` | offset | insert the string at `wTextBuf0+offset`: save the position in `wTextStartPos`, continue in the buffer, its `$F0` returns |
| `$FA` | — | blinking "more" arrow while waiting (bit 5) |
| `$FB` / `$FC` | frames | wait `frames` frames **or** until a button / wait `frames` frames only |
| `$FD`/`$FE` | — | per-character beep on/off (`wTextControl` bit 0) |
| `$FF` | — | `<CHOICE>`: the yes/no window (`OpenTextChoice`: saves the two tiles under it to `wScriptTileBuf0/1`, sound `$6C`, result 0) |

`$FF` is **not** an end marker — it is the same routine as `$E6`; `$F0` terminates. Handlers, in table order:
`$E0`–`$E4` `$2996`, `$E5` `$29A8`, `$E6` `$29BA`, `$E7` `$29BD`, `$E8` `$29CB`, `$E9` `$29FA`, `$EA` `$2A25`, `$EB`
`$2A30`, `$EC` `$2A3B`, `$ED` `$2A6D`, `$EE` `$2A73`, `$EF` `$2B09`, `$F0` `$2BCD`, `$F1` `$2C21`, `$F2` `$2C48`,
`$F3` `$2C51`, `$F4` `$2C6A`, `$F5` `$2C75`, `$F6` `$2C7B`, `$F7` `$2CAD`, `$F8` `$2CB8`, `$F9` `$2CC5`, `$FA`
`$2CFD`, `$FB` `$2D03`, `$FC` `$2D15`, `$FD` `$2D27`, `$FE` `$2D2D`, `$FF` `$2D33` (all in bank `$00`). Buffers:
`wTextBuf0`–`$3` = `$C130`, 16 B each, `$F0`-terminated; `wPlayerName` `$C60C` (10 B); `wTextNumber` `$C17E`.
## 6.4 Messages: the message word and the string banks
A message is one word: `H` = group, `L` = id; bits 6/7 of `H` are window flags (`MSG_KEEP_OPEN = $4000`,
`MSG_ALREADY_OPEN = $8000`) and are masked off.

| Step | Routine | Address |
|---|---|---|
| 1 | `StartMessageCommand09HL`: `wScriptParam0 = id`, `wScriptParam1 = group`, then `ScriptCommand09_ShowText` | `$13:$4001`, copy `$04:$55BB`; `$10:$4A27` |
| 2 | `StartMessageForGroup`: group `& $3F`; `wMessageMode` ≠ 0 → data path (11 far-ptr modes at `$10:$4AFF`) | `$10:$4AD0` |
| 3 | `StartMessageForGroup_ByGroup`: key-world redirect on `wMapType` bit 7 (banks `$83`/`$8A`), else `wStringIndex = L`, `wStringCategory = 0`, `rst $00` through the 14-word table | `$10:$4B20` |
| 4 | per-bank stub → `BeginStringDisplay_BankXX` at CPU `$4001` of the string bank: `id < threshold` → main category table, else overflow far-call | `$10:$4B37` |
| 5 | `BeginStringDisplay` → `LookupString` → `PrintTextStep` | `$00:$25C9` |

The group table (14 words, no bounds check) points at 7-byte stubs `21 01 40 06 <bank> D7 C9`; groups 6/7 share a
stub and so do 9/10.

| Group | Bank | Main ids | Overflow at → far-call, count |
|---:|---|---:|---|
| 0 / 1 / 2 | `$28` / `$29` / `$2A` | 218 / 142 / 149 | `$97:$4095` 38 / `$97:$474A` 114 / `$97:$5BBF` 107 |
| 3 / 4 | `$2B` / `$2C` | 138 / 145 | `$98:$4070` 113 / `$98:$572E` 111 |
| 5 / 6, 7 | `$2D` / `$2E` | 213 / 166 | `$99:$4070` 43 / `$99:$4B35` 90 |
| 8 / 9, 10 / 11 | `$7C` / `$80` / `$82` | 135 / 200 / 144 | `$99:$6366` 121 / `$96:$404B` 56 / `$96:$574A` 112 |
| 12 / 13 | `$86` / `$89` | 256 (flat) / 222 | — / `$98:$7032` 34 |

String-bank layout: `dw <list>` (category word), N × `dw <ptr>`, then `$F0`-terminated strings, every pointer
`$4000`-relative in its own bank. Totals: 3579 (group,id) messages, 2201 distinct strings, 3584 slots (group 3 lacks
ids 251–255). Example: group 0 id `$23` = list `$28:$4034`, ptr `$4F15`, 131 B, `"<VAR00> checked the bookshelf."`.
One debug string is unterminated (group 13 overflow id 27+, `$7CD2`, 814 × `$00` to the bank end).

Number rendering: `HLToDecimalDigits` / `Number24ToPackedBCD` produce digit codes or packed BCD;
`WritePackedBCDNoLeadingZeros` (`DE` = destination, digits `0`–`9`, `$F0` terminator, no leading zeros, zero → one
`0`) writes them out. Messages insert such a buffer with `$F9 <offset>`, e.g. `F9 4E` = `$C130+$4E = $C17E`
(`wTextNumber`; the card casino puts a 1–13 card and the stake there). Menu/battle number fields are drawn tile-wise
and **right-aligned** (3 cells for HP/MP, 2 for level), spare cells blank. The conversion for a plain 16-bit message
value elsewhere is *unconfirmed*.
## 6.5 The event-script VM (bank `$10`)

| Item | Address |
|---|---|
| bank marker `db $10` + entry (reads `wFadeState`, `wScriptStartRequest`) | `$10:$4000` |
| `FetchScriptCommand_NextOpcode` (`push hl; rst $00`) / opcode table, 249 words, `$00`–`$F8` | `$10:$4054` / `$10:$4056` |
| `ExecuteScriptCommand` (`dec a; rst $00`) / command table, 248 words, types 1–248 | `$10:$46F4` / `$10:$46F6` |
| first script, `Script_HehSoTheseAre` | `$10:$4F54` |

`RunEventScriptFrame` = fetch + execute, once per field frame. A fetch reads the opcode at `wScriptPointer` (via
`ReadWordFromDataBank` when `wScriptInDataBank` is set), checks `$FF` first, then jumps: it either consumes its
inline operands and acts at once (fetching again in the same frame) or sets `wScriptCommandType` and calls
`BeginScriptCommand`. A command runs its own multi-frame state machine and, when done, writes `wScriptStartRequest =
$80` to request the next fetch.

| Var | Meaning |
|---|---|
| `wScriptStartRequest` `$C919` | bit 7 = run the script at `wScriptPointer` (cleared by the fetch) |
| `wScriptPointer` `$C91A/1`, `wScriptRunning` `$C91F` | next opcode; non-zero while a script is in progress |
| `wScriptCommandType` `$C920`, `wScriptParam0/1` `$C921/2` | current command type; param0/1 double as message id/group |
| `wScriptStep` `$C923`, `wScriptReturn` `$C91C`–`$C91E`, `wScriptInDataBank` / `wDataBank` | command sub-step, saved position, operands from another bank after `$E7` |
| `wModeState` `$C5DC`, `wFadeState` `$C56C` | field mode; **a fetch does nothing while a fade runs** |

There is **no call/return opcode and no script stack**: control flow is jumps plus `$E4`/`$E7` only, and the only
return-address mechanism in either layer is the text printer's `$F9` buffer call.
### Opcodes with inline operands (verified)

| Op | Mnemonic | Bytes | Semantics |
|---|---|---|---|
| `$00` | message | 2 (u16) | show message `(group,id)`; type 1; blocks until dismissed |
| `$01` / `$02` | walk / walk_fast | 3 | object `obj` walks `n` tiles in `dir` (0 down, 1 right, 2 up, 3 left), 16 frames/tile; `$02` does 2 px/frame and may overshoot 1 px on its last frame; types 2/3 |
| `$03` | wait | 2 (u16) | block `n` frames; type 4; N waits exactly N frames |
| `$04` | hold_dpad | 2 | hold `dir` for `n` frames; type 5 |
| `$05` | face | 2 | set `dir` on target (0 = player, n = follower, `$80+n` = object); type 6; ends after 1 frame |
| `$06` | skip_if_no | 1 | restore the two choice-window tiles, then if `wTextYesNoResult == 0` add the offset byte (measured from the byte after it) to the pointer |
| `$07` / `$0A` | jump / set_flag | 2 (u16) | `wScriptPointer = address`, no return / `SetFlagBit(flag)` |
| `$0B` / `$0C` | slide_y / hide_object | 1 | 32-frame Y slide, type `$0C`, deltas `-2,-1,-1,0,-1,0,-1,0,0,1,0,1,0,1,1,2` / clear sprite slot `n` |
| `$0D` | encounter | 1 | start scripted encounter `n`; type `$0E`; blocks until the battle ends |
| `$0E` / `$0F` | add_gold / sound | 2 / 1 | add `amount` gold / `id`: `$FF` = restart map music, `< $60` = queue music, else queue SFX |
| `$E4` | choice_jump | 1/choice | skip `wTwoChoiceCursor` offset bytes, read the chosen one, jump forward by it (unsigned add) |
| `$E7` | jump_data_bank | 2 (u16) | set `wScriptInDataBank`, jump to `address` in `wDataBank` (`$0C,$0D,$0E,$15,$1D,$1F,$96`); operands then come from there |
| `$EA` / `$F5` | message_unless_flag0 / message_by_screen | 2 (u16) | message, but `id += $20` unless flag `EVENT_NEVER_SET` is set / `id += 16*wScreenTableIndex`; type 1 |
| `$FF` | end | 0 | clears `wScriptRunning`, `wScriptCommandType`, `wScriptInDataBank`; `wModeState = 0` (5 when `wMapType` bit 7) |

Every other opcode with a non-zero table entry is a **command** and consumes **no** inline bytes: the opcode byte
becomes `wScriptCommandType` and the command reads its own arguments. 249 entries, 48 distinct handlers, 50 zero
entries (`$08`, `$09`, `$10`, `$97`, `$A2`–`$BF`, `$D0`–`$DF`); `$F9`–`$FE` index past the table, unused.

| Range | Command family (names from the reference config; class verified) |
|---|---|
| `$11`–`$3A` | story scenes: `$1E` check_item, `$28` shake_screen, `$2E` warp_map41, `$32` give_item_blink, `$34` set_tiles_flag_310 |
| `$3C`–`$7F` | rewards/scenes: `$3C`/`$3D` reward_item_or_key, `$3F` blink_sprites, `$4F` set_tiles_d2, `$55` set_flag_322, `$5C` take_item, `$6C` give_monster, `$6F` desk_key, `$74` set_flag_redraw, `$78` save_screen |
| `$80`–`$A1` | field service: `$80` step_trigger_reward, `$84` random_gold_or_item, `$85` key_world_boss_battle, `$89` return_warp, `$8A` map_exit_warp, `$93` warp_with_followers, `$95` arena_grid_battle, `$96` arena_rounds, `$9B` heal_party, `$9E` key_world_floor_battle |
| `$C0`–`$F8` | `$CE` hide_sprites and shop/inn/vault/arena screens with `_close` partners: `$E0` inn, `$E2` shop, `$E5` vault, `$E8` swap_monsters, `$EB` hibernate, `$ED` breed, `$EF` egg_service, `$F0` rename, `$F2` key_appraisal, `$F3` medal_prizes, `$F4` npc_breed, `$F6` library, `$F7` arena, `$F8` priest |

There is **no script table**. Starters store `HL` and request a run; this exact body exists twice,
`StartScriptAtHL_B13` `$13:$4049` and `StartScriptAtHL_B04` `$04:$5603`:

```
7D EA 1A C9 / 7C EA 1B C9   ld a,l/h ; ld [wScriptPointerLo/Hi],a
3E 80 EA 19 C9              ld a,$80 ; ld [wScriptStartRequest],a
3E 01 EA DC C5 / C9         ld a,1 ; ld [wModeState],a ; ret
```

Callers are talk handlers, trigger and service commands and `$83`-type field scenes. 91 talk handlers start a script
(78 distinct scripts, all inside `$10:$4F54`–`$10:$65BE`); the most frequent opcodes in them are message 815,
set_flag 221, skip_if_no 119, `$E7` 101 (15 targets, 81 call sites in 11 banks), face 89, walk 76, wait 60,
walk_fast 58.
## 6.6 Talk-event dispatch and triggers
An A-press on a map spot ends in `DispatchTalkEvent` (`$13:$405C`), which switches on `wTalkEventIndex` (`$C917`)
through an 11-word category table at `$13:$40ED`, then on `wTalkEventGroup` (`$C916`) through that category's group
table (4-byte `FA 16 C9 C7` preamble, `dw` list at +4).

| Cat | Area | Target | Group table | Groups |
|---:|---|---|---|---:|
| 0 / 1 / 2 | Field / GreatLog / Kalka | `$4103`→`$04:$6892` / `$5941` / `$4126`→`$04:$612B` | `$04` / `$13` / `$04` | 40 / 247 / 70 |
| 3 / 4 / 5 | Yold / Norden / Fhunt | `$412D`→`$04:$58C2` / `$4A23` / `$4134` | `$04` / `$13` / `$13` | 110 / 171 / 115 |
| 6 / 7 | Darck / Elven Village | `$411F`→`$04:$6827` / `$4111`→`$04:$6A35` | `$04` | 2 / 184 |
| 8 / 9 / 10 | Traveler / Key World / Readable | `$593A` / `$4118`→`$04:$7B29` / `$410A`→`$04:$5616` | — / `$04` / `$04` | — / 9 / 35 |

Group entries are 2 bytes in four shapes: `dw $0000` (unused; 983 entries, with holes such as GreatLog 232/239), a
bare `C9` (no event), a 7-byte message handler `21 <id> <group> CD <4001|55BB> C9` (289 entries), or a script
handler `21 <lo> <hi> CD <4049|5603> C9`. Some test a story flag first (`ld de,<flag>; call TestFlagBit; jr c/nc`)
and then show one message or start one script. Example: GreatLog cat 1 group 3 → `$5D43` → `21 23 00 CD 01 40 C9` →
message `$0023`.

The pair comes from a **10-byte interaction record**, one static list per map: `MapInteractionTable` = 232 words at
`$87:$4539` indexed by `hMapId` (128 maps have a list, 532 spots); a list ends with a kind byte of `$FF`.

| Off | Field |
|---:|---|
| 0 | kind: 0 skipped; 1–4 facing-locked (`facing == kind-1`); 5 = the tile in front, any facing |
| 1–3 | map id the spot belongs to, then screen X, screen Y |
| 4, 5 | player X, player Y in pixels (cell = `>>3`) |
| 6–7 | story-flag word, little-endian (`$FFFF` = no flag); the spot exists only while the condition holds |
| 8 / 9 | talk event **group** → `wTalkEventGroup` / **index** (category) → `wTalkEventIndex` |

Step triggers reuse the layout in `MapStepTriggerTable` = 232 words at `$87:$40A0` (28 maps), where player X `$FF`
means "anywhere on that screen"; walking onto a record fires it. Key-world and town maps instead use **runtime**
trigger records built at map transition by bank `$60` (no static ROM copy): `wMapObjects` (`$CC48`, count `$CC47`)
is 8 bytes — 0 flags/kind (bit 7 = plain object, low 2 bits = kind), 1 kind-table index, 4 screen byte (`x<<4|y`), 5
cell byte (`x<<4|y`) — and `wScreenTriggers` (`$CCEB`, count `$CCE9`) is 4 bytes — 0 flags/kind, 1 kind-table index,
2 screen byte, 3 cell byte. Match rule (`FindTriggerEntryForCurrentScreen` `12:$70A4`, `..._ScreenTriggers`
`12:$710A`): byte 0 bit 7 clear **and** screen byte == `(hMapScreenX<<4)|hMapScreenY`; the object list is searched
only on the seven town maps and in key worlds, the screen-trigger list only when `hMapId >= $30` (first three
entries) or in `$85` maps. `wTriggerIndex` = count − entries left. Kind decode (`StoreTrigger` `12:$715E`): kind =
byte0 & 3; if 0, look up the 45-byte table at `12:$71BB` (`00 04 05 05 05 05 04 04 04 04 06 00 04 07 … 05 00 09 … 0A
06 00 01`, duplicated at `85:$5D8C`); if still 0 there is no trigger. Kinds 2/3 are blocking: the step is refused
(`02:$5AB6`) and A starts talk group `$0F` `Talk_StepTriggerReward` (`12:$7333`); kinds 1, 4–10 fire on stepping
onto the cell (`12:$73A1`), also group `$0F`. Marker graphics: `TriggerSpriteTable` `12:$71EE` (6-byte records from
`$12:$71E8`: graphics pointer, bank `$7E`, palette), meta-sprite set `12:$7308`, pixel offsets `12:$7313`;
`wTriggerMarkerFlags` (`$C956`) bit 7 hides it.
## 6.7 Story flags
`wStoryFlags = $CBD7` is a flat bit array: flag *n* is bit `n & 7` of byte `$CBD7 + (n >> 3)`. `SetFlagBit` =
`$00:$1845`:

```
ld a,d ; cp $03 ; jr nc,.hang   ; flags >= $0300 never return
ld b,e ; sra d / rr e  x3       ; keep the bit number; DE = flag >> 3
ld a,e ; add $d7 ; ld e,a       ; DE += $CBD7
ld a,d ; adc $cb ; ld d,a
ld c,1 ; mask = 1 << (flag & 7) ; then ld a,[de] ; or c ; ld [de],a ; ret
.hang: jr .hang                 ; infinite loop
```

Valid flags are therefore `0`–`767` even though the block is `$6B` = 107 bytes (856 bits); a script setting `$0300`+
hangs the cartridge. Testing uses the same `>>3`, `+$CBD7`, `1<<(n&7)` computation (shared unguarded entry
`$00:$181B`, called per flag word by the object-selector walk).

* Saved as the second save block: **SRAM file offset `0x3DA0`, length `0x6B`**, loaded by
  `LoadSaveBlocksFromSRAM_Data` (`02:$75F7`, `{addr,len}` descriptors) with the hero variant, `wPlayerName` (`0x291` B
  at `$C60C`) and `wKeyWorldSlot` (`0xB5` at `$CC42`).
* Other gates: object selectors (`$FFFD` two flags / `$FFFC`
  set→skip / `$FFFB` clear→skip / plain word taken while clear), warps, map variants, talk handlers.
* No partitioning
  of the number space is documented. Flags seen in scripts: `$06F $075 $078 $085 $098 $099 $09B $1CF $309 $310 $311
  $318 $322`.
## 6.8 What a port must reproduce exactly
* `wTextSpeed` frames per glyph with 0 as 1, `<PAUSE>` at speed 7 waiting for a button, `<INSTANT>` set by a button
  during the glyph wait, 16-byte tile writes gated on VRAM access.
* `$F0` ends a string, `$FF`/`$E6`/`$E7` are yes/no
  prompts, `$8D`/`$8E` overstrike the previous tile, zero is never a blank glyph.
* One fetch or one command step per
  frame; `$03` waits exactly N frames; a fade blocks the fetch; `$FF` leaves `wModeState = 0` (5 in key worlds). *
  `$06` restores the two tiles under the choice window before branching and reads `wTextYesNoResult` with 0 = yes;
  `$E4` advances by an unsigned byte offset past a runtime-length table; `$01` moves 1 px/frame; `$02` may overshoot 1
  px; `$0D` blocks until the battle ends.
* Flags `>= $0300` are rejected (the cartridge hangs); the flag block is
  saved at `0x3DA0`, length `0x6B`.
## Sources
* `re/notes/text_encoding.md`, `re/notes/messages.md`, `re/notes/text_classifier.md` — charset, string banks,
  `StartMessageForGroup` chain, glyph grid, box renderer.
* `re/notes/script_vm.md`, `re/notes/event_scripts.md`,
  `re/notes/event_scripts_handoff.md` — text VM, event VM, opcode table, timing.
* `re/notes/talk_events.md`,
  `re/notes/field_scripts.md`, `re/notes/triggers.md`, `re/notes/map_interactions.md`, `re/notes/field_commands.md` —
  dispatch, script inventory, trigger records, interaction records, field commands.
* `re/notes/map_objects.md`,
  `re/notes/field_script_run.md`, `re/notes/card_casino.md` — flag gates, flag arithmetic, number formatting.
* Ground truth: the reference disassembly (`src/charmap.inc`, `home/bank00_home.asm`,
  `scripts/bank10_scripts.asm`, `engine/bank13_talk.asm`) and the ROM bytes it quotes.
