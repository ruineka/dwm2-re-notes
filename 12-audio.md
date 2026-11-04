# 12. Audio: sound engine, music and sound effects

Addresses are from *Dragon Warrior Monsters 2: Tara's Adventure* (USA), 4 MiB ROM. The driver lives in bank `$00` (home ROM), track data in banks `$40`–`$43`. It writes the APU directly, keeps no register shadow except `rNR51`, is non-reentrant, and saves `rROMB0` (`$2100`) around each call.

## 1. Engine at a glance

- One tick per VBlank, from `VBlankHandler` `$00:03A4` (VBlank vector `$0040` = `f3 c3 a4 03`). Tick rate = 4194304/70224 = **59.727500569 Hz** (16.7427 ms); CGB double-speed does not change it.
- No timer: vector `$0050` is eight NOPs, and the ROM never writes `rTMA`/`rTAC`.
- The driver runs a fixed array of **6 channel slots** over the 4 hardware channels. The hw channel is per-record data (record byte 1, 0–3), not a slot property; two slots may share one hw channel.

| address | routine | address | routine |
|---|---|---|---|
| `$00:122D` | `QueueMusic` (`ld [wMusicRequest],a; ret`) | `$00:1278` | `QueueSoundEffect` |
| `$00:131A` | `ProcessSoundQueue` | `$00:1231` | `StartMusic` |
| `$00:127C` | `StartSoundEffect` | `$00:3290` | `InitSoundHardware` |
| `$00:3354` | `StartSound` (one id, returns `A = id+1`) | `$00:334B/$334E/$3351` | 4 / 3 / 2 consecutive `call $3354` |
| `$00:33E8` | `SoundTick` (per-frame driver) | `$00:3554` | `StartChannelFromTrackHeader` |
| `$00:35CD` | `SoundNextEvent` | `$00:3938` | `ComputeNotePitch` (wave path `$00:3599`) |
| `$00:3989` | `ComputeNotePitch_TriggerChannel` | `$00:3998` | `ComputeNotePitch_ApplyPanning` |
| `$00:39B9` | `SoundTick_VolumeSlide` | `$00:39F8` | `SoundTick_PitchOffset` |
| `$00:3A2F` | `WriteChannelEnvelopeIfChanged` | `$00:3A5D` | `ClearChannelLengthBits` (`rNRx1 &= $C0`) |
| `$00:3A7A` | `SoundTick_PlayingNote` | `$00:3A94` | `SoundTick_VolumeModulation` (body `$3A98`) |
| `$00:3B51` | `ReturnTwiceIfSoundSkipMaskAAndSoundSkipMaskB` | `$00:3DAE` | `SoundLabelSlot` |
| `$00:3DC8` | `SoundTick_StepEnvelope` | `$00:34BA/$34C7/$349F/$32E8` | wait countdown / end pass / next note / mark done |
| `$02:604B` | `RestartMapMusic` | `$02:6050` | `PlayMapMusic` |
| `$02:609D` | `PlayMapMusic_ByMapId` | `$02:6089/$02:6093` | `PlayMapMusic_QueueIfNew` / `QueueSoundIfNew` |

## 2. How a song or effect is started

`ProcessSoundQueue` `$00:131A`: if `wMusicRequest != $FF` call `StartMusic` then store `$FF`; then the same for `wSoundEffectRequest`/`StartSoundEffect`. Music is served before effects on the same frame.

`StartMusic` `$00:1231`: `ld [wCurrentMusic],a` → `di` → `call InitSoundHardware` → if `A == 0` return (stop) → `ld [wSoundId],a` → number of tracks: **4** for ids `$02`, `$0F`, `$58`; **2** for `$40`, `$42`, `$44`, `$46`, `$48`, `$50`, `$52`; **3** for every other id. It then calls `StartSound` for that many consecutive ids (`id`, `id+1`, …), so a "song" is a run of consecutive records started on one frame. `wCurrentMusic` is `$FF` at boot and `$FF` also means "nothing playing".

`StartSoundEffect` `$00:127C`: pushes all registers, `ld [wSoundId],a`, then **1** track for most ids, **2** (`id`, `id+1`) for `$63 $67 $70 $72 $74 $7E $89 $8B $8D $91 $9F $A5 $AC $AE $B2 $B6 $B8 $BA $BD $BF $C1 $C3 $C5 $C7 $C9 $D2 $D4 $DA $DD` (29 ids), **3** for `$6D`. No `InitSoundHardware`, so effects overlay the song; its only caller is `ProcessSoundQueue`.

`StartSound` `$00:3354` — the only routine that touches a slot:
1. `ld [wSoundId],a`; walk `SoundBankTable` `$00:3E13` for the first entry whose first byte exceeds `id`; the **previous** entry gives base id, record array and bank (`$FF` first byte ends the table).
2. `ld [rROMB0],bank`; `index = id − base`; record = `array + 4*index`; slot = `wSoundChannelSlots + record[0]`.
3. If the old slot byte 0 is not `$FF`, take the **old slot's byte 1** (`hTrackPosHi`) `& 3` and clear the matching stereo pair of `wSoundEngineMode` (`0→$EE`, `1→$DD`, `2→$BB`, `3→$77`). Keyed on the old *track position* high byte, not on the hw channel — a ROM quirk to copy.
4. Unconditionally: slot+0 = slot+1 = 0 (`hTrackPosLo/Hi` = "read header"), slot+2 = flags (hw channel), slot+3/4 = track pointer, slot+5 = bank, slot+10 = `$FF` (sweep/wave-select sentinel), slot+21 = 0, slot+25..31 = 0.

## 3. Sound table (`SoundBankTable` `$00:3E13`)

`db $00 / dfar SoundRecords_Bank40 / db $1c / dfar …_Bank41 / db $31 / dfar …_Bank42 / db $a8 / dfar …_Bank43 / db $ff,$ff`: base ids **0, 28 (`$1C`), 49 (`$31`), 168 (`$A8`)**; record arrays begin at `$4001` of banks `$40`–`$43` (byte `$4000` of each sound bank holds that bank's own number). 223 records = ids **0–222**. No song titles and no other song table exist. A record is 4 bytes `{slot offset ($00,$20,…,$A0), hw channel 0–3, track pointer lo, hi}`, the pointer being a `$4000`–`$7FFF` address in the record's bank. No priority, no mask, no free-slot search; ids > 222 read past the table.

| sound ids | bank | records | note |
|---|---|---|---|
| 0–27 | `$40` | 28 | ids 0–5 (songs 1–2) point at the silence track `$40:4071` |
| 28–48 | `$41` | 21 | |
| 49–167 | `$42` | 119 | |
| 168–222 | `$43` | 55 | |

## 4. Track format

4-byte header, then fixed **2-byte events**; positions count events, so `address = base + 2*position` and playback starts at event 2 (byte offset 4). The header is read only when `hTrackPosLo/Hi == 0` (track start).

| byte | pulse ch1/ch2 | wave ch3 | noise ch4 |
|---|---|---|---|
| 0 low nibble | tempo step 0–15 | tempo step | tempo step |
| 1 | duty `= byte1 & 3` | modulation delay | latched, unused |
| 2 (nibbles swapped) | `rNRx2` volume/envelope | raw `rNR32` output level | `rNR42` volume/envelope |
| 3 | `rNR10` sweep (ch1 only) | wave number 0–15 | stored, unused |

Byte 3 as a wave number is read only because `StartSound` wrote `$FF` to the slot's sweep/wave byte, the sentinel meaning "use the header byte". Byte 2 is stored swapped: `$0D` → `$D0` (volume 15, period 0); on the wave channel the swapped byte *is* the `rNR32` value (`$06` → `$60` = 25 % output).

**Tempo.** Each slot keeps `hSndTickAccum` (`$FFDF`); every frame `accum += step` (low nibble of the duty/tempo byte `$FFDE`). If the sum is ≥ 16 the slot stores `accum − 16` and the frame is a **carry frame**: volume slide, gate timer, wait counter and envelope timer are all skipped for that slot. A wait/gate of `L` lasts `L*16/(16−step)` frames on average (exact — the accumulator phase carries across notes): step 0 → `L`, 8 → `2L`, 15 → `16L`. Header load and `AF` both set `accum = step`.

**Per-frame order, one slot, non-carry frame:** pitch offset (if the gate timer is 0) → playing-note check/volume modulation → vibrato-counter increment (capped at the delay) → tempo block → volume slide → gate-timer decrement → wait countdown → envelope/hold logic → note end. A slot whose hardware channel was already handled this frame is skipped: `wSoundSkipMaskB` holds one stereo bit (`$11/$22/$44/$88`), so the test is `wSoundSkipMaskA & wSoundSkipMaskB != 0` and the `$A0`/`$A1` guards drop the register write.

**Note length.** A note lasts `wait` non-carry ticks. If `hSndEnvFlags` (`$FFF3`) has a non-zero high nibble (set by `AA`), the wait becomes `operand − (flags & $0F)` and then `hSndEnvTimer` counts down; at 0 the start volume is restored from `hSndEnvelopeReload` and the note ends. With that nibble set, the envelope advances exactly **once** per note, when the timer reaches `(flags&$0F)−1`.

## 5. Event byte-code

Second bytes are operands; every event is exactly 2 bytes unless noted.

| opcode | effect |
|---|---|
| `$00`–`$9F` | note: `octave = op>>4`, `semitone = op&$F`, operand = wait ticks. Semitone ≥ `$C` = rest on ch1–3. Noise: `$1F` rest, `<$10` = index into the 16-byte `rNR43` table at `$38A0`, `$10`–`$1E` = raw `rNR43` |
| `$A0` | volume: `hSndEnvelope = swap(operand)` (the `rNRx2`/`rNR32` value) |
| `$A1` | ch1: sweep → `rNR10`; ch3: select wave number (`rNR30 = 0`, copy wave, remember it) |
| `$A2` | ch1/2: duty `= operand & 3` (bits 6–7 of `$FFDE`); ch3: modulation delay |
| `$A3` | gate `= 2*(operand&$F)`; channel-flags group `= (operand+$10)&$F0`; operand `$FE` only clears the group. Not a nop |
| `$A4`, `$AB`, `$F0`–`$FC`, `$FE` | no-op (2-byte nop) |
| `$A5` | panning: operand `1` → `hSndPanning = swap(old)`, else `hSndPanning = operand` |
| `$A6` | `rNR50 = operand` (two 3-bit master volumes), written immediately |
| `$A7` | wait `operand` ticks, then end the fetch (no note) |
| `$A8` | `hSndWaveParam = operand`: high nibble = wave set, low nibble = modulation row. All extracted data uses 0 → no-op |
| `$A9` | branch: `$F0/$F1` inc/dec `hSndBranchIndex` `$FFE4`, `$F2/$F3` inc/dec `wSoundBranchArg` `$DD18`, `$FE`/`$FF` jump through a `u16` table after the operand (word = **event index**). No extracted track uses it |
| `$AA` | envelope: high nibble 0 clears timer/reload/flags; else timer `= op>>4`, flags `= (op>>4)|$F0`, reload `= (old&$F0)|(op&$F)` |
| `$AC` | call (4-byte): `{count, target_lo, target_hi}`, target = byte offset >> 1 (event index); uses `hSndLoopCount` `$FFF4` |
| `$AD` | return from `$AC` |
| `$AE` | tuning: `hSndDutyAndTempo bit 4 = operand & $10` (selects period table B) |
| `$AF` | tempo step: `operand & $F` → both `hSndTickAccum` and the step nibble |
| `$B0` | jump to label `operand & $F` only when `operand ≥ $F0`; else 2-byte nop |
| `$B1`–`$BF` | repeat: increment label `operand & $F`'s counter, jump back while counter `< (op&$F)+1`; the section plays `(op&$F)+1` times |
| `$C0`–`$CF` | volume modulation: delay = operand, depth `= (op&$F)<<4`; ignored when the envelope period nibble ≠ 0 and on wave |
| `$D0`–`$DF` / `$E0`–`$EF` | volume slide up/down by `op&$F`, operand = reload time; skipped on wave, **applied** on noise |
| `$FD` | define label `operand & $F` at the next event (counter = 0) |
| `$FF` | end of track: position `= $FFFF`, mute the channel's two `rNR51` bits; wave slots 0/1 arm `wSoundWaveReload` |

**Labels.** `wSoundLabelSlots` `$DCC0 + channel*12 + (label&$F)*3` holds `{counter, pos_lo, pos_hi}`; only 4 labels per channel fit, labels 4–15 reach later channels' bytes (slot 5 label 4 = `$DD08`), and no extracted track relies on that. `$AC`/`$AD` use a separate loop counter and return position.

## 6. Note → period

`ComputeNotePitch` indexes `SoundNotePeriodTable` `$3B5C`: 12 little-endian words `Q ≈ round(131072/f)` for C2…B2 (`07d4 0764 06f9 0695 0637 05dd 0589 053a 04f0 04a8 0465 0426`). Row 2 `$3B74` (`079c 072e 06c7 0666 060a 05b3 0561 0515 04cc 0486 0445 0408`) is row A × 0.972 = **+49.1 cents** (quarter tone), selected by `hSndDutyAndTempo` bit 4 via `AE`; the converter adds `$18` to `2*semitone` to index it.

`value = $0800 − (Q[n] >> octave)` (with `hSndFreqLo` clamped to `$02`–`$FD` after the write) and `f = 131072 / (Q[n] >> octave)`. Octave nibble `o` sounds at **C(2+o)**: `o = 2` → C4 = 261.6 Hz, `o = 0` → C2. The high byte is written as `(H & 7) | $80` (bit 7 = restart). Noise notes never use this table; wave notes do, plus the raw `rNR32` level.

## 7. Volume, envelope, modulation

- `WriteChannelEnvelopeIfChanged` `$00:3A2F`: if `(A & 7) == 0` set bit 3 (`A |= $08`) so the DAC never switches off; if the byte equals the current `rNRx2` do nothing; else write it, rewrite `rNRx4 = hSndFreqHi` (retrigger) and clear the length bits. "Write only if changed" is audible — it decides whether a note retriggers.
- Software envelope step (`SoundTick_StepEnvelope`): `new = ((reload_low+1)*(start_vol+1)) >> 4`, minimum 1; the old start volume moves into `hSndEnvelopeReload`'s high nibble (15×15 wraps to 0 with bit 0 set).
- Volume modulation `$C0`–`$CF` (`$00:3A94`): builds a 4-bit phase `e` from `hSndVibratoCounter`/`hSndVibratoDelay` with four `add a / cp delay / sub delay / ccf / rl e` steps (≈ `floor(16*counter/delay)`), ORs in the depth nibble, reads the word at `$31CE` (the row table `SoundModulationTable` starts at `$31D0`) (`+2*(hSndWaveParam&$F)`, only entry 0 exists), takes `row[depth|phase]`, ORs that byte's high nibble with `swap(hSndEnvelope)` and uses its low bits to pick extra scaling from `SoundEnvelopeScaleTable` `$3B8C` (16×16; row 0 all `$00`, row 15 `$00 $10 … $F0`); result → `rNRx2`, or on wave `rNR32 = ((e>>1)+2)` level. The table has 12 rows and ends at `$3290`, where `InitSoundHardware` begins; `SoundTick` itself is at `$33E8`. Rows 13–15 do not exist, so `depth|phase ≥ $D0` reads code as data — a latent bug, not a table entry.
- Volume slide `$D0`–`$EF` (`$00:39B9`): counts `hSndPitchSlideCounter` down, reloads from `hSndPitchSlideTime`, then ±1 on the `rNRx2` volume nibble (clamped 15/0); does nothing while the envelope period nibble is non-zero. Only wave is excluded — despite the `hSndPitchSlide*` names, the code changes volume.
- Gate (`A3`) is `hSndNoteTimer`/`hSndNoteLength = 2*(arg&$F)`, counted on non-carry frames only. It gates `SoundTick_PitchOffset` `$00:39F8`: row `= (hSndChanFlags&$F0)−$10`, column `= wSoundTickBuf & $0F` of `SoundPitchOffsetRows` `$3C8C` (15 rows × 16 signed bytes), added to the frequency low byte and written to `rNRx3`. It does not end the note; noise is excluded.
- `rNR50` starts `$77`, and is otherwise changed only by `A6` and by the palette-fade path (`StepMusicVolumeFade`, `wSoundFadeLevel/Target/Timer/Volume` `$C5E2`–`$C5E5`, run from `StepFade` only while `wFadeState` bit 7 is clear; the "start sound fade" helper has no caller).
- Panning: `hSndPanning` defaults to `$FF` and is reset to `$FF` by every track header; `ApplyPanning` replaces the channel's two bits of `wSoundEngineMode` with `hSndPanning & noteWork` (`noteWork` = `$11/$22/$44/$88` for ch1–4). All shipped data is centred.

## 8. Wave channel

- `SoundWaveSetTable` `$30CC` = `dw $30CE` (one entry): 16 wave images × 16 bytes = 32 four-bit samples, first sample in the low nibble. 0 = sine, 1 = triangle, 2 = square, 3 = sawtooth; 4–15 are stepped/decaying variants. Copied to `$FF30`–`$FF3F` with `rNR30 = 0`, then `rNR30 = $80`.
- Wave number = `swap(n)` = `16*n`; numbers ≥ 16 read past the table (mask to 0–15).
- Wave note order: copy pattern if the number changed → `rNR32 = hSndEnvelope` (raw level) → `rNR33` → `rNR31 = 0` → `rNR34 = (H&7)|$80` **only when `rNR52` bit 2 says the channel is off**, else `rNR34 = H&7` → `rNR31 &= $C0`.
- `A1` re-selects a wave mid-track; when a wave track ends (`$FF`) on slot 0/1 the pending pattern is loaded at the end of the next pass (`wSoundWaveReload` `$DD19`).

## 9. Noise channel

- Note bytes are `rNR43` values, not notes: `<$10` indexes `$38A0` (`00 01 11 12 14 23 07 15 17 32 33 60 61 45 53 62`), `$10`–`$1E` are the raw byte, `$1F` is a rest (envelope 0). LFSR width/divisor/shift are entirely whatever the byte says — the driver adds nothing.
- `rNR42` comes from the header/modulation like a pulse channel; `rNR41` is cleared after each trigger and `rNR44 = (H&7)|$80` (`H` is the noise "frequency" high byte, unused by hardware beyond the trigger bit). Percussion is written per event: sound id 18 (`$40:5C7D`, header `01 00 0F 00`) is `FD`/`FD` labels plus `1F 60` rests and repeated `31 01`/`41 01` hits with `BB F0`/`B7 F0` repeat counts. Volume slides apply; pitch offset does not.

## 10. Register write order (must be reproduced exactly)

Pulse ch1/2: `rNRx2` (only if changed → then `rNRx4` retrigger + length clear) → `rNR10` (ch1 only) → `rNRx3` → `rNRx1 = (duty<<6)|$3F` → `rNRx4 = $80|(H&7)` → `rNRx1 &= $C0`.
Wave ch3: `rNR30=0` → 16 bytes to `$FF30` → `rNR30=$80` → `rNR32` → `rNR33` → `rNR31=0` → `rNR34` (trigger only when inactive) → `rNR31 &= $C0`.
Noise ch4: `rNR42` → `rNR43` → `rNR44 = $80|(H&7)` → `rNR41 &= $C0`.
`rNR51` is written **once per frame**, at the end of `SoundTick`, as `wSoundEngineMode & wSoundSkipMaskA` (the slots processed that frame); `wSoundEngineMode` persists across frames, which is how stereo bits of ended and started tracks survive.

## 11. Music selection by map / area

`PlayMapMusic` `$02:6050` reads `wMapType` `$CC44`; bit 7 set takes the key-world byte lookup instead of the table. Otherwise `PlayMapMusic_ByMapId` `$02:609D` does `ldh a,[hMapId]` (`$FF90`) + `rst $00` dispatch through a 227-entry `dw` table at `$02:$60A0` (map ids 0–226; 25 `$0000` entries = no music). 202 maps use 21 handlers:

| handler | maps | default id | condition / variation |
|---|---|---|---|
| `$62DB` | 31 | `$19` (9) | Music19 |
| `$6372` | 58 | `$22` (12) | most common handler |
| `$6307` | 28 | `$1C` (10) | |
| `$6339` | 23 | `$25` (13) | |
| `$6268` | 22 | `$16` (8) | Music16, the field theme |
| `$62E0` | 15 | `$2E` (16) | flag `$23` → `$19` |
| `$631A` | 5 | `$2E` (16) | flag → `$1C` |
| `$6334` | 3 | `$CC` (128) | maps `$A1`–`$A3` |
| `$62BB` | 2 | `$0C` (5) | maps `$0D`, `$14` |
| `$62C0` | 2 | `$16` (8) | flags `$CC`/`$38` → `$CF` (129) |
| `$630C` | 2 | `$1C` (10) | player-state bit 3 → `$2B` (15) |
| `$6327` | 2 | `$1F` (11) | flag `$25` → `$1C`; maps `$A0`, `$A4` |
| 19 handlers, one map each | 19 | `$16`/`$2E`/`$CC`/`$76` | `$626D`, `$6291`, `$62ED`, `$634C`, `$6365`, `$6377` are screen/flag variants returning `$28`; `$62DA` leaves the music alone; `$62D5` (map `$1D`) plays SFX `$76` and no music; `$633E` (map 38) calls `InitSoundHardware`, i.e. silence |

- Several handlers inspect screen coordinates/flags and may return `$28` (14) instead, so one map can sound different per room.
- Key world (`wMapType` bit 7): `$86→$22`, `$85→$25`, `$84→$19`, `$83→$19`; otherwise a floor-info byte of 6 selects `$2B` when player-state bit 3 is set, else `$35` (18).
- `QueueIfNew` compares against `wCurrentMusic` and returns when equal, so **a screen change or map link never restarts the song**. A restart needs `wCurrentMusic = $FF` first (`RestartMapMusic` `$02:604B`, reached from a field-mode warp through `GameMode1_Init`) or a script queueing a new id. A 43,628-frame capture shows 41 starts, 9 stops, 0 restarts, 0 jingles.
- Field scripts: command `$0F` = `cp $FF` → `RestartMapMusic`, `cp $60` → `QueueMusic`, else `QueueSoundEffect`; ids `< $60` are thus music and `≥ $60` effects (map handlers themselves use `$CC`/`$CF` as music).
- Battle: `GameMode4_Init_PlayBattleMusic` (bank `$19`) queues `$0F` for `wBattleKind` 0/1 and `$13` (19) otherwise; traced arena loops queue `$02`, `$28`, `$44`, `$0F` per round. Boot is silent, the logo queues record 6 (song 3), the key sparkle plays effect 222, the ending uses sound 214 (song 132). There is no separate fanfare/jingle mechanism — a "fanfare" is just an effect id that starts 2 or 3 consecutive tracks.

## 12. Sound id → song id (rows of `assets/generated/song_table.inc`)

Song ids are not stored in the ROM: a song id is the index of the consecutive record group.

| sound id | song | where it is used |
|---|---|---|
| 2 | 2 | arena / battle scene (4 tracks) |
| 6 | 3 | title logo (3 tracks) |
| 9 | 4 | title menu |
| 15 | 6 | arena |
| 22 (`$16`) | 8 | field theme (22 maps) |
| 28 (`$1C`) | 10 | area/battle maps (28 maps) |
| 40 (`$28`) | 14 | script-scene theme and `$28` overrides |
| 68 (`$44`) | 23 | arena round (2 tracks) |
| 88 (`$58`) | 31 | 4-record scene |
| 96 (`$60`) | 43 | 2-track effect (noise) |
| 118 (`$76`) | 51 | map `$1D` ambience effect |
| 204 (`$CC`) | 128 | maps `$A1`–`$A3` |
| 207 (`$CF`) | 129 | conditional map theme |
| 214 (`$D6`) | 132 | ending |
| 222 (`$DE`) | — | boot key-sparkle effect |

## 13. What a reimplementation must match to sound identical

1. Tick = one VBlank, 59.7275 Hz, never a timer, no double-speed scaling.
2. The per-slot tempo accumulator, including the carry frame that skips *all* counters and the reset to `step` on header load and `AF`.
3. `rNRx2`'s write-only-if-changed rule plus the forced `$08` bit — this decides which notes retrigger.
4. The exact register order of §10 (`rNRx3` before `rNRx4`, `rNRx1` written twice on pulses, `rNR30` toggled around the wave copy, wave trigger only when the channel is inactive).
5. `rNR51` written once per frame from `wSoundEngineMode & processed-mask`, with `wSoundEngineMode` persisting between frames.
6. `StartSound`'s old-slot `rNR51` clearing keyed on the old `hTrackPosHi & 3`, plus the 4/3/2-id `StartMusic` lengths versus the 1/2/3-id `StartSoundEffect` lengths.
7. Frequency from the `$3B5C`/`$3B74` tables with `$0800 − (Q>>octave)`, not an equal-tempered formula; octave `o` = C(2+o).
8. Rests: envelope 0 on pulses/noise, `rNR30 = 0` on wave.
9. Noise bytes passed through unchanged as `rNR43` (LFSR parameters included in the byte).
10. `InitSoundHardware`'s `rNR50 = $77`, `rNR51 = 0`, slots starting `$FF`, labels cleared, then the per-record volume writes; and no fade at map transitions (the game has none).

## 14. Unknown / unconfirmed

- Byte-exact behaviour of `SoundTick_VolumeModulation` (`$00:3A94`–`$00:3B4F`) is decoded structurally, not A/B-verified against hardware; the code-as-data rows 13–15 are a known hazard.
- Labels ≥ 4 aliasing later channels' label bytes is a code fact, but no track has been shown to use it.
- Which effect ids are level-up/item/victory fanfares is undocumented; only 118 (map `$1D`) and 222 (boot) are identified.
- Behaviour of sound ids above 222 (past the `SoundBankTable` terminator) is undefined.

## Sources

- `re/notes/audio.md` — §4b driver/record facts, §6 command set and tables, §4c rendering, §4d ids.
- `re/notes/audio_handoff.md` — engine location, tick model, track/note format.
- `re/notes/map_music.md` — map jump table, 21 handlers, key-world lookup, script command `$0F`.
- `re/notes/field_script_run.md` — field-script sound command `$0F`.
- Session audits of the VBlank entry, `StartSound`, `InitSoundHardware`, tempo rules,
  wave/RAM details and the dead "wait for channels" machinery (internal working notes).
- Session trace analysis of `wCurrentMusic`, map-music restarts and per-scene sound ids.
- The reference disassembly: `home/bank00_home.asm` (every routine above), `ram.asm`
  (`wSound*` and `$FFD8`–`$FFF7` symbols), `engine/bank19_battle_load.asm` (battle
  music switch).
- `assets/generated/song_table.inc` — 223 rows: sound id → song id, slot byte, hw channel.
- ROM byte checks in `rom.gbc` (Tara's Adventure, USA): vectors `$0040/$0050/$0058`, every driver entry byte, `SoundBankTable`, the period/envelope/pitch/noise/wave tables, and sample tracks `$40:4071`, `$40:4077`, `$40:42F3`, `$40:4589`, `$40:5C7D`.
