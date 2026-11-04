# Corrections and contributions

This is a reference document, so the bar for a change is evidence, not opinion.

## Reporting an error

Open an issue containing:

1. **the file and the claim** that is wrong (quote the line);
2. **the evidence** that contradicts it — a file offset with bytes, a routine
   address with the instructions, or a frame number from a trace;
3. **the correct statement**, if you have one.

Example:

> `05-field-maps-objects.md` says the warp table is at file `0x467A6`. The bytes
> at that offset do not look like a 256-word pointer table; the table seems to be
> at `0x467A4` (first non-zero word `$4000` lands on a plausible record). Bytes:
> `a6 67 a4 67 …`

## Sending a change

* One topic per pull request, and state the evidence in the description.
* Keep the style: `$BB:AAAA` addresses, file offsets for data, *unconfirmed* for
  anything inferred, tables over prose.
* Do not add: ROM data, extracted assets, save files, or code from the game.
  Addresses and formats only.
* If you correct a claim, say why the old one was wrong — that sentence is often
  the most useful part of the change.
* Run `python3 tools/check.py` before you open the pull request.

## Style notes

* Prefer a table to a paragraph when the content is enumerable.
* Name routines as the game's own symbols do, and give the address.
* When two readings are possible, say which you chose and what would decide it.

## License of contributions

By contributing you agree that the text is licensed under CC BY 4.0, as described
in [`LICENSE`](LICENSE).
