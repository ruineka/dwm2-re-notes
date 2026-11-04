# HOW-TO: reverse-engineering a Game Boy Color game

This is about *method*, not about one repository. The running example is
**Dragon Warrior Monsters 2** (two 4 MiB MBC5 cartridges, shared engine, 15 banks
of difference), because it exercises nearly every problem a GBC game can pose:
banked code, a script VM, a text engine, generated content, a link protocol, and
two editions that must be told apart. Everything below applies to any GBC title.

The questions this answers:

* where do you even start, and in what order;
* how do you keep from believing wrong things (you will, repeatedly);
* how do you *notice* that you are wrong and correct course;
* how would a strong frontier model work one of these problems if it had to be
  accurate rather than fast.

Vocabulary lives in [`GLOSSARY.md`](GLOSSARY.md) (every term, its definition, and
the search phrase that finds the authoritative source); §12 is the short version.

---

## 1. What the problem actually is

A GBC cartridge is a complete, closed, deterministic machine description:

* a 4 MiB (32 Mbit) address space split into 256 banks of 16 KiB;
* `$0000–$3FFF` fixed, `$4000–$7FFF` switchable (MBC5: write the low bank number
  to `$2000–$2FFF`, the high bit to `$3000–$3FFF`);
* 8 KiB WRAM in two 4 KiB windows, four banks via `SVBK $FF70`;
* 16 KiB VRAM in two banks via `VBK $FF4F`; palettes via `BCPS/BCPD/OCPS/OCPD`
  (`$FF68–$FF6B`); OAM DMA through `$FF46`; HDMA through `$FF51–$FF55`;
* five interrupt vectors (`$40` VBlank, `$48` STAT, `$50` timer, `$58` serial,
  `$60` joypad) plus the `RST` vectors;
* one frame = 70,224 cycles at 4,194,304 Hz = 59.7275 Hz (in double speed the
  CPU runs at 8,388,608 Hz but the frame keeps its duration).

Two consequences shape everything you will do:

1. **There is no hidden state.** Whatever the game does, it does by reading and
   writing those addresses. If you can see the addresses, you can explain it.
2. **It is deterministic.** The same inputs from the same power-on produce the
   same frames, byte for byte. Any disagreement between two implementations is a
   fact you can bisect, not a mystery.

So the work is not "guess what the developer meant". It is: find the code, find
the data, and then make your implementation agree with the machine — with a test
that tells you when it stops agreeing.

---

## 2. The first two weeks: an order that pays off

Do these in order. Each one makes the next cheaper.

1. **Identify the cartridge.** Header at `$0100–$014F`: entry point, logo
   (`$0104`), title (`$0134`), CGB flag (`$0143`: `$80` compatible / `$C0` only),
   cart type (`$0147`), ROM size (`$0148`), RAM size (`$0149`), version (`$014C`),
   header checksum (`$014D`), global checksum (`$014E–$4F`). Hash the file and
   write the hash down; every later measurement is only valid for that image.
2. **Map the banks.** For each of the 256 banks compute: unique byte count,
   longest run of `$00`/`$FF`, and a byte-class histogram. Pure-padding banks,
   mostly-ASCII banks, banks full of `$00–$1F` (opcode-shaped) and banks full of
   `$C0–$DF`+small values (pointer-shaped) tell you immediately where the code,
   the text, the tables and the graphics are.
3. **Find the skeleton.** Disassemble the fixed bank `$0000–$3FFF`: the vectors
   at `$0040…` land in the game's own handlers, and the boot path ends in a main
   loop with a mode variable. That loop and that variable are the spine of the
   game — everything else is a subroutine hanging off it.
4. **Build the frame contract.** Read the VBlank handler end to end and write
   down, in order, everything it does: OAM DMA, palette flush, scroll write,
   sound tick, random-seed step, mode update, text step, fade step. Every timing
   bug you ever chase will be explained by a line in that list.
5. **Discover RAM by observation, not by guess.** Run the emulator with a memory
   viewer; change one thing in the game (walk one cell, open the menu, gain gold)
   and see which bytes move. Name the variable by what makes it move. This is
   where most of your early certainty comes from, and it costs minutes per
   variable.
6. **Find the text system early.** Text is the interface between you and
   everything you need to navigate: menus, names, signs, the story. Locate where
   strings live (search the ROM byte patterns once you know a handful of glyphs),
   find the terminator, find the printer routine, and build a decoder. Once text
   is readable, every kind of note becomes cheap.
7. **Decode the graphics containers.** Tiles are 8×8 2bpp, 16 bytes each, two
   bit-planes interleaved per row (row *r*: plane 0 at `2r`, plane 1 at `2r+1`).
   Find the palette format (CGB is BGR555 little-endian words) and the
   compression (many GBC games use an LZSS variant; recognise it from the shape
   of a known graphic's header). A tile viewer you can point at any bank is worth
   more than any amount of staring at hex.
8. **Build the first instrument before the third subsystem.** The moment you
   compare a behaviour twice by eye, stop and script it: deterministic input
   replay, frame-numbered state dumps, and a diff.

Rule of thumb: the first week is *infrastructure*, the second is *subsystems*. If
you are still reading hex by hand at the end of week two, you are doing it wrong.

---

## 3. Your instruments, and what each is for

| Instrument | What it gives you | Minimum capability you need |
|---|---|---|
| Disassembler | code you can read and search | `bank:addr` addresses, labels you can rename, output you can diff after a change |
| Debugger emulator | PC/registers/memory/VRAM at chosen moments | conditional breakpoints on PC ranges and memory writes; RAM search for changing bytes |
| Tracer | the actual path of one behaviour | log `[frame, bank, pc]` and WRAM writes for a window, then histogram |
| State dumper | comparable snapshots | WRAM/VRAM/OAM/palettes/registers at a frame, in a parseable form |
| Input replayer | reproducibility | one recorded input stream that both the emulator and your code consume |
| Differential harness | "who is wrong" | run two implementations on the same inputs and compare state every frame |
| Your notes | memory across sessions | one address per claim, with how it was verified |

Two properties matter more than the choice of tools:

* **Everything must be scriptable and addressable.** If the only way to see a
  frame is to press a key, you cannot bisect.
* **Everything must be reproducible from power-on.** A savestate is fine for
  exploring and fatal for claims: hardware state you do not model will leak into
  your conclusions. Keep one save file you can always recreate and replay from a
  fixed input stream.

---

## 4. Evidence: how not to believe wrong things

The most expensive failure is not a hard problem — it is a **wrong fact that
everything downstream trusts**. Structure the work so wrong facts get caught
cheaply.

### 4.1 The four sources, ranked

1. **ROM bytes.** Absolute, cheap, no interpretation.
2. **A disassembly listing.** High, but produced by a program and a previous
   reader: it encodes guesses about where code starts and what is data.
3. **An execution trace.** Proof of what happens, not of why. Excellent for
   "which routine runs when", weak for "what does this byte mean".
4. **Notes, comments, forum posts, your own summaries.** A map, never a proof.

**If (4) contradicts (1), the byte wins and the note is fixed in the same breath.**
Make that a habit and your notes slowly become true.

### 4.2 The prediction habit

Before running the experiment, write down what you expect:

> *Claim:* the deck's object list is chosen by story flag `$001`.
> *Prediction:* the selector word will look like `$FFFE`/flag+list, and clearing
> that flag in RAM will change the sprite id of the companion standing on deck
> screen (0,0).

Then run it. Two outcomes, both valuable: the prediction holds (you now *know*,
rather than having read), or it fails and you have found where your model is
wrong — which is exactly what you were looking for.

An experiment that cannot fail is not an experiment. "I read the routine and it
looks like it does X" must become "if X, then at frame N the byte at `Y` is `Z`".

### 4.3 The two-of-three rule

For anything you will build on for days, insist on two of three:

* the bytes at the address say it (structure and values);
* the listing says it (the routine that reads them);
* the machine does it (a trace, or a controlled poke changing the behaviour).

One source is a hypothesis, two is a working fact, three is a foundation.

### 4.4 Confidence labels

Tag claims **confirmed** (two sources including execution), **inferred** (one
strong source), **tentative** (naming guess or pattern match). Write the label
next to the claim. Upgrade in place when you find the third source — a note set
whose confidences never change is a note set nobody checks.

---

## 5. The loop, for any subsystem

This is the whole method; everything else is detail.

```
1. Choose ONE behaviour with an observable boundary.
   "Walking across a screen boundary" — not "the field engine".
2. Write down the observable: which bytes/frames change, and when.
3. Find the code and data the behaviour passes through: breakpoint on the
   observable, then read the callers or the table it indexes.
4. Dump the data structurally (pointer table → record size → fields) and let
   invariants reject a wrong decode (§6.2).
5. Implement the smallest thing that reproduces the observable.
6. Measure: replay identical inputs through the real machine and yours,
   compare per frame, and write down the first differing frame.
7. Fix the earliest difference, not the most annoying one.
8. Record the claim, the addresses, the before/after measurement and what the
   fix ruled out. Commit it as one unit.
```

Habits that make the loop fast:

* **Work from the boundary inward.** An edge observable (screen warp, message
  box, damage number, music change) is worth ten internal states you cannot see.
* **One variable per experiment.** Two changes at once and a shifted symptom
  teach you nothing about either.
* **Always chase the earliest divergence.** Later symptoms are usually
  consequences; two implementations first disagree at exactly one frame, and
  everything after it is noise.
* **Write the result before interpreting it.** The number or byte pattern first,
  the explanation second. Interpretation-first is how motivated reasoning gets in.
* **Three attempts, then change level.** Re-read the routine, pick a different
  observable, or question the assumption underneath the approach. Grinding is
  not a method.

---

## 6. Data structures: the part that actually takes weeks

### 6.1 The decoding protocol

For any table:

1. Find the **index space**: what indexes it, and how large the index can get.
2. Find the **pointer table** or the **stride**. If pointers: all in the same
   bank? inside the ROM? monotonic? aligned? One pointer outside the bank means a
   wrong base address or a wrong record size.
3. Infer the **record size** from the spacing between consecutive records, then
   confirm it against the fields: small values look like byte fields, `$C0–$DF`
   pairs look like WRAM pointers, `$00–$3F` words look like counts, and the tail
   of a record is often padding.
4. Decode **one record by hand**, the **whole table with a script**, then check a
   few records against what the game displays (a name, a price, a stat line).
5. Emit the table as generated data (one file per table, never typed by hand) and
   assert a known entry in a unit test.

### 6.2 Invariants: free error detection

Machine-generated data is full of accidental structure. Turn it into tests:

* pointers point inside their own bank and inside the ROM;
* a length byte matches the number of records you found;
* indices stay below the table size (sprite ids, species ids, map ids);
* a name is printable in the game's charset, or ends in the terminator;
* levels, prices and rates are monotonically non-decreasing;
* checksums stored in the data validate (saves, record blocks, graphics headers);
* a mirror table agrees with its original.

When an invariant breaks you do not have a cosmetic bug: you have a wrong decode,
and everything built on it is suspect until it is fixed.

### 6.3 Trust sizes, check meanings

A record's *meaning* can be wrong while its *size* is right, and that is still
useful: sizes survive refactors, and "this record is 0xA5 bytes and the array has
30 entries" is a test you can run forever.

---

## 7. How a frontier model should work a problem

Not "think harder" — think in *structures that catch mistakes*. This is the
discipline that separates a fast guess from an answer you can defend.

### 7.1 Before you touch anything

* **Restate the question** in one sentence, including the observable that would
  settle it. If you cannot, you are about to explore aimlessly.
* **List what you already know and how you know it** (byte / listing / trace /
  note). Anything you cannot source is not knowledge yet.
* **Name the cheapest discriminating experiment.** Not the most thorough one —
  the one that kills the most hypotheses per unit of effort: usually a single
  byte read or one conditional breakpoint.

### 7.2 While working

* **Decompose to one-command steps.** A step you cannot express as a command with
  a small output is too big. Long silent chains of reasoning are where models (and
  humans) drift.
* **Read with a question.** Every file you open answers a specific question; when
  it is answered, stop. Reading more "to be safe" feels productive and
  accumulates contradictions.
* **Prefer structural facts to semantic ones.** "The table at `X` has 30 records
  of `0xA5` bytes" is checkable; "this is the party record" is an interpretation
  that will later be wrong in a subtle way.
* **Keep a ledger.** One line per claim: `claim | evidence | confidence | what
  would falsify it`. When your context is reset, the ledger is your memory; when
  two claims conflict, it shows which one was sourced.
* **Bound your parallelism.** Two or three independent probes at most, each with
  its own written verdict. Wide fan-out produces half-finished threads and no
  decisions.
* **Write results before interpreting.** The first differing frame, the byte
  pattern, the count. Interpretation is a separate step with its own chance to be
  wrong.

### 7.3 When you think you know

1. **What would you see if you were wrong?** If no observation distinguishes the
   two, you do not have a claim.
2. **What is the cheapest test?** Run it, even when it feels unnecessary. A byte
   read costs nothing; a wrong foundation costs days.
3. **Where is this load-bearing?** Anything three subsystems will build on gets
   the third source before you move on.

### 7.4 The failure modes of capable models, and the countermeasures

| Failure | What it looks like | Countermeasure |
|---|---|---|
| Hallucinated address | a confident `$C5xx` with no source | print the bytes at every address you write |
| Motivated reasoning | evidence bent toward the elegant theory | pre-register the prediction; separate observation from explanation |
| Silent generalization | "this table is probably the same format" | check one entry of the new table, always |
| Reading instead of testing | long plausible reading sessions | every third action is an experiment |
| Context drift | forgetting which bank the session is in | restate the one-line question before each step |
| Premature victory | "implemented" reported as "works" | the definition of done (§9) |
| Sunk-cost loop | sixth variation of the same failed fix | three attempts, then change level |

### 7.5 Habits that specifically help a model

* **Batch the cheap checks.** One command printing five addresses plus their
  sanity properties teaches more than five commands printing one line each.
* **Ask for the counterexample.** When a note claims X, look for the record that
  contradicts it. The contradiction is the useful finding.
* **Use invariants as a free reviewer.** A decode that breaks a pointer range or
  a monotonicity rule is wrong however plausible it reads.
* **Write the handoff while it is fresh.** A paragraph of "what I would tell
  myself in the morning" is the highest-value artifact you produce.

---

## 8. Knowing when you are wrong: the error catalogue

Real error classes, with the test that catches each.

| Error | Symptom in practice | The check that catches it |
|---|---|---|
| Wrong bank | data reads as noise; pointers go nowhere | every pointer in a table must land in that table's bank |
| Off-by-one base | first record plausible, the rest garbage | decode the last record too; compare against the index count |
| Wrong record size | field values drift after the first records | pointer spacing must equal size × count |
| Misread terminator | text runs into the next string; menus gain trailing glyphs | find the routine that consumes the terminator instead of guessing from hex |
| Two similar routines | a fix moves the symptom without fixing the cause | breakpoint on the observable; exactly one routine should write it |
| Miscounted RNG draws | divergence appears only in random outcomes, one step off | count draws in your trace against the listing; the first differing random value names the draw |
| Trusted an old note | everything downstream is subtly wrong | re-check the one address you are about to depend on |
| Wrong hardware timing | frames drift, sound desyncs, saves corrupt | compare frame counts at fixed input; count DMA and serial cycles exactly |
| Wrong endianness | 16-bit fields look like garbage with a recognisable low byte | check one known pointer's byte order |
| Wrong edition | 99 % works, a few strings and sprites differ | hash the ROM; diff the editions at bank granularity |

The meta-lesson: **every one of these is caught by a cheap structural check.**
Build the checks into the decoding, not into a debugging session afterwards.

---

## 9. Definition of done

A subsystem is done when all five hold:

1. **Declared**: a note with addresses, structure, and a confidence per claim.
2. **Tested**: a unit test asserts known values (a name, a price, a stat line, a
   generated world's seed).
3. **Compared**: replaying identical inputs through the real machine and your
   code agrees per frame for the behaviour's window — and when it does not, the
   first divergence is written down with its frame number.
4. **Regenerable**: the data comes from a script over the ROM, never typed.
5. **Documented at the boundary**: what the next person needs in order to use it,
   phrased as facts (addresses, formats, order of operations), not as history.

A change that moves a comparison later without closing it is progress and should
be recorded as such; "still diverges at frame N, was N−x" is a fact.

---

## 10. Worked examples (DWM2), as method demonstrations

**A table with a decoder you have to infer.** Field screen data is a stream: a
16-bit length, a marker byte, then `{marker, X, Y}` runs that copy rows from
already-decoded output. How it was pinned down: dump the stream, notice the
recurring `{0xNN, X, Y}` shape, implement the copy rule, then compare the decoded
1,920-byte screen against the emulator's live VRAM buffer *byte for byte*, and
revise the rule until 2,672/2,672 bytes match. Method: invent the simplest rule
that explains the bytes, then let a byte-exact comparison falsify it.

**A text command table that everyone had wrong.** Strings end at one particular
byte; three other bytes that look like terminators actually mean "open the
yes/no window" and "beep off/on". The catch: dump the 32-entry dispatch table,
follow the `$FF` entry to its routine, and read the routine. Method: the dispatch
table is the specification; hex patterns are not.

**A single byte that changes the whole identity of the game.** The two editions
differ at one instruction that writes one story flag; from it follow the player's
sprite set, the companion's sprite set, the deck dialogue branch and the deck
object selector. Method: diff the two ROMs at bank granularity, then read the
*only* code bytes that differ inside an otherwise identical bank — and do not
assume the difference is "content".

**A protocol with no framing.** The link cable is byte-synchronous with no
lengths, checksums or sequence numbers. Method: log every serial byte on both
sides, label which side drives the clock, rebuild the state machine from the
observed alternation, then verify a full session with balanced byte counts and
zero stalls. The listing alone would not have told you which side speaks first in
each state.

---

## 11. Practicalities that bite

* **Space and memory shaped the design.** When data has a strange limit (32
  items, 30 records, 6 slots) that is a ROM constraint to model, not a bug to
  "fix".
* **MBC5**: a bank write takes effect immediately, and the bank register's value
  at boot is not defined by the cartridge — never assume bank 1.
* **Double speed** halves cycle counts while the frame keeps its duration;
  anything timed in cycles (serial, HDMA, audio) must be counted at the current
  speed.
* **Palettes are not RGB.** CGB colors are 15-bit BGR555 and the game's own
  conversion to 24-bit is part of its output; two plausible conversions differ by
  one LSB — invisible to the eye, fatal to a pixel test.
* **OAM priority is subtle**: index order, the attribute priority bit, and the
  per-line sprite limit decide overlaps. A "logical" draw order looks right in
  stills and wrong in motion.
* **Save formats have validity checks**: a wrong checksum silently discards the
  save. Find the magic byte and both checksums before you write save code.
* **Text is per-game, not standard.** Encoding, terminators and printer are the
  game's own; decode them from the ROM.
* **Do not mistake emulator artifacts for game behaviour.** Boot ROMs,
  uninitialised VRAM and timing fuzz are artifacts; compare states at frame
  boundaries with deterministic input.

---

## 12. Key terms, and what to search for each

A compact list of the vocabulary the notes use; the full set with definitions and
sources is in [`GLOSSARY.md`](GLOSSARY.md). The right-hand column is the phrase
that finds accurate material — prefer results from gbdev.io, GitHub repositories
with test ROMs, and pages that quote registers rather than paraphrase them.

| Term | Meaning in one line | Search phrase |
|---|---|---|
| **bank / bank map** | 16 KiB cartridge window at `$4000–$7FFF`, 256 possible banks | `game boy bank switching MBC5` |
| **MBC5** | Mapper: bank low/high at `$2000`/`$3000`, RAM enable `$0A` at `$0000` | `MBC5 registers` |
| **WRAM / HRAM / VRAM / OAM** | Work RAM / high RAM / video RAM / sprite table | `pan docs memory map` |
| **vectors** | Fixed entry addresses: `$0040` VBlank, `$0048` STAT, `$0050` timer, `$0058` serial, `$0060` joypad | `game boy interrupt vectors` |
| **PPU / tile / 2bpp** | Video hardware; 8×8 16-byte tiles, two bit-planes | `game boy tile format` |
| **LZSS** | Compression used for graphics and maps; several incompatible variants | `LZSS game boy decompression` |
| **APU / frame sequencer** | Sound hardware; 512 Hz stepper for envelopes and lengths | `game boy frame sequencer` |
| **serial / SB / SC** | Link-cable shift register and control; byte-synchronous | `game boy serial transfer SC SB` |
| **savestate vs battery save** | Emulator snapshot vs the cartridge's own SRAM file | `savestate battery save difference` |
| **disassembly** | Code rendered as searchable assembly with labels | `mgbdis disassembler` |
| **recursive descent** | Find code by following control flow from entry points | `recursive descent disassembler` |
| **code/data separation** | Deciding which bytes are instructions — the core disassembly problem | `code data separation binary` |
| **symbol file (`.sym`)** | `bank:addr name` lines naming routines and variables | `game boy sym file` |
| **jump table** | Array of code pointers behind a `switch`-like dispatch | `jump table recovery` |
| **coverage trace** | Which addresses executed under a given input | `coverage trace basic block` |
| **far call** | Write a bank register, then call into `$4000–$7FFF` | `game boy far call idiom` |
| **static recompilation** | Translate guest code to host code ahead of time | `static binary translation` |
| **oracle / differential testing** | Reference implementation; run two and compare | `differential testing oracle` |
| **state parity** | Agreement on the game's own variables, frame by frame | `state comparison testing` |
| **clean room** | Reimplementation from observation, without copied code | `clean room design` |
| **TCRF / ROM map** | Unused-content wiki / community data-layout docs | `tcrf`, `data crystal ROM map` |

## 13. The one-page version

1. Identify the image, hash it, and never work on an unhashed ROM.
2. Map the banks before you read any code.
3. Read the VBlank handler and write the frame contract down.
4. Discover RAM by poking one thing and watching which bytes move.
5. Find the text engine; readability is leverage.
6. Decode data structurally, and let invariants reject a wrong decode.
7. Work one observable behaviour at a time; fix the earliest divergence.
8. Two sources for a working fact, three for a foundation.
9. Pre-register predictions; separate observation from explanation.
10. Three failed attempts means change level, not persist.
11. Write it down with addresses before you believe you will remember it.
12. "Implemented" is not "verified": the comparison frame number is the truth.
