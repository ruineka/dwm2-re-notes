# 11. The link cable protocol

The game talks to another cartridge one **serial byte** at a time
(`SB $FF01`/`SC $FF02`, 4096 cycles per byte, 128 in double speed). Every
protocol step is a fixed-length exchange of bytes; there are no packet headers,
lengths or checksums on the wire. Getting the byte order wrong desynchronises
the two consoles permanently, so this file is deliberately explicit.

## Serial plumbing

* Serial interrupt vector `$0058` → `SerialInterruptHandler`, which ends in
  `$00:255B` → `RunLinkSession` (`$1B:4001`).
* `wLinkRole $C57F` bit 1 is not one rule, it is three:
  * in the **data exchange** (`LinkSendStepWithBuffer`, `$1B:45A1`) bit 1 set
    means this side transmits and clocks (`StartSerialTransferInternalClock`,
    `$08AD`, `SC` bits 0+7); clear means it arms `$F9` and waits
    (`SerialSendByte`, `$08BA`, `SC` bit 7 only);
  * in the **resync greeting** (`$00:4006`) the polarity is inverted: bit 1 clear
    drives the clock;
  * it is **re-derived after every mode change** from the partner's greeting byte
    (`$70 | wIsCGB`), so on a mixed DMG/CGB pair the DMG side ends with bit 1 set
    no matter who pressed A. `RunLinkSession_FindPartner` (`$1B:402A`) sets it
    when it receives a leader code and clears it on a follower code.
* The clock driver writes `$81` to `SC` (internal clock, start transfer); the
  other side waits for the interrupt.
* In link play the VBlank handler runs a reduced path (sound tick, sound queue,
  `GameFrameUpdate` only — no joypad poll, no PRNG advance, no text step), and
  fades no longer pause game logic.

## Title menu (`$07:6090`)

`TitleMenu_Draw $07:60F3` sends `$F4` every frame and draws 7 entries, or 8 when
`wLinkSetting $C894 != 0`. `TitleMenu_SendHighlight $07:6145` sends the follower
byte for the highlighted row; `TitleMenu_Choice $07:6231` handles A.

| Row | Label | Leader (A) | Follower | Session | Entry routine |
|---:|---|---|---|---:|---|
| 0 | CONTINUE | `$F4` | `$F4` | — | `TitleMenu_Choice` |
| 1 | NEW GAME | `$F4` | `$F4` | — | `TitleMenu_Choice` |
| 2 | BREEDING | `$F5` | `$FA` | 2 | `$07:63B7` |
| 3 | KEY TRADE | `$F6` | `$FB` | 3 | `$07:641C` |
| 4 | VS MODE | `$B7` | `$FC` | 4 → battle 1 | `$07:646B` |
| 5 | DREAM EGG | `$DC` | `$DD` | 8 | `$07:6558` |
| 6 | TEAM MODE | `$E0` | `$E1` | 6 → battle 7 | `$07:64BA` |
| 7 | TERRY | `$F1` | `$F3` | 5 | `$07:6509` |

Follower table `SendLinkByteForMenuOption_Data $07:65BD`:
`f4 f4 fa fb fc dd e1 f3` (the same bytes are duplicated at `$1B:43E1`).
`$F4` doubles as the idle byte.

## Pairing (`$1B:402A`)

* A **leader** byte is accepted only while `wTitleScreenSubState == 1`; it makes
  the receiver passive (`wLinkRole |= 3`).
* A **follower** byte is accepted only while `wTitleScreenSubState == 2`; it
  makes the receiver the clock driver (`wLinkRole = set 0, res 1`).
* The received code's option must equal the local menu row. On a mismatch the
  A-presser goes to state 4 (`$07:4289`) and shows
  `String_07_00_05` — "Game Link is not ready. Please check and try again." —
  then returns to the title; the other side's cursor jumps to the partner's row.
* `$FE` (state 7 `$07:4178`) prints "Game Link cannot be used with Super Game
  Boy." but **nothing in the ROM writes `$FE`** — a dead path.
* Two CGBs: `$00:4006` corrects the roles once from the greeting byte. It never
  clears bit 1 on either side, so a 0/0 pair only happens if neither console ever
  received a leader or follower code (both sat on a menu row without pressing A).

## Sessions

| Session | Function | Screen data |
|---:|---|---|
| 2 | breeding | `LinkBreed $F1:4B9F`, `BreedStartExchange $F1:4E4A` |
| 3 | key trade | `LinkKeyTrade $1B:547D` (37 steps) |
| 4 | VS setup | `RunLinkSession4ScreenState $07:6C12`, `LinkBattleSetupMenu_ConfirmAndStart $1B:6C61` |
| 1 | VS battle | `$31:4001` / `$31:4106` |
| 5 | Terry breeding | `LinkBreed $37:4BEB`, pack/unpack at `$37:5BC6`/`$37:5C4E` |
| 6 | team mode exchange | `TeamMode_Screen $33:5215`, `RunLinkSession6Exchange $33:5883` |
| 7 | team battle | `GameMode7` (`$A0`) |
| 8 | dream egg | `$F0:4CA0`, `RunLinkSession8Exchange_Trade $F0:51B8` |

## Records (sizes exact)

| Record | Bytes | Notes |
|---|---:|---|
| Monster (plain) | 165 | the SRAM `0xA5` record verbatim, no translation |
| Monster (packed) | 149 | canonicalised: 4-glyph names + glyph remap, 1-byte species code, skills via a remap table, AGL/INT/WLD scaled ≈51/25/25 % |
| Battler | 78 | `PackBattlerRecords $1B:7152` (14-byte name, 8 skills, status + `$15` stats, `$1F` personality/resistance, item, `$FF`) |
| Team | 234 | 3 × 78 |
| Command block | 19 | `turn0 turn1 turn2 seedLo seedHi menu menu a0..a5 m0..m2 s0..s2` |
| Key block | 6 | 4-byte key entry + 2-byte seed |
| Key world | 405 | 13 chunks of 30 B plus a 15 B tail (14 transfers, `$0195` divided by `$1E`) |
| Child block | 100 | Terry breeding |
| Gift block | 216 | dream egg |
| Egg data | 16 | |
| Name | 12 | partner name |
| Flags | 3 | |

No record carries a checksum, a length or a sequence number. A dropped byte is
detected only by the game's own step machine stalling, never by the
transport.

## Per-session control bytes

* Breeding (2): `$FF` offer, `$FE` refuse, `$01` go, `$F0` end.
* Key trade (3): `$01`…`$05`, `$FD` cancel, `$FE` refuse, `$F0` end.
* VS (4): `$D3` sync, per-member HP/MP/status bytes, `$FE/$FD/$FC/$FB` kind
  byte, 10-byte rules + `$02` + `$F0`, 165-byte prize, `$D2` → name swap, `$01`,
  19-byte command block.
* Dream egg (8): `$BA`, 12-byte name, 3-byte flags, `$B3/$A8/$B6/$BD`, `$BB`
  cancel.
* Team mode (6): fee `$01/$10/$20/$30/$40/$FE`, `$F0`, `$D2` → `$0C`, 2-byte
  seed, `$03`.
* Terry (5): `$02`, `$00`, `$03`, `$FD` refuse, `$F0` end.

## Seeds

The **bit-1-clear** side's seed wins: `$33:5BB3` copies its own `wRandomLo/Hi`
into `wRandomSeed2` when bit 1 is clear, and copies the received seed back when
bit 1 is set (`$31:5DA7`, `$A0:503A` do the same for their blocks). Since
`FindPartner` leaves bit 1 clear on the side that sent the leader code, the
side that pressed A is the seed authority. A reimplementation must keep the two
generators in lockstep with the byte stream, not with the frame counter.

## Edition differences

Tara ↔ Cobi linking works: the protocol is identical, the only edition-varying
wire byte is the team-mode mark byte (`$33:58CA`, byte 15 of the fight-info
block) which the receiver stores where nothing reads it. See `14-editions.md`.
