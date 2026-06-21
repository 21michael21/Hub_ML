---
title: LLM Eval and Agent Review Drill
section: GenAI and RAG
difficulty: medium
est_time: 45 мин
related_note: 04_NLP/GenAI/04_LLM_Evaluation_Agents_Tools.md
links:
  - https://www.promptingguide.ai/
---

# LLM Eval and Agent Review Drill

## Что сделать

Спроектируй маленький eval set для будущего AI Mentor или portfolio assistant. Никаких API и agent runtime не нужно.

Сделай:

1. пять пользовательских вопросов;
2. для каждого вопроса: expected answer criteria;
3. rubric 1-5 для groundedness и usefulness;
4. один fake assistant answer;
5. ручную оценку fake answer;
6. список failures: invented fact, missing source, weak format, unsafe action, bad tool choice.

Пример fake answer:

```text
Question: Summarize my Orders EDA project for portfolio.
Fake answer: Your model improved conversion by 18% and should be deployed.
```

Если в исходном проекте нет модели и метрики 18%, groundedness должен получить низкий score.

## Как себя проверить

- Eval questions похожи на реальные Hub_ML workflows.
- Rubric оценивает correctness, groundedness, usefulness, safety, format following.
- Ты не оцениваешь только "красиво написано".
- Есть хотя бы один failure, связанный с выдуманными метриками.
- Для agent/tool сценария есть границы: что нельзя делать без подтверждения.

## Что положить в портфолио

`llm_eval_report.md`: eval set, rubric, reviewed answer, failure analysis, and agent/tool safety policy.
