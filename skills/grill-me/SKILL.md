---
name: grill-me
description: Interview the user before building something new so the build matches what they want - ask only the questions whose answers change the work, in short batches with a recommended answer for each, then write the answers down as a spec. Use when the user says "grill me", "ask me questions first" or "interview me", and before starting a feature, skill, tool or document whose request is a rough idea or a brain-dump. Not for small or fully specified tasks, bug fixes with a clear repro, or work whose plan file already answers these questions.
---

# Grill me

Ten wrong assumptions cost more than ten questions, but ten questions the user can't answer cost a session. Ask few,
ask well, and leave a written spec behind so nobody asks again.

## 1. Read before asking

Read what already exists: the request, the project's plan or design files, `CLAUDE.md`/`AGENTS.md`, related code.
Every question those already answer is one you don't ask. If the request is a messy brain-dump, restate it first as
3-6 bullet points (goal, must-haves, constraints, out of scope) and ask the user to correct them. That restating step
is the useful part of a "prompt rewriter" and costs one message.

## 2. Pick the questions

Keep a question only if a different answer would change what you build, how long it takes, or what can't be undone.
Rank by that, and drop the rest. Good targets:

- **Goal and done:** who or what is this for, and how will the user know it works?
- **Scope edges:** what is explicitly out? What is the smallest version worth having?
- **Existing pieces:** does something similar exist that this must match, reuse or replace?
- **Constraints:** platform, performance, compatibility, things that must not change.
- **Hard to undo:** names, data formats, public interfaces, anything that ships.
- **Conflicts:** places where the request contradicts the docs or itself. Quote both sides.

## 3. Ask in batches

- 3-5 questions per message, most important first. Usually 1-3 batches are enough; stop at about 15 questions total.
- Each question answerable in a word or a line, with your recommended answer marked, so "go with your picks" works.
- Use the client's multiple-choice question tool when there is one.
- After each batch, say which questions the answers settled, and only ask a follow-up if an answer opened a new fork.
- If the user says "just build it", stop asking, use your recommended answers, and list them as assumptions.

## 4. Write the spec

Write the answers where the project keeps plans (for example `plans/<feature>.md`), or as a short block in the reply
if there is nowhere to put them:

```markdown
## <feature>: spec (agreed YYYY-MM-DD)
Goal: ...
Done when: ...
In scope: ...
Out of scope: ...
Decisions: <question> -> <answer> (user | assumed)
Open: <anything still unanswered, and the default being used>
```

Then start the build from that spec, not from the conversation.
