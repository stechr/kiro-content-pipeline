---
description: "The five-minute checklist I run before shipping any script, and why the boring items catch the worst bugs."
date: 2026-05-24
tags:
  - engineering
  - practices
---

# The Checklist I Run Before Shipping a Script

I have shipped enough small scripts to know that the small ones bite hardest. Nobody reviews a 40-line helper. It goes straight to production, and three weeks later it quietly deletes the wrong folder.

So I built a checklist. It takes five minutes. It has saved me more than five minutes many times over.

## What is on it

- Does it fail loudly? A script that swallows errors is worse than no script.
- What happens on the second run? If running it twice breaks something, I have a bug, not a tool.
- Where does it write? I trace every path it touches before I trust it near real data.
- Would a stranger know how to run it? If the answer needs me in the room, it is not done.

None of these are clever. That is the point. The clever failures are rare. The boring ones happen every week.

## Checklists are not a lack of skill

Early on I thought a checklist meant I did not trust myself. Now I see it the other way: it means I trust the process more than my mood on a given afternoon.

Pilots use them. Surgeons use them. My scripts are less important than either, which is exactly why I cannot afford to wing it.

What is the one item you would add to your own pre-ship checklist?

## Sources

- [1] Atul Gawande, "The Checklist Manifesto" — https://atulgawande.com/book/the-checklist-manifesto/
