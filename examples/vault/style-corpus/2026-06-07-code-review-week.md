---
description: "A week of doing nothing but code review taught me that the best comments ask questions instead of giving orders."
date: 2026-06-07
tags:
  - engineering
  - collaboration
---

# A Week of Only Code Review

My team ran an experiment. For one week I wrote no code. I only reviewed it. By Friday I had learned more about how we work than in the previous month of shipping.

## Orders shut people down; questions open them up

The first two days my comments were instructions. "Rename this." "Extract this function." They were correct and they landed flat. People made the change and moved on, and nothing about the next pull request improved.

So I switched to questions. "What happens if this list is empty?" "Is there a reason this runs inside the loop?"

The difference was immediate. A question hands the problem back to the author with their context intact. Half the time they had already thought about it and I learned something. The other half they had not, and they fixed it themselves and remembered it.

## Review is teaching, not gatekeeping

I used to treat review as a gate: does this pass or not. That framing makes every comment a verdict. Teaching is a better frame. A verdict ends a conversation; a good question starts one.

The code got better that week. The reviews got shorter over time, which is the real signal.

When did a review comment actually change how you write code?

## Sources

- [1] Google Engineering Practices, "How to do a code review" — https://google.github.io/eng-practices/review/reviewer/
