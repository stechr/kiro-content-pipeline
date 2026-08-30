---
description: "Why I stopped optimizing for clever code and started optimizing for the person who reads it next."
date: 2026-05-10
tags:
  - engineering
  - craft
---

# I Stopped Writing Clever Code

For a long time I measured a good day by how much I could fold into one line. A dense list comprehension. A regex that did the work of ten `if` statements. It felt like skill.

Then I came back to my own code six months later and could not read it.

## The person who reads it next is usually you

Here is the thing nobody tells you early on: the reader of your code is almost never a stranger. It is you, in three months, with none of the context you have today. Every clever shortcut is a loan against that future person's time, and the interest rate is high.

So now I ask one question before I commit: would I understand this cold?

If the answer is no, I unfold it. Two more lines. A named variable instead of a magic number. A comment that says *why*, never *what*.

## Boring code ages well

Clever code is fragile because it depends on the author being present. Boring code does not. It sits there, obvious, and keeps working while you go do something more interesting.

I would rather ship the boring version and sleep well.

What is one piece of "clever" code you wish your past self had written plainly?

## Sources

- [1] Martin Fowler, "Refactoring" — https://martinfowler.com/books/refactoring.html
