# 7. The battle system

Cartridge reference for Dragon Warrior Monsters 2 (Tara's Adventure; the battle-relevant banks $16, $19, $1A, $30, $31, $32, $35, $36, $39, $3A and $0C are byte-identical in Cobi's Journey). ROM code is cited as `$BB:AAAA`; the file offset of `$BB:AAAA` is `BB*0x4000 + (AAAA-0x4000)`. A few routines were pinned only in the annotated listing and are cited as `bank31_battle_phases.asm:NNNN`. Facts marked *(not yet confirmed)* are not proven in the sources.

## 1. Slot numbering and per-slot state
The engine's native convention is slot 0-2 = player party, slot 3 = player helper, slot 4-6 = foe side, slot 7 = foe helper. Per-slot battle arrays use this order with stride 8 (words, e.g. `wBattleHP $D8BF`, `wBattleDEF $D90F`, `wBattleAGL $D91F`, `wBattleLevel $D8B7`), stride 7 (`wSlotResistances $DA72`), stride 9 (`wBattleStatus $D80C`) or stride 16 (`wBattleSkills $D989`, 8 skill ids at even offsets). The "foes first" numbering (0-2 foes, 4-6 party) is reached by the involution `(slot + 4) & 7`, which keeps the side and swaps the two helpers. Battler records exist only for the six real slots: `wBattlerRecordSlot1 $D123`, `Slot2 $D171`, `Slot4 $D1BF`, `Slot5 $D20D`, `Slot6 $D25B`.

## 2. Entry points
| Stage | Address |
|---|---|
| Field encounter roll | `$0A:$43DC` |
| Area description dispatch | `$0A:$476E` |
| 52 per-area loader stubs | ROM `0x28AD0` |
| Battle descriptor -> enemy list | `$0A:$4CBA` (writes `wEncounterMonsters $CFDC-$CFE1`, clears `$CFCF-$CFC5`) |
| Bank-1 handler | `bank_001.asm:6688-6738` (sets `wGameMode` = 4) |
| Game-mode dispatch | `$00:$0355`, table `$00:$0359`; mode 4 -> `$31:$4001` |
| Mode-4 init (battle shell) | `$31:$4001`, farcalls `$19:$4001` |
| Battle setup chain (party copy, enemy build) | `$19:$4001`, `$19:$4079`, `$19:$4557`, `$19:$46DD`, `$19:$4752` |
| Foe battler construction | `$1A:$63A7` |
| Per-frame battle update | `$31:$40A5` |

`$31:$40A5` runs the link joypad exchange and effect animation when `wLinkMode $C58A != 0`, otherwise increments play time and calls `RunBattlePhase`.

## 3. Phase machine
`RunBattlePhase $31:$40CC` dispatches on `wBattlePhase $CFC8`:

| wBattlePhase | meaning | step variable | dispatch |
|---|---|---|---|
| 0 | intro | `wBattleStep $CFC9` | `$31:$40D6`, table `$31:$40DA` |
| 1 | fight | `wBattleStep` | `$31:$43B2`, table `$31:$43B6` |
| 2 | battle end | `wBattleStep` | `$31:$43E6`, table `$31:$43EA` |

Phase 0 steps: 0 wait for `wFadeState == 0`, 1 draw screen (`$31:$47A9`), 2 intro message (`$31:$4106`, exchanges player names when linked), 3 surprise round (`~$31:$4248`), 4 `StartFightPhase` (increments `wBattlePhase`, clears `wBattleStep`, returns `wBattleArg0 $D868`, 0 = normal/party surprise, 1 = foes struck first).
Phase 1 steps: 0 `BattleFight_BeginRound` (runs `StartRound`, then step 1), 1 `RunBattleSetup` (tactic window, then the FIGHT/PLAN/ITEM/FLEE menu), 2 farcall `RunBattleCommandEntry` (bank $30), 3 farcall `RunBattleActions` (bank $32), 4 farcall `RunBattleStep4`.
Phase 2 steps (10): 0 draw screen, 1 result, 2 wait for sound, 3 records and EXP sum (`$31:$449C`, `$31:$44B0`), 4 award EXP, 5 join offer (`$31:$46CA`), 6 return to field, 7-8 link finish, 9 queue end sound.
Round loop: `StartRound` marks every slot -> command entry per actor -> speed list and sort -> action queue -> per-action resolve machine -> wear-off and poison -> marks refilled. The fight ends when one side has no able battler; `wBattleScene $D092` carries the result (0 win, 1 party wiped, 2 foes left the field, 3 gave up). `StartRound` also sets bit 7 of all eight `wSideControl $DAD8` bytes, clears `wPersonalityActs $D854` (16 bytes), `wActionQueue $D895` (10 bytes), sets `wBattleActionChoice $DA1C` to `$FF` (16 bytes), `wBattleItemTarget`/`wBattleItemId` to `$FF`, `wMenuState` to 0, then marks slots: 3 = empty/out, 1 = blocked (§5), else 0. If every party slot is still 0 it skips the command menu and advances `wBattleStep`.

## 4. Surprise round
Part 3 of phase 0 is the only initiative roll in the game. It returns at once for `wLinkMode != 0` or `wBattleKind $CFC5 >= 2`, setting `wBattleTurn $D891 = 1`. Otherwise one table byte is drawn: `wRandomLo < 8` means the party surprises (`wBattleArg0 = 0`, string `$0B + (wRandomHi & 1)`); else a second byte is drawn and `wRandomHi < 8` means the foes surprise (`wBattleArg0 = 1`, string `$0D + (wRandomLo & 1)`); otherwise `wBattleTurn = 1`. The struck side's three `wSlotMarks` become 3 (`$FF` for an empty slot), so it loses that round; the message is category-0 bank $2F text ("appeared stunned!" `$0C`, "suddenly attacked!" `$0D`, "struck without warning!" `$0E`), then `wBattlePhase` is decremented and `wBattleStep` set to 4 so the phase runs again.

## 5. Command entry: action and target
`RunBattleCommandEntry` (bank $30) dispatches on `wBattleSubPhase $CFCA` at `$30:$4006` (table `$30:$4008`): 1 next actor, 2 `AIChooseActionResolveStep $30:$4579`, 3 choose target, 4 list speeds, 5 sort, 6 totals. Next actor walks `wBattleActor $D8A4` from 0 to 7; a present slot marked 1 enters command entry (`wBattleSubPhase += 1`, `wBattleResolveStep = 0`), and after slot 7 it jumps straight to step 4. Choosing a target marks the acting slot 2, resets the sub-phase and increments the actor.

`ChooseActionTarget $39:$4001`: `wBattleActionId = wBattleActionChoice[2*actor]`; `mode = wSlotAIMode $DA53[actor]` indexes `ActionTargetModeTable + 4*mode`, holding two word pointers (the second table applies to slots 4-7 when `wLinkMode` is 0 or 2, otherwise the first); `add hl,bc` twice reaches a 228-entry per-action routine, which writes `wBattleTargetChoice[2*actor]`. `TargetRandomFoe` scans the opposite three slots (4-6 for actors 0-3, 0-2 for 4-7), keeping the first present slot and replacing it with every later present slot when `wRandomLo` bit 7 is set *after* one `AdvanceRandom` (later slots are favoured; one PRNG step). `TargetSavedSlotOrRandomFoe` uses the stored slot when present (a value >= 8 counts as absent).

Player commands: action id 0 = Fight (plain ATTACK, skill data id 0), a skill's data id (name id + 1) = Skill, `$AC` = Guard with the target forced to self (`$31:$529E`). A monster's tactic is `wSlotTactic $DA43` low 2 bits (saved in MON_SEX bits 4-5):

| value | tactic | behaviour |
|---|---|---|
| 0 | Charge | AI acts, attack-biased |
| 1 | Mixed | AI acts, neutral |
| 2 | Defense | AI acts, support/guard-biased |
| 3 | Command | the player chooses Fight/Skill/Guard for this monster |

For tactics 0-2 the monster's `wBattleActionChoice` byte is cleared to `$FF` and filled by the AI.

Blocked monsters (no command at all): `CheckSlotStatusBlock $00:$3E25` returns carry for status byte 0 bits 4/6/7 (confused, paralyzed, asleep), byte 3 bits 0-5 (frozen, dancing, tripped, shivering, cowering, vacant), byte 5 bits 6-7 (ironized). The wide variant used at round start (bank $31, listing region `bank31_battle_phases.asm:7BEE`) adds byte 3 bits 6-7 (airborne) and byte 4 bits 2-3 (high jump). A tactic is never a blocked case.

Forced actions, first set bit wins (`ForcedActionForActorStatus`, bank $30): byte 3 bit 6 airborne -> `$CD`; byte 4 bit 2 high jump -> `$CC`; byte 5 bit 4 song -> `$CE`; byte 8 bit 0 love rain -> `$CF`.

Obedience roll for the player's monsters with tactic 0-2 (`CheckObeys`, bank $30): the monster ignores the tactic when `trait/4 + tacticByte/4 + PersonalityTacticWeights[personality*4 + tactic] < wBattleExtraStat/16 + rand(0..63)`. Paralyzed monsters always obey; tactic 3 always obeys.

## 6. Action order: the speed list
`RunBattleCommandEntry_ListSpeeds $30:$4160` clears `wActionQueue` (9 bytes `$FF`), `wBattleArg0` (9 bytes), `wBattleTempBuf $D87D` (18 bytes), sets `wActionQueuePos = 0`, `wLoadSlot = 0`, `DE = $0800`, and for each present slot marked 2: (1) one `AdvanceRandom`, value discarded; (2) `BC = wBattleAGL[slot]`, `A = 3`, `Multiply8By16`, `/10` -> `3*AGL/10` (floor); (3) speed = `RandomInRange(3*AGL/10, AGL)`; (4) `AddActionSpeedBonus` - `+3000` for action `$62` or `$D8` (always first), action `$69` replaces the speed with `rand(1..9)` (one `AdvanceRandom`, `wRandomLo mod 9 + 1`), otherwise a skill adds `1000` when skill-record byte 5 bit 2 is set, else `10`, and `AddActionSpeedBonus_BankA1` adds `2000` for those skills using the second random stream; (5) speed into `wBattleTempBuf`, slot number into `wBattleArg0`. The item turn is appended as slot id `$10` with speed 2010 (`$30:$429D`).

`SortBySpeed $30:$42B7`: 8 bubble passes, fastest first, slot numbers swapped with their speeds. A pair swaps when the later speed is *not lower*, so equal speeds swap too: two equal speeds keep their original order, three come out reversed. The sorted slot numbers are copied into `wActionQueue` until `$FF`. No PRNG use.

## 7. Damage
`RunBattleActions` (bank $32) walks the queue; sub-phase 0 is `RunBattleActions_StatusChecks` (10 resolve steps: start action, check action/MP/target, personality text, action text, break free, select effect, shatter checks, link rule check, pay MP, dropped dead). The item turn (`$10`) branches to sub-phase 8. The effect machine for one action is `RunBattleResolveStep $36:$4001`, 16 cases on `wBattleResolveStep $CFCB`: 0 begin, 1 target reactions, 2 effect `$82`, 3 rolled out of the way, 4 effect checks, 5 critical roll, 6 action effect (resistance roll), 7 compute damage, 8 sound, 9 effect flags, 10 damage message, 11 branch on action, 12 apply damage, 13 defeat, 14 aftermath, 15 advance. Damage path = 6 -> 7 -> 12 -> 13.

### 7.1 Physical formula (`ComputeAttackDamage $36:$5011`, `ComputeBasicDamage $36:$5023`)
```
AdvanceRandom                                     ; one PRNG step, value discarded
d    = wBattleDEF[target] / 2                     ; floor
ATK  = wBattleATK[actor]
if ATK <= d:            return RandomInRange(0, 1)                        ; 2 steps total
half = (ATK - d) / 2                              ; floor
if (ATK >> 4) >= half:  return RandomInRange(0, ATK >> 4)                 ; 2 steps
return half + RandomInRange(-(half>>4), half>>4) + RandomInRange(-1, 1)   ; 4 steps
```
16-bit arithmetic with wraps, floor division throughout, no minimum of 1 (0 damage is legal). The "weak hit" branch is `ATK/16 >= half`, i.e. `d >= 7*ATK/8`. The result is stored in `wBattleDamageLo/Hi $D872/$D873`. Round-70 trace: Slash ATK 10 vs CactiBall DEF 4 -> 4; CactiBall ATK 11 vs Slash DEF 7 -> 3; both are the low roll of `half + rand(-1..1)`.

### 7.2 Resistance scaling
A picker selects one of four 16-bit tables from `wBattleStatus8 $D814`, testing bit 6 then bit 7; the chosen 2-bit level (0-3) from `wSlotResistances` indexes the table.

| picker | bit 6 set | bit 7 set | neither |
|---|---|---|---|
| default | `1_075_04_0` | `131_116_075_03` | `1_085_05_0` |
| alt | `075_05_025_0` | `131_116_075_03` | `1_075_04_0` |
| bit6 | `1_085_05_0` | `131_116_075_03` | `131_116_075_03` |

| table | level 0 | level 1 | level 2 | level 3 |
|---|---|---|---|---|
| `1_085_05_0` | d | d*85/100 | d/2 | 0 |
| `1_075_04_0` | d | d/2 + d/4 | (d*8/10)/2 | 0 |
| `131_116_075_03` | d + d/4 + d/16 | d + d/8 + d/32 | d/2 + d/4 | (d*6/10)/2 |
| `075_05_025_0` | d/2 + d/4 | d/2 | d/4 | 0 |

All values are 16-bit and wrap (d = 65535 at level 0/1 of `131_116_075_03` gives 20477 / 10237); divisions floor; level 3 is immunity. Level source, `wSlotResistances $DA72` (7 bytes per slot): byte 0 - bits 1-0 Bang, 3-2 Firebal, 5-4 Blaze/BigBang; byte 1 - 7-6 Vacuum, 5-4 Bolt, 3-2 IceBolt, 1-0 Radiant; byte 2 - 7-6 Sleep, 5-4 Beat, 3-2 RobMagic, 1-0 StopSpell; byte 3 - 7-6 PanicAll, 5-4 Sap, 3-2 Slow, 1-0 Sacrifice; byte 4 - 7-6 MegaMagic, 5-4 FireAir, 3-2 FrigidAir, 1-0 PoisonGas; byte 5 - 7-6 PalsyAir, 5-4 Curse, 3-2 LegSweep, 1-0 DanceShut; byte 6 - 7-6 MouthShut, 5-4 RockThrow, 3-2 GigaSlash, 1-0 unused.

### 7.3 Step-7 modifiers (`ResolveStepComputeDamage`, bank $36)
`rec5`/`rec6` are skill-record bytes 5/6 (plain attack = 0/0). The order is fixed: (1) `rec6` bit 4 with actor status byte 1 bit 2 (attack doubled) -> x2; (2) `rec6` bit 3 with actor status byte 2 bit 7 (critical rolled) -> clear the bit, damage = `RandomInRange(ATK - ATK/20, ATK + ATK/20)` (one PRNG step), personality bonus skipped; (3) `rec6` bit 5 with actor status byte 4 bit 0 (charge up) -> x2; (4) `rec5` bit 1 with actor status byte 4 bit 4 (suck air) -> `RandomInRange(2d, 2d + d/2)` (one step); (5) actor `wPersonalityActs` bit 6 ("pumped up") -> `damage += damage/2`; (6) target `wBattleStatus7` bits 0-2: bit 2 (counter) with `rec5` bit 7 -> /2, bit 0 (guard) with `rec6` bit 7 -> /2, bit 1 (damage x10 flag) alone with `rec6` bit 7 -> /10, then target `wPersonalityActs` bit 1 ("tucked in fear") -> /2; (7) target status byte 6 bit 2 (berserk) with `rec5` bit 7 -> x2, except actions `$6F` (ramming) and `$70` (kamikaze). Doublings wrap at 65536; halvings floor.

### 7.4 Applying and defeat
`ApplyDamageToTarget` (bank $32) switches on the top two bits of `wResolveMsgArg`: `00` nothing, `01` sets level-up-gain flags only, `10`/`11` do `wBattleHP[target] = max(0, HP - damage)`. HP 0 -> resolve step 13, which sets `wBattleSlotOut[slot] = 1` and clears the status record.

### 7.5 Instant-death gate (`$36:$5B19`)
This routine rolls no damage; it returns one carry bit ("the effect happens"). `$36:$6141` returns early when `wBattlePhase` is 2 or 3 and the actor is a party slot (< 4). Then `class = (wSlotResistances[7*target + 2] >> 4) & 3` (byte 2 bits 5-4 = Beat/instant-death resistance). `$36:$65B6` leaves class 3 intact and turns any other class into 4 when actor `wPersonalityActs[actor]` bit 2 ("concentrated") is set; class 4 -> carry set. Otherwise the skill id in `wBattleSkill $D8A6` picks one of three branch sets, each then testing status byte 0 bits 6/7 of the target:

| skills | enters | bit 6 | bit 7 | neither |
|---|---|---|---|---|
| `$00`, `$01-$12`, `$14`, `$79` | `$36:$620F` | - | `$6278` | `$62B1` |
| `$82` | `$36:$61F9` | `$62B1` | `$628E` | `$629B` |
| all others | `$36:$61D6` | `$629B` | `$628E` | `$6278` |

The leaf picks one of seven PRNG executors for classes 0/1/2 (`$636A $6373 $637C $6385 $638E $6397 $63A0`); class 3 -> carry clear, class 4 -> carry set. Leaf `$62B1` also branches on the side: with `wLinkMode == 1` or a foe target it uses `$6373/$637C/$6397`, for a party target (`wBattleTarget < 4`) the stricter `$6353` = `$637C/$638E/$63A0`. Each executor does one `AdvanceRandom` and sets carry iff `wRandomLo <` threshold: `$636A` 216 (84.4%), `$6373` 191 (74.6%), `$637C` 127 (49.6%), `$6385` 102 (39.8%), `$638E` 76 (29.7%), `$6397` 63 (24.6%), `$63A0` 38 (14.8%). Carry set means the effect lands: the caller `$36:$6B9F` jumps away on carry clear, and on carry set zeroes the target's HP and writes damage 1000 (`$03E8`) at `$36:$6BA4`. Beat, Defeat, K.O.Dance and UltraDown all route through this gate. Which physical status corresponds to byte 0 bit 6 vs bit 7 is *(not yet confirmed)*.

Skill records are 17 bytes each at ROM `0x680D4`, fetched by `$1A:$4001` with `HL = data_id*17 + 0x40D4`; data id = name id + 1, and `$FF` is the "no skill" sentinel. Record bytes 9-16 are consumed only by the effect executor `$39:$5F0E` (base damage = preset + `uniform[0..random]`); the gate above uses fixed thresholds. Skill learning prerequisites are a separate table of 60 x 18-byte records at `$1A:$6900A` (16 data bytes + `FF FF`), bytes 11-12 = minimum INT, consumed by code not yet located.

## 8. Status effects
`wBattleStatus $D80C` is 9 bytes per slot; `wBattleStatus1 $D80D` is byte 1 of slot 0.

| byte | bit(s) | meaning | effect |
|---|---|---|---|
| 0 | 7 | asleep | blocks command |
| 0 | 6 | paralyzed | blocks command; forces `$CA` when high-jumping |
| 0 | 5 | cursed | status mark |
| 0 | 4 | confused | blocks command; confused actor takes a random action |
| 0 | 2-3 | sleep counter | mark only |
| 0 | 1 | badly poisoned | round-end damage max HP/6 (1..150) |
| 0 | 0 | poisoned | round-end damage max HP/16 (1..50) |
| 1 | 2 | attack doubled | damage x2 (`rec6` bit 4) |
| 1 | 3 | critical | AI heal weight +`$1E` |
| 2 | 7 | critical rolled | damage replaced by +-5% ATK roll (`rec6` bit 3) |
| 3 | 0-5 | frozen, dancing, tripped, shivering, cowering, vacant | blocks command |
| 3 | 6-7 | airborne | wide block; forced action `$CD` |
| 4 | 0 | charge up | damage x2 (`rec6` bit 5) |
| 4 | 2-3 | high jump | wide block; forced action `$CC` |
| 4 | 4 | suck air | drain formula (`rec5` bit 1) |
| 4 | 0,1,4,5 (mask `$33`) | status set | AI heal weight +`$1E` |
| 5 | 6-7 | ironized | blocks command; turn text `$15` |
| 5 | 4 | song forced | forced action `$CE` |
| 6 | 2 | berserk | damage x2 (`rec5` bit 7) except ramming/kamikaze |
| 7 | 0 | guard | damage /2 (`rec6` bit 7) |
| 7 | 1 | damage x10 flag | damage /10 (with `rec6` bit 7) |
| 7 | 2 | counter | damage /2 (`rec5` bit 7) |
| 8 | 0 | love rain forced | forced action `$CF` |
| 8 | 3 | unused | wide block tests it, never set |

Poison and turn-limited statuses wear off in `RunBattleActions_WearOffAndDefeat` (bank $3A) at the end of the round; waking up, breaking a curse and shattering each have their own resolve step and text. Poison damage can kill.

## 9. Rewards
- EXP pool: `BattleEnd_Records_SumExpAward $31:$44B0` clears the 24-bit `wBattleExpAward $DA6B` and adds the 3-byte EXP field of each foe battler record (`$D1D7`, `$D225`, `$D273`) only when that slot's `wBattleSlotOut == 1`. Standing foes and helpers add nothing.
- Split: `BattleEnd_GainExperience` (`bank31_battle_phases.asm:7052`), 10 parts on `wBattleResolveStep`; part 0 skips EXP for battle kinds 4, 5 and 8+, sets `d` = number of standing party slots and divides the pool by `d` (floor); each standing monster receives that share.
- Cap: `AddExpToRecordCCapped` adds the share to MON_EXP (save record `$58`, 3 bytes LE), wraps 24-bit, then clamps to `$98967F` = 9,999,999.
- Farm: `DivideBattleExpAwardByModeFactor` divides the pool by 20 (farm level 0), 15 (level 1) or 10 (higher) and adds that to every farm monster, same cap.
- Wild EXP: `AccumulateGrowthForLevelsTemp1` (`bank19_battle_load.asm:1845`) turns `base_exp` X and level L into `S = sum(c=1..L)(c*X/20)` (floor per term, remainders collected in one byte and divided by 20 once), then `S/3`; battle kind 3 leaves the terms undivided and shifts `S >>= 2`; `S = max(S, 1)`, `S = min(S, 65535)`, stored as a 3-byte BATTLER_EXP with the high byte 0. Roster (trainer/arena) foes carry a literal EXP in record bytes 6-7 instead.
- Level-up check `RecordReachedNextLevelExp` (`bank31_battle_phases.asm:8080`): blocked at MON_MAX_LEVEL; else true when MON_EXP >= `ExpTable[curve][MON_LEVEL]`. The table (32 x 99 x 3 bytes at `$19:$4E60`, stride 297) stores the requirement for the *next* level, entry 0 being level 1.
- Level-up gains `ComputeLevelUpStatGainsForBattleArg1` (`bank1a_skill_prereqs.asm:3020`): per stat `gain = StatGrowthTable[growth[stat]][MON_LEVEL]` (32 x 99 bytes at `$1A:$2617`, `+ $63*row + level`), plus a 0..4 growth-item bonus on the item's stat, clamped so the stat stays below 999. Applying (`bank31_battle_phases.asm:7461`) increments MON_LEVEL and adds to MAX_HP/MAX_MP/ATK/DEF/AGL/INT; current HP and MP are unchanged.
- Gold and item drops: none at battle end. No routine in banks $0A, $16, $19, $30, $31, $32, $35, $36, $39, $3A or $A0 awards gold or an item when the battle ends; gold comes only from field events, chests, arena prizes and shops.
- Join offer `DecideJoinOffer $16:$5B7E` (phase 2 step 5, `$31:$46CA`): no offer when linked, when the kind is 3, 4, 5 or 8+, when the slot is not 4-6, or when the species join class is 7. A 16-bit meter is scaled (first sighting x{5, 2, 1, 1/2, 1/5, 1/16}; already seen x{1, 1/4, 1/8, 1/8, 1/8, 1/20}), reduced by `rand%91 + 10`, rejected when bit 15 ends up set, then `rand%100 + 1 < 91` decides. A first sighting also rolls `rand%200` against `JoinChanceByClass $16:$5CFB`. Accepted monsters are shaped at `$16:$7364` and stored on the farm.

## 10. Fleeing
`TryFlee $31:$4D95` tests, in order: `wBattleTurn == 0` (always succeeds); party maximum level > foe maximum + 5; one table byte with `roll = (byte & 7) + 1` and `threshold = wBattleTurn < 4 ? wBattleTurn : 7`, success when `roll <= threshold` (1/8, 2/8, 3/8, then 7/8); no able foe (`CountAbleFoes == 0`). Otherwise string `$2C` ("But the escape route was cut") and the turn is lost: every present party slot is marked 3 and the sub-phase goes to 3, so only the foes act (no action, no MP cost, no "miss"; poison still ticks). A successful flee in a non-link battle lowers personality (`$31:$4E54`) and sets `wBattleScene = 2`.

Refusal gate `$31:$4CBC`: `wLinkMode != 0` refuses before reading the kind (string `$20`); kinds 2, 3, 5, 6 and 7 also give `$20` ("No fleeing from this battle!"); kind 4 and 8+ switch to sub-step `$0B`, the "Retire now?" yes/no.

## 11. AI
Tables, all in bank $30: `PersonalityTacticWeights $30:$5587` (file `0x0C1587`, 108 bytes = 27 x 4), `SkillAIBaseWeightTable $30:$55F3` (`0x0C15F3`, 402 bytes = 201 words), `AIScoreRoutineTableA $30:$5785` (`0x0C1785`, 603 bytes) and `AIScoreRoutineTableB $30:$59E0` (`0x0C19E0`, 603 bytes), `AIModeRoutineTable $30:$45D0` (`0x0C05D0`, 10 bytes), `AIChoiceRoutineTable $30:$4998` (`0x0C0998`, 6 bytes). A and B are byte-identical, so mode 4 behaves exactly like modes 1-3. Personality rows are patterns of `{$14, $0F, $05}` over Charge/Mixed/Defense, fourth entry 0 except personality 5 = `$0A`; this table feeds the disobedience roll, not the action choice. Base weights: 166 of 201 non-zero, min 50, max 110, sum 15280; a zero entry is never scored.

Mode `SetSlotAIModeFromINT $19:$4298`: INT < 30 -> 0; 30-99 -> 1; 100-549 -> 2; 550-899 -> 3; >= 900 -> 4. `AIModeRoutineTable` maps 0 to `AIRunNextChoice $30:$4946` (random pick within a kind) and 1-4 to the scoring routines `$30:$4AD3` / `$30:$4AC6`.

Scoring: `InitAIWeightsForActor $30:$45DA` clears the ten words of `wAIWeights $D2AD`, sets `wAIChoiceWeights $DA3C = {0,0,0}`, `wAIChoiceOrder $DA3F = {1,2,3}`, `wAIChoiceIndex $DA42 = 3`, then adds, each saturating to 0..`$FF`: (1) command bias - FIGHT adds `$2D` to the tactic's own weight (tactics 0-2 only), any other command adds `$14` to the previous tactic's weight; (2) personality tens - weight[i] += personality byte i / 10 (`$D968`, `$D970`, `$D978`); (3) status and HP - `+$1E` to charge when the actor is critical or `status4 & $33` and the command is not FIGHT, `+$1E` to defense when an ally is below 1/6 HP and the actor owns a healing skill (`$16-$20`, `$7B`, `$7C`, `$9F-$A1`) and mode is 3 or 4 and the tactic is not Command, and on turn 0 for a party actor outside link play with menu bit 0 clear, `-30` to defense; (4) random - player-style actors add `wRandomLo & $0F` per weight (one `AdvanceRandom` each), foe-style actors add `RandomInRange(0, band)` with band 30/25/20/15/10 for personality < 50/< 100/< 150/< 200/else.

`SortAIChoiceWeightsAndWeightSkills $30:$483F` runs three compare-swaps (0-1, 1-2, 0-1) moving the order array with the weights. Equal weights are ordered by single bits of the *current* random word (`wRandomHi` bit 0, `wRandomLo` bit 0, `wRandomHi` bit 1), not by a new roll, so equal weights are not stable. Then `order[0]`'s skills get `+$32` (doubled to `$64` under FIGHT, 0 under Command or Defense), `order[1]`'s get `+$19`, and the attack word (index 8) and guard word (index 9) are seeded according to `order[0]`.

`ScoreSkillForAI $30:$4BA0`: skill `$FF` -> `$FFFF`; else add the base weight, one `AdvanceRandom` adding `wRandomLo & $3F`, reject when skill-record byte 3 bit 0 is clear, else farcall the skill's bank-$E2 scoring routine and combine its two outputs; a result with bit 15 set becomes `$FFFF`. `ChooseHighestWeightedAction $30:$4C00` takes the largest word; each tie consumes one `AdvanceRandom` and replaces the candidate only when `wRandomLo` bit 0 is set; all `$FFFF` falls back to action 0. Guard is quartered for helpers and the foe side.

Randomness everywhere is the table PRNG: `AdvanceRandom` = `NextTableByte $00:$095B`, `wRandomHi $C5E8 = (wRandomHi + 1) & $7F`, `wRandomLo $C5E7 = table[wRandomHi]` (128 bytes at `$00:$0973`), and `RandomInRange(lo, hi) = lo + ((wRandomHi << 8) | wRandomLo) mod (hi - lo + 1)`, with `lo == hi` returning `lo` without a step. It is not the LCG used for key generation. PRNG steps per decision: 3 for random weights (either style), 0 for tactic Command, 0 for the sort, 1 per non-empty kind list in mode 0, 1 per scored skill with a non-zero base weight, 1 per tie in the highest-weight choice.

## 12. Arena and tournament battles
Arena fights use the same battle engine; only setup and aftermath differ. A tournament is 3 single 3v3 battles (`ArenaMenu_AfterRound $0C:$6A6A`, `ArenaMenu_AfterRoundAgain $0C:$6E59`), each putting three monster-table ids into `wEncounterMonsters`. A round is won iff `wBattleScene == 0`. `wArenaRank $C82C` (saved as one byte at SRAM file `0x3D2F`, not clamped on load) selects the flavour: 0 = kiddie cup, fixed teams, no fee, scripted first magic key; 1-4 = classes C, B, A, S with fixed teams, fees 100/500/1000/5000 and a new key; 5+ = champion loop, random ladders, fees 1000/2000/3000/5000, random prize. The rank increments only in `ArenaMenu_AfterRound` (`$0C:$6A8B`), so rank 5 is terminal. Losing resets the arena state without rank change, refund or prize, and the arena heals the whole party on exit (bank $12). Prize tables live at `$0C:$75D2`/`$0C:$7602`: `$FE` generates a key (6000 gold when the ring is full), `$FD` rolls one of four 7-entry item lists (game ids 64-83 and 90-97) from the `random mod 52` quotient, 1..98 give that item directly, and a full inventory converts to 6000 gold.

Arena foes are prebuilt 26-byte roster records, not species recomputed from growth: `[0-1]` species, `[2-5]` skills, `[6-7]` EXP, `[8]` join class, `[9]` level, `[10-21]` HP/MP/ATK/DEF/AGL/INT, `[22-25]` growth/personality. Ids below `$250` load from `34:$4075 + 26*id`; ids `$250+` load from `$A2:$4056 + 26*(id - $24F)`.

## 13. Link battles
A linked battle is mode 4 with `wLinkMode != 0`. The only battle payload is the 19-byte command block sent by `RunBattleSetup_SendLinkChoices $31:$5CED` (sync byte `$01` from `$31:$5CDD`) and unpacked by `$31:$5DA7` when `wLinkMessage == $F0`:

| bytes | content |
|---|---|
| 0-2 | `wSlotTactic` of slots 0-2 (or 4-6 when `wLinkRole` bit 1 is set) |
| 3-4 | `wRandomLo`, `wRandomHi` (the battle seed) |
| 5-6 | `wMenuState`, twice |
| 7-12 | `wBattleActionChoice[0..5]` |
| 13-15 | `wSlotMarks[0..2]` (or 4-6) |
| 16-18 | `wSideControl[0..2]` (or 4-6) |

The side whose `wLinkRole` bit 1 is clear copies its random pair into `wRandomSeed2Lo/Hi $C5BA/$C5BB`; the other side loads its `wRandomLo/Hi` from that exchange, so both sides share the battle seed (the second stream serves link-side rolls). `$31:$4106` also exchanges the 10-byte player name at battle start. Linked battles refuse fleeing and, for kinds 4/5, items. The link protocol has no checksum.

## 14. Details a reimplementation must reproduce
- One PRNG stream shared by damage, speed, AI, targeting, the instant-death gate and fleeing; any extra or missing call changes the whole battle. `RandomInRange(lo, lo)` consumes nothing.
- Speed: `RandomInRange(3*AGL/10, AGL)` after one discarded roll, bonuses `+3000`/`+1000`/`+10`/2010, 8-pass bubble sort that swaps on equal speeds (two equal keep order, three invert), item turn slot id `$10`.
- Marks: 1 blocked, 2 acted, 3 pending; a surprise round or a failed flee writes 3 for the whole side.
- 16-bit wrap and floor division everywhere; no minimum damage of 1; EXP clamped to 9,999,999.
- Critical replaces damage with the +-5% ATK roll and skips the personality bonus; it never multiplies. Instant-death: class 3 immune, class 0 always lands, "concentrated" forces a landing; thresholds are `wRandomLo <` values from §7.5.
- AI ties use bits of the current random word, and equal weights are not stable.
- Message framing: two 18-cell lines at (8, 112) and (8, 128) in the 160x40 window at tile row 13; glyph codes are font-cell indices; numbers right-aligned; status marks replace the "Lv:" row; no "Round N" text exists.
- `wBattleScene` is the only result handed back to the field and the arena: 0 win, 1 party wiped, 2 fled or foes gone, 3 gave up. EXP and join offers happen only on a win; there is never gold or an item drop from a battle.

## Sources
- re/notes/battle_flow.md
- re/notes/battle_damage_full.md
- re/notes/battle_commands.md
- re/notes/battle_resolve.md
- re/notes/battle_resolve_handoff.md
- re/notes/battle_ai.md
- re/notes/battle_reward.md
- re/notes/battle_layout.md
- re/notes/battle_text.md
- re/notes/skill_damage.md
- re/notes/skill_requirements.md
- re/notes/arena_data.md
- re/notes/arena_teams.md
- re/notes/arena_rank.md
- re/notes/arena_tournament.md
- re/notes/link_cable.md (§5.2)
- Annotated disassembly: `engine/bank30_battle_commands.asm`, `bank31_battle_phases.asm`,
  `bank32_battle_actions.asm`, `bank36_battle_effects.asm`, `bank39_battle_targets.asm`,
  `bank3a_battle_effect_steps.asm`, and `ram.asm`.
