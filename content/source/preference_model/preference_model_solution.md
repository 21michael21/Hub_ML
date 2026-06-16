# Preference Model take-home - solution scaffold

> Status: source PDFs require Telegram login on `it.krasavchik.club`, so this is a solution scaffold based on the public company context. Replace the "Task summary" block after the real PDF text is available.

## Company context

Preference Model builds automated ML research engineering: reinforcement-learning environments, robust reward functions, and tasks that reflect real-world ML research complexity.

## Task summary

Fill this after reading `preference_model_task.pdf`.

- Objective:
- Inputs:
- Expected output:
- Constraints:
- Evaluation criteria:
- Submission format:

## Proposed solution structure

### 1. Clarify objective

Restate the task as an ML objective and an engineering deliverable. If the task is ambiguous, list assumptions explicitly.

### 2. Baseline

Build the simplest correct baseline first:

- deterministic preprocessing;
- simple metric;
- small model or rule-based reference;
- reproducible script/notebook;
- clear failure cases.

### 3. Stronger approach

Depending on the actual task:

- If it is preference modeling: start with Bradley-Terry / pairwise ranking loss, then compare with DPO-style objective if language-model outputs are involved.
- If it is environment/reward design: define state, action, reward, termination, invalid actions, and evaluation rollouts.
- If it is ML experiment automation: define task generator, scoring function, hidden tests, and robustness checks.

### 4. Evaluation

Report at least:

- primary metric;
- baseline comparison;
- ablation or sanity check;
- error analysis;
- runtime and reproducibility notes.

### 5. Risks and limitations

- reward hacking or metric mismatch;
- data leakage;
- overfitting to visible tests;
- non-deterministic evaluation;
- poor handling of edge cases;
- lack of monitoring if deployed.

## README template

```markdown
# Preference Model take-home

## Problem

## Assumptions

## Approach

## How to run

## Results

## Error analysis

## What I would improve with more time
```

## Done criteria

- A reviewer can run the solution from scratch.
- The baseline and final approach are both explained.
- The metric is tied to the task goal.
- Limitations are honest and concrete.
- The final answer is concise enough for a hiring team to scan quickly.
