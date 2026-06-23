import { AppShell } from "../components/AppShell";
import { ClickableCard } from "../components/ClickableCard";
import { EmptyState } from "../components/EmptyState";
import { MetricTile } from "../components/MetricTile";
import { QualityGateCard } from "../components/QualityGateCard";
import { SectionHeader } from "../components/SectionHeader";
import { SkeletonBlock } from "../components/SkeletonBlock";

const resumeItems = [
  {
    title: "Trello board sync",
    meta: "adapter · boards/list/cards · local config",
    status: "READY" as const,
    action: "Открыть",
  },
  {
    title: "Google Calendar reminders",
    meta: "calendar · OAuth ready · event blocks",
    status: "READY" as const,
    action: "Открыть",
  },
  {
    title: "Inbox review",
    meta: "triage · open items · next command",
    status: "IN PROGRESS" as const,
    action: "Продолжить",
  },
];

const todayItems = [
  {
    title: "Создать реальные задачи",
    meta: "Trello · add cards from command line",
    status: "READY" as const,
  },
  {
    title: "Проверить календарные блоки",
    meta: "Google Calendar · time blocks and reminders",
    status: "READY" as const,
  },
];

export function HubMLPreview() {
  return (
    <AppShell>
      <section className="hub-hero">
        <div className="hub-brand">
          <div className="hub-brand-kicker">
            <span className="hub-accent-marker" />
            Task Command Center · local workstation
          </div>
          <h1>Task Command Center</h1>
          <p>Консоль управления задачами, Trello и Google Calendar.</p>
        </div>
        <QualityGateCard percent={100} label="SYSTEM GATE" status="READY" caption="Trello + Google Calendar connected" />
      </section>

      <section className="hub-section">
        <SectionHeader
          eyebrow="RESUME"
          title="Продолжить"
          description="Основные рабочие направления без отдельных широких кнопок."
        />
        <div className="hub-card-list">
          {resumeItems.map((item) => (
            <ClickableCard
              action={item.action}
              href="#"
              key={item.title}
              meta={item.meta}
              status={item.status}
              title={item.title}
            />
          ))}
        </div>
      </section>

      <section className="hub-section">
        <SectionHeader eyebrow="TODAY" title="План на сегодня" description="Два ближайших шага для реальной работы." />
        <div className="hub-card-list">
          {todayItems.map((item) => (
            <ClickableCard action="Открыть" href="#" key={item.title} meta={item.meta} status={item.status} title={item.title} />
          ))}
        </div>
      </section>

      <section className="hub-section">
        <SectionHeader eyebrow="SYSTEM" title="Статус" description="Небольшой набор primitives для проверки ритма страницы." />
        <div className="hub-metric-grid">
          <MetricTile label="Trello" value="ready" meta="board sync available" />
          <MetricTile label="Calendar" value="ready" meta="OAuth token present locally" />
          <MetricTile label="CLI checks" value="100" total="100" progress={100} />
        </div>
      </section>

      <section className="hub-section">
        <SectionHeader eyebrow="LOADING" title="Skeleton & empty" description="Вспомогательные состояния для будущих реальных данных." />
        <div className="hub-metric-grid">
          <div className="hub-metric-tile">
            <SkeletonBlock width="62%" height="13px" />
            <div style={{ height: 12 }} />
            <SkeletonBlock width="90%" height="11px" />
            <div style={{ height: 10 }} />
            <SkeletonBlock width="76%" height="11px" />
          </div>
          <EmptyState title="Нет новых задач" body="Когда появится входящий backlog, он будет показан здесь." action="создать задачу" />
        </div>
      </section>
    </AppShell>
  );
}
