---
title: Python Basics
track: Python
level: beginner
status: ready
tags: [python, basics, list, dict, function, loop]
prerequisites: []
related_tasks: [python_basics_user_events__manual_01]
related_practice: [python_basics_user_event_structures]
related_projects: []
---

# Python Basics

## Why it matters

Python basics are the first working layer for Hub_ML practice. Before pandas,
models, notebooks, or project reports, the learner needs to read small records,
keep values in variables, move through a list, build a dict, and put repeated
logic into a function. This is not abstract syntax trivia. It is the same shape
that appears later in mentor tasks: take raw records, summarize them, check the
result, and explain why the code is stable.

## Core idea

Think of Python as a small toolbox. A `list` keeps ordered items. A `dict`
connects a key with a value. A `for` loop applies the same action to each item.
An `if` chooses the branch for the current item. A `function` gives the whole
operation a name, input, and return value. In beginner data work, this usually
means transforming a list of event dictionaries into a clearer summary.

## Minimal runnable example

```python
records = [
    {"user_id": 1, "event_type": "view", "price": 0},
    {"user_id": 1, "event_type": "purchase", "price": 30},
    {"user_id": 2, "event_type": "purchase", "price": 20},
]

def summarize_user_events(records):
    summary = {}
    for row in records:
        user_id = row["user_id"]
        if user_id not in summary:
            summary[user_id] = {"events": 0, "purchases": 0, "revenue": 0}
        summary[user_id]["events"] += 1
        if row["event_type"] == "purchase":
            summary[user_id]["purchases"] += 1
            summary[user_id]["revenue"] += row["price"]
    return summary

result = summarize_user_events(records)
assert result[1] == {"events": 2, "purchases": 1, "revenue": 30}
assert result[2]["revenue"] == 20
```

## Connection to Hub_ML

In Hub_ML this note connects to the practice card
`python_basics_user_event_structures` and the mentor task
`python_basics_user_events__manual_01`. Both are intentionally small: no pandas,
no machine learning, and no hidden framework. The goal is to build the mental
model for records, loops, conditionals, and reusable functions before the same
idea appears in Data Lab projects and notebook experiments.

## Common mistakes

- Printing a result instead of returning it from the function.
- Mutating the input records when only a summary is needed.
- Recreating the user row on every loop iteration and losing earlier counts.
- Mixing string and numeric values, for example adding `"30"` instead of `30`.
- Writing code that works for one user but fails when a second user appears.
- Forgetting a test for an empty list or a user with no purchases.

## Self-check

1. Can you explain where the example uses a list, dict, loop, condition, and function?
2. What does the function return for an empty `records` list?
3. Why is `user_id not in summary` checked before counters are incremented?
4. Which part would change if the revenue field were named `order_sum`?
5. Can you add one assert for a user with two purchases?

## Portfolio output

Create a tiny `python_basics_summary.py` file with one function, three asserts,
and a short README paragraph explaining the input shape, output shape, and edge
cases. This is not a portfolio centerpiece, but it is useful evidence that the
foundation is tested and readable.

## Sources

- Python official tutorial: https://docs.python.org/3/tutorial/
