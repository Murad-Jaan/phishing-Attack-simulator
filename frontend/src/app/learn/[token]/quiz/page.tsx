import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft, ShieldCheck } from 'lucide-react';

import { QuizRunner } from '@/components/awareness/quiz-runner';
import { en } from '@/content/en';

export const metadata: Metadata = {
  title: en.awareness.quiz.title,
  description: en.awareness.quiz.description,
};

export default async function AwarenessQuizPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

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
          <span className="text-sm font-semibold text-foreground">{en.app.name}</span>
        </div>
      </header>

      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto max-w-3xl px-4 py-10 sm:py-14"
      >
        <Link
          href={`/learn/${encodeURIComponent(token)}`}
          className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-strong hover:underline"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          {en.awareness.quiz.backToAwareness}
        </Link>
        <h1 className="mt-4 text-3xl font-bold leading-10 tracking-tight text-foreground sm:text-4xl sm:leading-[48px]">
          {en.awareness.quiz.title}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
          {en.awareness.quiz.description}
        </p>

        <QuizRunner token={token} />
      </main>
    </div>
  );
}
