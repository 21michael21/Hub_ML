---
title: "ML Take-home: Preference Model"
section: ML
difficulty: hard
est_time: "3-5 ч"
status: draft
links:
  - "https://www.preferencemodel.com/"
  - "https://it.krasavchik.club/docs/ml-ds/homework/preference_model_vacancy.pdf"
  - "https://it.krasavchik.club/docs/ml-ds/homework/preference_model_task.pdf"
  - "https://arxiv.org/abs/2305.18290"
---

## Что сделать

> Черновик: текста домашнего задания пока нет. Ссылки на vacancy/task PDF вернули страницу входа через Telegram, а не PDF. Эту карточку нельзя считать готовой практикой, пока сюда не добавлен реальный текст задания.

Это карточка для разбора ML take-home от Preference Model. Компания публично описывает себя как команду, которая строит automated ML research engineering и RL environments для обучения моделей решать реальные ML-research задачи. Ссылки на vacancy/task PDF сейчас требуют вход через Telegram, поэтому точный текст задания нужно открыть вручную через клуб и положить рядом как исходник или скопировать в Portfolio output.

Рабочий план:

1. Прочитай vacancy PDF и выпиши, что именно оценивают: ML research, RL environments, reward functions, infrastructure, experiments, engineering quality.
2. Прочитай task PDF и выдели: входные данные, ожидаемый артефакт, ограничения по времени, критерии оценки, формат сдачи.
3. Сформулируй baseline: самая простая рабочая версия решения, которую можно объяснить за 2 минуты.
4. Сделай solution plan: данные -> метрики -> модель/алгоритм -> эксперименты -> риски -> что бы улучшил при большем времени.
5. Если в задании есть код или датасет, решай в Notebook, а сюда сохрани итоговый README и ссылку на артефакт.

Минимальный шаблон решения лежит в `content/source/preference_model/preference_model_solution.md`.

## Как себя проверить

- Ты можешь одной фразой сказать, какую бизнес/исследовательскую задачу решает take-home.
- В решении есть baseline, а не только сложная идея.
- Метрика соответствует цели задания, а не выбрана потому что "обычно так делают".
- Есть честный раздел risks/limitations: где решение может сломаться.
- README выглядит как работа ML engineer: reproducibility, команды запуска, assumptions, next steps.

## Что положить в портфолио

Папку `preference_model_take_home/`: README с постановкой задачи, solution plan, experiments log, финальный код/notebook, короткий postmortem "что улучшить за следующий день".
