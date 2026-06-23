import { useState } from "react";
import { AppShell } from "../components/AppShell";
import { ClickableCard } from "../components/ClickableCard";
import { EmptyState } from "../components/EmptyState";
import { MetricTile } from "../components/MetricTile";
import { QualityGateCard } from "../components/QualityGateCard";
import { SectionHeader } from "../components/SectionHeader";
import { SkeletonBlock } from "../components/SkeletonBlock";

const resumeCards = [
  {
    title: "Inbox Review",
    meta: "Trello · входящие карточки · next triage",
    status: "IN PROGRESS" as const,
    action: "Открыть",
  },
  {
    title: "Today Plan",
    meta: "локальный план · рабочий день · calendar blocks",
    status: "READY" as const,
    action: "Открыть",
  },
  {
    title: "Calendar Blocks",
    meta: "Google Calendar · фокус-блоки · reminders",
    status: "READY" as const,
    action: "Открыть",
  },
];

const inProgressCards = [
  {
    title: "Подготовить Trello inbox к ревью",
    meta: "project: Task Command · list: Inbox · due today",
    status: "P1" as const,
    action: "Открыть",
  },
  {
    title: "Сверить calendar blocks с планом дня",
    meta: "project: Calendar hygiene · 2 блока требуют проверки",
    status: "P2" as const,
    action: "Открыть",
  },
  {
    title: "Обновить команды из examples/tasks.md",
    meta: "project: CLI docs · локальная задача",
    status: "P3" as const,
    action: "Открыть",
  },
];

function DashboardSkeleton() {
  return (
    <div className="hub-card-list hub-card-list-loading">
      {[0, 1, 2].map((item) => (
        <div className="hub-clickable-card hub-loading-card" key={item}>
          <span className="hub-clickable-body">
            <SkeletonBlock width="62%" height="13px" />
            <SkeletonBlock width="42%" height="11px" />
          </span>
          <SkeletonBlock width="54px" height="11px" />
        </div>
      ))}
    </div>
  );
}

export function Dashboard() {
  const [isReloading, setIsReloading] = useState(false);

  function handleReload() {
    setIsReloading(true);
    window.setTimeout(() => setIsReloading(false), 900);
  }

  return (
    <AppShell
      breadcrumb={["Task Command", "Dashboard"]}
      commandLabel="⌘K command palette"
      isReloading={isReloading}
      onReload={handleReload}
      statusLeft={["local · online", "trello connected", "calendar connected"]}
      statusRight={["main", "⌘K"]}
    >
      <section className="hub-hero hub-anim-header">
        <div className="hub-brand">
          <div className="hub-brand-kicker">
            <span className="hub-accent-marker" />
            local · online
          </div>
          <h1>Task Command Center</h1>
          <p>Trello + Google Calendar local workstation</p>
        </div>
        <QualityGateCard
          caption="Trello connected · Google Calendar connected · Mock mode OFF"
          details={["Trello connected", "Google Calendar connected", "Mock mode OFF"]}
          label="SYSTEM GATE"
          percent={100}
          status="READY"
        />
      </section>

      <section className="hub-section hub-anim-hero">
        <SectionHeader eyebrow="RESUME" title="Продолжить" description="Три быстрых входа в рабочий контур." />
        <div className="hub-card-list">
          {resumeCards.map((card, index) => (
            <ClickableCard
              action={card.action}
              href="#"
              key={card.title}
              meta={card.meta}
              status={card.status}
              title={card.title}
            >
              <span className={`hub-card-delay hub-card-delay-${index + 1}`} />
            </ClickableCard>
          ))}
        </div>
      </section>

      <section className="hub-section hub-anim-section-1">
        <SectionHeader eyebrow="TODAY" title="План на сегодня" description="Web UI пока не читает Trello/Calendar напрямую." />
        {isReloading ? (
          <DashboardSkeleton />
        ) : (
          <EmptyState
            action="подключить API слой"
            body="Реальные Today cards появятся после безопасного backend/API слоя. Секреты не попадают в browser bundle."
            title="Нет загруженных Today cards"
          />
        )}
      </section>

      <section className="hub-section hub-anim-section-2">
        <SectionHeader eyebrow="IN PROGRESS" title="В работе" description="Ограниченный список 2-3 задач с priority chips." />
        {isReloading ? (
          <DashboardSkeleton />
        ) : (
          <div className="hub-card-list">
            {inProgressCards.map((card, index) => (
              <ClickableCard
                action={card.action}
                fail={card.status === "P1"}
                href="#"
                key={card.title}
                meta={card.meta}
                status={card.status}
                title={card.title}
              >
                <span className={`hub-card-delay hub-card-delay-${index + 1}`} />
              </ClickableCard>
            ))}
          </div>
        )}
      </section>

      <section className="hub-section hub-anim-section-3">
        <SectionHeader eyebrow="CONNECTIONS" title="Состояние" description="Локальная web-оболочка без доступа к credentials." />
        <div className="hub-metric-grid">
          <MetricTile label="Trello" value="ready" meta="connected via CLI config" />
          <MetricTile label="Calendar" value="ready" meta="OAuth stays local" />
          <MetricTile label="Mock mode" value="off" meta="production commands preserved" />
        </div>
      </section>
    </AppShell>
  );
}
