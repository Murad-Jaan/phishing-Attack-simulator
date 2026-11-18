'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, CheckCircle2, RotateCcw, XCircle } from 'lucide-react';

import { Alert } from '@/components/ui/alert';
import { Button, buttonVariants } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { en } from '@/content/en';

const questions = en.awareness.quiz.questions;

export function QuizRunner({ token }: { token: string }) {
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [completed, setCompleted] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError] = useState(false);
  const nextRef = useRef<HTMLButtonElement>(null);
  const firstOptionRef = useRef<HTMLInputElement>(null);
  const question = questions[index];
  const answered = selected !== null;
  const isCorrect = selected === question.correctIndex;

  useEffect(() => {
    if (answered) {
      nextRef.current?.focus();
    }
  }, [answered]);

  useEffect(() => {
    if (index > 0 && !answered) {
      firstOptionRef.current?.focus();
    }
  }, [index, answered]);

  async function finish(): Promise<void> {
    setFinishing(true);
    setError(false);
    try {
      const response = await fetch(
        `/api/v1/quiz/${encodeURIComponent(token)}/complete`,
        { method: 'POST', credentials: 'same-origin', cache: 'no-store' },
      );
      if (!response.ok) {
        throw new Error('completion failed');
      }
      setCompleted(true);
    } catch {
      setError(true);
    } finally {
      setFinishing(false);
    }
  }

  function advance(): void {
    if (index + 1 < questions.length) {
      setIndex(index + 1);
      setSelected(null);
      return;
    }
    void finish();
  }

  function retry(): void {
    setIndex(0);
    setSelected(null);
    setError(false);
    setCompleted(false);
  }

  return (
    <Card className="mt-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold leading-7 text-foreground">
            {completed ? en.awareness.quiz.completedTitle : en.awareness.quiz.title}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {completed ? en.awareness.quiz.completedBody : en.awareness.quiz.description}
          </p>
        </div>
        {!completed ? (
          <p
            className="shrink-0 rounded-full border border-border bg-surface-muted px-3 py-1 text-xs font-semibold text-foreground"
            aria-label={en.awareness.quiz.progressLabel}
          >
            {en.awareness.quiz.progress
              .replace('{current}', String(index + 1))
              .replace('{total}', String(questions.length))}
          </p>
        ) : null}
      </div>

      {completed ? (
        <div className="mt-6 flex flex-col items-start gap-4">
          <span className="flex items-center gap-2 rounded-full border border-success-tint-border bg-success-tint px-3 py-1 text-sm font-semibold text-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            {en.awareness.quiz.completedTitle}
          </span>
          <div className="flex flex-wrap gap-3">
            <Link
              href={`/learn/${encodeURIComponent(token)}`}
              className={buttonVariants()}
            >
              {en.awareness.quiz.backToAwareness}
            </Link>
            <Button variant="secondary" onClick={retry}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              {en.awareness.quiz.retry}
            </Button>
          </div>
        </div>
      ) : (
        <form
          className="mt-6"
          onSubmit={(event) => {
            event.preventDefault();
            if (answered) {
              advance();
            }
          }}
        >
          <fieldset>
            <legend className="text-base font-semibold leading-6 text-foreground">
              {question.prompt}
            </legend>
            <p className="mt-1 text-sm text-muted-foreground">
              {en.awareness.quiz.chooseAnswer}
            </p>
            <div className="mt-4 space-y-3">
              {question.options.map((option, optionIndex) => {
                const chosen = selected === optionIndex;
                const showCorrect = answered && optionIndex === question.correctIndex;
                return (
                  <label
                    key={option}
                    className="flex min-h-11 cursor-pointer gap-3 rounded-xl border border-border bg-surface p-4 text-sm leading-6 text-foreground has-[:checked]:border-primary has-[:checked]:bg-primary-tint has-[:disabled]:cursor-default"
                  >
                    <input
                      ref={optionIndex === 0 ? firstOptionRef : undefined}
                      type="radio"
                      name={`question-${question.id}`}
                      value={optionIndex}
                      checked={chosen}
                      disabled={answered}
                      onChange={() => setSelected(optionIndex)}
                      className="mt-1 h-4 w-4 shrink-0 accent-primary"
                    />
                    <span className="min-w-0">
                      <span className="block">{option}</span>
                      {answered && chosen ? (
                        <span
                          className={
                            isCorrect
                              ? 'mt-1 flex items-center gap-1 text-xs font-semibold text-success'
                              : 'mt-1 flex items-center gap-1 text-xs font-semibold text-danger-strong'
                          }
                        >
                          {isCorrect ? (
                            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                          )}
                          {isCorrect
                            ? en.awareness.quiz.correct
                            : en.awareness.quiz.incorrect}
                        </span>
                      ) : null}
                      {showCorrect && !chosen ? (
                        <span className="mt-1 flex items-center gap-1 text-xs font-semibold text-success">
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                          {en.awareness.quiz.correct}
                        </span>
                      ) : null}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          {answered ? (
            <div
              className="mt-4 rounded-xl border border-border bg-surface-muted p-4"
              aria-live="polite"
            >
              <p className="text-sm font-semibold text-foreground">
                {en.awareness.quiz.explanationLabel}
              </p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {question.explanation}
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="mt-4">
              <Alert variant="danger" title={en.awareness.quiz.completedTitle}>
                {en.awareness.quiz.completionError}
              </Alert>
            </div>
          ) : null}

          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              ref={nextRef}
              type="submit"
              disabled={!answered || finishing}
              data-testid="quiz-next"
            >
              {index + 1 === questions.length
                ? finishing
                  ? en.awareness.quiz.finishing
                  : en.awareness.quiz.finish
                : en.awareness.quiz.next}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
            {error ? (
              <Button variant="secondary" onClick={() => void finish()}>
                {en.awareness.quiz.finish}
              </Button>
            ) : null}
          </div>
        </form>
      )}
    </Card>
  );
}
