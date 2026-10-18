# Bug reports

Each report comes from a user. Some reports have more than one root cause, and some root causes
show up in more than one report.

---

**#1: "It only works once"**
> I ran `python-cli add 5 coffee` and it worked. Then I ran `python-cli add 10 lunch` and now
> every command crashes with a big error.

**#2: "Can't list anything"**
> I deleted my data file and started fresh. `add 12.50 lunch` prints an error about a
> "format code", and `summary` blows up too.

**#3: "My March expenses are missing"**
> I imported `sample.csv`, which is all March 2026. `list --month 2026-03` shows almost
> nothing, and some entries have weird dates. One row wouldn't import at all.

**#4: "Delete removed the wrong thing"**
> `list` showed my lunch as #1. I ran `delete 1` and it deleted my coffee (#2) instead.

**#5: "Clear doesn't clear"**
> I had 4 coffee expenses and ran `clear --category coffee`. It said it removed 2, and 2 are
> still there.

**#6: "Everything is tagged with everything"**
> After importing a CSV, every expense shows `[treat, essential, essential, treat]`, even my
> sandwich.

**#7: "Summary is upside down and the percentages are all 0"**
> The biggest category should come first. Every percent shows `0.0%`, except sometimes one
> shows `100.0%`.

**#8: "Our script thinks errors succeeded"**
> Our shell script runs `python-cli delete 99 || echo failed`. It prints `error: ...` but never
> prints `failed`, because `$?` is 0.
