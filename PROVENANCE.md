# Provenance: how these notes were made, and how they were checked

A reference is only as good as the evidence behind it. This page states where the
facts come from and what standard they were held to.

## The three artifacts

| Artifact | Role |
|---|---|
| **Retail ROM dump** (Tara's Adventure, 4 MiB, sha256 `fc6809c3…`) | the default source of truth: every table, every byte, every address |
| **Retail ROM dump** (Cobi's Journey, 4 MiB, sha256 `8e38a742…`) | the same claims in the second edition; the two differ in 15 banks, listed in `14-editions.md` |
| **Annotated disassembly of the same engine** ([`JoeyLandy/dwm2decomp`](https://github.com/JoeyLandy/dwm2decomp), MIT) | routine boundaries, names and cross-references — a map, checked against the ROM before use |
| **Running execution** (a cycle-level emulator trace, and/or a static recompilation with a differential harness) | behaviour claims: which routine runs when, what changes at which frame |

Nothing was taken from another decompilation's conclusions without checking the
bytes, and nothing was inferred from "this looks like how game X does it". Routine
names in these notes follow that disassembly's naming (its `src/ram.asm` symbol
table) so a reader can move between the two; where our reading of the behaviour
differs, the note says so rather than silently renaming.

## The standard each claim meets

* **Address-backed.** A fact is stated with a `$BB:AAAA` address or a file offset.
  If a note cannot attach one, it says *unconfirmed* instead of guessing.
* **Sized.** Tables are described by pointer table + stride + record layout, so a
  reader can re-derive them structurally rather than trusting a dump.
* **Two-sourced for anything load-bearing.** Byte dump plus either the listing or
  an observed execution. Claims that rest on one source say so.
* **Errors are kept visible.** Where an earlier reading of the notes was wrong,
  the correction is in the text (the text terminator `$F0` vs the yes/no window
  byte, the breeding table's real bank, the audio driver's real bank) rather than
  silently overwritten — the wrong reading is often the one a reader will
  independently arrive at, so naming it helps.

## What was deliberately not shipped

* **Raw research notes.** The per-topic working notes (`re/notes/…` in the
  citations) contain longer verbatim excerpts, extracted data and dead ends.
  They are provenance, not product; the shipped files are the distilled version.
* **Extracted data.** No tables, text, graphics or audio from the cartridge:
  addresses and formats only. Getting the data requires your own dump.
* **Code.** This repository documents behaviour; it is not a port or a
  recompilation.

## Why the split matters legally

The addresses, formats and algorithms are facts and are not copyrightable. The
game's *content* — its text, artwork, music and data tables — is copyrighted, so
it is not reproduced here. That is also why the guides describe how to extract
data from your own dump instead of shipping it.

## Reproducing a claim

Any claim can be checked with a hex editor, a small Python script and an accurate
emulator. [`HOW-TO.md`](HOW-TO.md) gives the procedure, the invariants that catch
a wrong decode, and the failure modes to expect. If a claim in these notes cannot
be reproduced that way, it is a bug: please report it (see
[`CONTRIBUTING.md`](CONTRIBUTING.md)).
