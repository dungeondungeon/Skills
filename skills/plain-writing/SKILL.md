---
name: plain-writing
description: Rewrite or check prose so it reads like a person wrote it and is easy to follow - no em dashes, no stock AI phrases, short sentences, active voice - with a script that flags what is left. Use for text that leaves the chat - store pages, patch notes, READMEs, posts, emails, docs - when the user says "humanize", "make it sound less like AI", "plain English", "simplify" or "STE", and on your own drafts of such text before handing them over. Not for code, code comments, legal text, or fiction and in-game dialogue written in a character's voice.
---

# Plain writing

Two jobs in one skill: sound human (the "humanizer" job) and be easy to read (a light version of Simplified Technical
English, ASD-STE100). `check.py` next to this file does the counting; you do the rewriting. It uses only the standard
library.

```bash
python ~/.claude/skills/plain-writing/check.py <file>          # or pipe text in: ... | python check.py -
python ~/.claude/skills/plain-writing/check.py --ste <file>    # stricter: STE sentence and paragraph limits
```

It prints each problem with its line number and exits 1 if any are found.

## How to rewrite

1. Run the check on the draft first, so you fix what it finds instead of guessing.
2. Fix in this order, because later fixes depend on earlier ones:
   - **Cut** sentences that say nothing: openers ("Great question"), summaries of what you just said, closing offers.
   - **Replace** stock AI words with the plain word the sentence means ("use" not "leverage", "full" not
     "comprehensive"). If no plain word fits, the sentence was probably empty: cut it.
   - **Split** long sentences. One idea per sentence. Turn an em dash into a full stop, a comma or brackets.
   - **Make it active**: say who does what ("The script deletes the file", not "The file is deleted").
   - **Vary rhythm**: avoid three items in every list and the same sentence length in a row.
3. Keep the meaning, every fact and number, and the author's own voice and slang. Don't add claims to make it flow.
4. Run the check again. A remaining flag is fine when the word is the right one (a quoted title, a technical term);
   say which flags you kept and why.

## STE mode (`--ste`)

For instructions, procedures and manuals. Limits from ASD-STE100: procedural sentences up to 20 words, descriptive
up to 25, paragraphs up to 6 sentences, one instruction per sentence, imperative verbs for steps. This is a light
version: it does not check the STE approved dictionary, so don't call the result STE-compliant.

## What the check does not catch

Tone, hedging that is actually needed, and wrong facts. Read the result once as the reader would before sending.
The word list is in `check.py` (`AI_WORDS`, `AI_PHRASES`); add to it when a giveaway slips through, and say so.
