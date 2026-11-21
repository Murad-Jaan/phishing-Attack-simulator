import type { Metadata } from 'next';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Flag,
  GraduationCap,
  ShieldCheck,
} from 'lucide-react';

import { Card } from '@/components/ui/card';
import { buttonVariants } from '@/components/ui/button';
import { en } from '@/content/en';
import {
  fetchAwareness,
  type AwarenessContent,
  type AwarenessRedFlag,
} from '@/lib/api/awareness';

export const metadata: Metadata = {
  title: en.awareness.title,
  description: en.awareness.description,
};

const FALLBACK_FLAGS: AwarenessRedFlag[] = [
  {
    label: en.awareness.fallbackRedFlagOne,
    explanation: en.awareness.fallbackRedFlagOneBody,
  },
  {
    label: en.awareness.fallbackRedFlagTwo,
    explanation: en.awareness.fallbackRedFlagTwoBody,
  },
  {
    label: en.awareness.fallbackRedFlagThree,
    explanation: en.awareness.fallbackRedFlagThreeBody,
  },
];

const TIPS = [
  {
    title: en.awareness.tipOneTitle,
    body: en.awareness.tipOneBody,
  },
  {
    title: en.awareness.tipTwoTitle,
    body: en.awareness.tipTwoBody,
  },
  {
    title: en.awareness.tipThreeTitle,
    body: en.awareness.tipThreeBody,
  },
];

async function loadAwareness(token: string): Promise<AwarenessContent> {
  try {
    const content = await fetchAwareness(token);
    return {
      simulation: content.simulation,
      red_flags:
        content.red_flags.length > 0 ? content.red_flags : FALLBACK_FLAGS,
    };
  } catch {
    return { simulation: true, red_flags: FALLBACK_FLAGS };
  }
}

export default async function AwarenessPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const content = await loadAwareness(token);

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-4">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-tint text-primary-strong"
            aria-hidden="true"
          >
            <ShieldCheck className="h-5 w-5" />
          </span>
          <span className="text-sm font-semibold text-foreground">
            {en.app.name}
          </span>
        </div>
      </header>

      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto max-w-3xl px-4 py-10 sm:py-14"
      >
        <span className="awareness-enter awareness-delay-1 inline-flex items-center gap-2 rounded-full border border-success-tint-border bg-success-tint px-3 py-1 text-xs font-semibold text-success">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          {en.awareness.badge}
        </span>

        <h1 className="awareness-enter awareness-delay-2 mt-5 text-3xl font-bold leading-10 tracking-tight text-foreground sm:text-4xl sm:leading-[48px]">
          {en.awareness.title}
        </h1>
        <p className="awareness-enter awareness-delay-3 mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
          {en.awareness.description}
        </p>

        <div className="awareness-enter awareness-delay-4 mt-8 flex flex-wrap items-center gap-3">
          <a
            href={`/learn/${encodeURIComponent(token)}/quiz`}
            className={buttonVariants({ size: 'lg' })}
            data-testid="quiz-cta"
          >
            <GraduationCap className="h-5 w-5" aria-hidden="true" />
            {en.awareness.quizCta}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </a>
          <a
            href="#training-tips"
            className={buttonVariants({ variant: 'secondary', size: 'lg' })}
            data-testid="start-training"
          >
            {en.awareness.startTraining}
          </a>
          <a
            href="mailto:security@example.test"
            className={buttonVariants({ variant: 'outline', size: 'lg' })}
            data-testid="report-link"
          >
            <Flag className="h-5 w-5" aria-hidden="true" />
            {en.awareness.reportLink}
          </a>
        </div>

        <Card className="awareness-enter awareness-delay-5 mt-10">
          <h2 className="text-xl font-semibold leading-7 text-foreground">
            {en.awareness.redFlagsTitle}
          </h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {en.awareness.redFlagsHelp}
          </p>
          <ul className="mt-5 space-y-4">
            {content.red_flags.map((flag) => (
              <li key={flag.label} className="flex gap-3">
                <span
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-danger-tint text-danger-strong"
                  aria-hidden="true"
                >
                  <AlertTriangle className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-foreground">
                    {flag.label}
                  </span>
                  <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                    {flag.explanation}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <section
          id="training-tips"
          aria-labelledby="training-tips-title"
          className="awareness-enter awareness-delay-6 mt-10 scroll-mt-6"
        >
          <h2
            id="training-tips-title"
            className="text-xl font-semibold leading-7 text-foreground"
          >
            {en.awareness.tipsTitle}
          </h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {en.awareness.tipsHelp}
          </p>
          <ol className="mt-5 space-y-4">
            {TIPS.map((tip, index) => (
              <li
                key={tip.title}
                className="flex gap-4 rounded-2xl border border-border bg-surface p-5"
              >
                <span
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-tint text-sm font-bold text-primary-strong"
                  aria-hidden="true"
                >
                  {index + 1}
                </span>
                <span className="min-w-0">
                  <span className="block text-base font-semibold text-foreground">
                    {tip.title}
                  </span>
                  <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                    {tip.body}
                  </span>
                </span>
              </li>
            ))}
          </ol>

          <div className="mt-6 rounded-2xl border border-border bg-surface-muted p-5">
            <p className="text-sm font-semibold text-foreground">
              {en.awareness.trainingDoneTitle}
            </p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {en.awareness.trainingDoneBody}
            </p>
          </div>
        </section>

        <Card className="awareness-enter awareness-delay-7 mt-10">
          <h2 className="text-lg font-semibold leading-7 text-foreground">
            {en.awareness.reportTitle}
          </h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {en.awareness.reportBody}
          </p>
          <p className="mt-4 text-sm font-medium text-foreground">
            {en.awareness.privacyNote}
          </p>
        </Card>
      </main>
    </div>
  );
}
