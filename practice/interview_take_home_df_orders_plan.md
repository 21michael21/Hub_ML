---
title: "ML Take-home: Orders Analysis Submission Plan"
section: "Interview Prep"
difficulty: medium
est_time: "60 мин"
related_note: "05_IT_Resources/ML_Take_Home_Assignment_Guide.md"
dataset: "df_orders.csv"
links:
  - "https://huyenchip.com/ml-interviews-book/"
  - "https://book.the-turing-way.org/reproducible-research/reproducible-research/"
  - "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes"
---

# ML Take-home: Orders Analysis Submission Plan

## Что сделать

Смоделируй маленькое ML/DS take-home assignment на `df_orders.csv` или `df_events.csv`. Не пиши фейковое полное решение и не придумывай результаты. Цель — подготовить структуру работы, которую можно честно заполнить после анализа.

Сценарий: компания просит быстро разобраться в заказах или событиях и подготовить воспроизводимый mini report. Для сравнения открой существующую карточку `ML Take-home: Preference Model`: она показывает, как выглядит внешний take-home prompt, но здесь ты делаешь только честный submission plan без фейкового решения.

Сделай:

1. Напиши problem statement: какую бизнес- или аналитическую задачу решаешь.
2. Определи deliverables: README, notebook/report, 1-2 charts/tables, limitations, next steps.
3. Составь timebox plan на 4-5 часов.
4. Выпиши EDA-checklist: shape, columns, missing values, duplicates, suspicious values, basic metrics.
5. Опиши baseline или простой аналитический метод.
6. Определи evaluation checklist: какие метрики или проверки покажут, что вывод полезен.
7. Напиши README outline.
8. Напиши final submission checklist: что проверить перед отправкой.

## Как себя проверить

- В problem statement понятно, кому полезен результат.
- README outline содержит запуск, данные, подход, результаты, limitations и next steps.
- Timebox plan реалистичен: не обещает production system за вечер.
- Evaluation checklist не содержит фейковых метрик.
- Есть явный пункт про reproducibility: команды запуска, зависимости, пути к данным.
- Есть пункт "что не включать": raw private data, секреты, большие файлы, неподтверждённые claims.
- В limitations есть минимум 3 честных ограничения анализа.

## Что положить в портфолио

Шаблон `take_home_submission_plan.md`: problem statement, deliverables, timebox, EDA checklist, README outline, evaluation checklist, limitations и next steps. После реального анализа можно дополнить этот шаблон графиками, таблицами и проверенными выводами.
