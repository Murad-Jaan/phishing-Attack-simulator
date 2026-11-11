'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Eye,
  Flag,
  Monitor,
  RotateCcw,
  Search,
  Smartphone,
  X,
} from 'lucide-react';

import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { en } from '@/content/en';
import {
  fetchTemplatePreview,
  fetchTemplates,
  type TemplatePreview,
  type TemplateSummary,
} from '@/lib/api/templates';
import { cn } from '@/lib/utils';

const difficultyLabel = {
  easy: en.templates.easy,
  medium: en.templates.medium,
  hard: en.templates.hard,
} as const;

const statusLabel = {
  draft: en.templates.draft,
  published: en.templates.published,
  archived: en.templates.archived,
} as const;

const difficultyTone = {
  easy: 'border-success-tint-border bg-success-tint text-success',
  medium: 'border-warning-tint-border bg-warning-tint text-warning',
  hard: 'border-danger-tint-border bg-danger-tint text-danger-strong',
} as const;

function redFlagText(count: number): string {
  if (count === 0) {
    return en.templates.noRedFlags;
  }
  if (count === 1) {
    return en.templates.redFlagCountOne;
  }
  return en.templates.redFlagCount.replace('{count}', String(count));
}

function formatUpdated(value: string | null): string {
  if (!value) {
    return '';
  }
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

export function TemplateLibrary() {
  const [search, setSearch] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [technique, setTechnique] = useState('');
  const [status, setStatus] = useState('');
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const [previewTemplate, setPreviewTemplate] = useState<TemplateSummary | null>(
    null,
  );
  const [preview, setPreview] = useState<TemplatePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [previewReloadKey, setPreviewReloadKey] = useState(0);
  const [showRedFlags, setShowRedFlags] = useState(true);
  const [viewport, setViewport] = useState<'desktop' | 'mobile'>('desktop');
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const data = await fetchTemplates(
          { search, difficulty, technique, status },
          controller.signal,
        );
        if (!active) return;
        setTemplates(data.templates);
        setTotal(data.total);
        setError(false);
      } catch (err) {
        if (!active || controller.signal.aborted) return;
        setError(true);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }, search.trim() ? 250 : 0);

    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [search, difficulty, technique, status, reloadKey]);

  useEffect(() => {
    if (!previewTemplate) {
      return;
    }
    const controller = new AbortController();
    let active = true;
    setPreviewLoading(true);
    setPreviewError(false);
    fetchTemplatePreview(previewTemplate.id, controller.signal)
      .then((data) => {
        if (!active) return;
        setPreview(data);
      })
      .catch(() => {
        if (!active || controller.signal.aborted) return;
        setPreviewError(true);
      })
      .finally(() => {
        if (active) {
          setPreviewLoading(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [previewTemplate, previewReloadKey]);

  useEffect(() => {
    if (!previewTemplate) {
      return;
    }
    closeButtonRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setPreviewTemplate(null);
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [previewTemplate]);

  const closePreview = useCallback(() => {
    setPreviewTemplate(null);
    setPreview(null);
    setPreviewError(false);
  }, []);

  const openPreview = useCallback((template: TemplateSummary) => {
    setPreview(null);
    setPreviewError(false);
    setShowRedFlags(true);
    setViewport('desktop');
    setPreviewTemplate(template);
  }, []);

  const hasFilters = Boolean(
    search.trim() || difficulty || technique.trim() || status,
  );

  function clearFilters() {
    setSearch('');
    setDifficulty('');
    setTechnique('');
    setStatus('');
  }

  const resultCount =
    total === 1
      ? en.templates.resultCountOne
      : en.templates.resultCount.replace('{count}', String(total));

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm md:p-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-2 md:col-span-2 xl:col-span-1">
            <label
              htmlFor="template-search"
              className="block text-sm font-medium text-foreground"
            >
              {en.templates.searchLabel}
            </label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                id="template-search"
                data-testid="template-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={en.templates.searchPlaceholder}
                className="pl-9"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="template-difficulty"
              className="block text-sm font-medium text-foreground"
            >
              {en.templates.difficultyLabel}
            </label>
            <select
              id="template-difficulty"
              data-testid="template-difficulty"
              value={difficulty}
              onChange={(event) => setDifficulty(event.target.value)}
              className="min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2 text-base text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background md:text-sm"
            >
              <option value="">{en.templates.allDifficulties}</option>
              <option value="easy">{en.templates.easy}</option>
              <option value="medium">{en.templates.medium}</option>
              <option value="hard">{en.templates.hard}</option>
            </select>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="template-technique"
              className="block text-sm font-medium text-foreground"
            >
              {en.templates.techniqueLabel}
            </label>
            <Input
              id="template-technique"
              data-testid="template-technique"
              value={technique}
              onChange={(event) => setTechnique(event.target.value)}
              placeholder={en.templates.techniquePlaceholder}
              aria-describedby="template-technique-help"
            />
            <p
              id="template-technique-help"
              className="text-xs text-muted-foreground"
            >
              {en.templates.techniqueHelp}
            </p>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="template-status"
              className="block text-sm font-medium text-foreground"
            >
              {en.templates.statusLabel}
            </label>
            <select
              id="template-status"
              data-testid="template-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2 text-base text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background md:text-sm"
            >
              <option value="">{en.templates.allStatuses}</option>
              <option value="draft">{en.templates.draft}</option>
              <option value="published">{en.templates.published}</option>
              <option value="archived">{en.templates.archived}</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p
            className="text-sm font-medium text-muted-foreground"
            role="status"
            aria-live="polite"
            data-testid="template-count"
          >
            {loading && templates.length === 0 ? en.templates.loading : resultCount}
          </p>
          {hasFilters ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              data-testid="clear-template-filters"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              {en.templates.clearFilters}
            </Button>
          ) : null}
        </div>
      </div>

      <section
        aria-busy={loading}
        aria-label={en.templates.title}
        data-testid="template-results"
      >
        {error ? (
          <Alert variant="danger" title={en.templates.loadErrorTitle}>
            <div className="space-y-3">
              <p>{en.templates.loadErrorBody}</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setReloadKey((key) => key + 1)}
                data-testid="retry-templates"
              >
                {en.templates.retry}
              </Button>
            </div>
          </Alert>
        ) : loading && templates.length === 0 ? (
          <div
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
            aria-hidden="true"
            data-testid="template-loading"
          >
            {[0, 1, 2, 3, 4, 5].map((item) => (
              <Card key={item} className="p-5 md:p-5">
                <div className="h-5 w-2/3 animate-pulse rounded bg-surface-muted" />
                <div className="mt-4 h-6 w-1/3 animate-pulse rounded bg-surface-muted" />
                <div className="mt-4 h-4 w-full animate-pulse rounded bg-surface-muted" />
                <div className="mt-2 h-4 w-4/5 animate-pulse rounded bg-surface-muted" />
                <div className="mt-6 h-11 w-32 animate-pulse rounded bg-surface-muted" />
              </Card>
            ))}
          </div>
        ) : templates.length === 0 ? (
          <Card className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <span
              className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-tint text-primary-strong"
              aria-hidden="true"
            >
              <Search className="h-6 w-6" />
            </span>
            <h2 className="text-lg font-semibold leading-7 text-foreground">
              {hasFilters
                ? en.templates.emptyTitle
                : en.templates.emptyLibraryTitle}
            </h2>
            <p className="max-w-md text-sm leading-6 text-muted-foreground">
              {hasFilters
                ? en.templates.emptyBody
                : en.templates.emptyLibraryBody}
            </p>
            {hasFilters ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={clearFilters}
                data-testid="empty-clear-filters"
              >
                {en.templates.clearFilters}
              </Button>
            ) : null}
          </Card>
        ) : (
          <div
            className={cn(
              'grid gap-4 sm:grid-cols-2 xl:grid-cols-3',
              loading ? 'opacity-70' : undefined,
            )}
            data-testid="template-grid"
          >
            {templates.map((template) => (
              <Card
                key={template.id}
                className="flex flex-col p-5 md:p-5"
                data-testid={`template-card-${template.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-base font-semibold leading-6 text-foreground">
                    {template.name}
                  </h2>
                  <Badge variant="secondary">{statusLabel[template.status]}</Badge>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge
                    variant="outline"
                    className={difficultyTone[template.difficulty]}
                  >
                    {difficultyLabel[template.difficulty]}
                  </Badge>
                  {template.attack_technique_id !== 'none' ? (
                    <Badge variant="outline">{template.attack_technique_id}</Badge>
                  ) : null}
                  <Badge variant="outline">
                    <span className="sr-only">
                      {en.templates.versionLabel.replace(
                        '{version}',
                        String(template.version),
                      )}
                      :{' '}
                    </span>
                    v{template.version}
                  </Badge>
                </div>

                <p className="mt-3 line-clamp-2 text-sm leading-6 text-muted-foreground">
                  {template.subject}
                </p>

                <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-strong">
                  <Flag className="h-3.5 w-3.5" aria-hidden="true" />
                  {redFlagText(template.red_flag_count)}
                </p>

                {template.status === 'archived' ? (
                  <p className="mt-2 text-xs leading-5 text-warning">
                    {en.templates.archivedWarning}
                  </p>
                ) : null}

                <div className="mt-auto flex items-end justify-between gap-3 pt-4">
                  <span className="text-xs text-muted-foreground">
                    {formatUpdated(template.updated_at)}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => openPreview(template)}
                    data-testid={`template-preview-${template.id}`}
                  >
                    <Eye className="h-4 w-4" aria-hidden="true" />
                    {en.templates.preview}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      {previewTemplate ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-2 sm:p-6"
          role="presentation"
          data-testid="template-preview-dialog"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closePreview();
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="template-preview-title"
            aria-describedby="template-preview-description"
            className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-xl"
          >
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border p-4 md:p-6">
              <div className="min-w-0 space-y-2">
                <h2
                  id="template-preview-title"
                  className="text-lg font-semibold leading-7 text-foreground"
                >
                  {previewTemplate.name}
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant="outline"
                    className={difficultyTone[previewTemplate.difficulty]}
                  >
                    {difficultyLabel[previewTemplate.difficulty]}
                  </Badge>
                  {previewTemplate.attack_technique_id !== 'none' ? (
                    <Badge variant="outline">
                      {previewTemplate.attack_technique_id}
                    </Badge>
                  ) : null}
                  <Badge variant="secondary">
                    {en.templates.versionLabel.replace(
                      '{version}',
                      String(previewTemplate.version),
                    )}
                  </Badge>
                </div>
                <p
                  id="template-preview-description"
                  className="max-w-2xl text-sm leading-5 text-muted-foreground"
                >
                  {en.templates.previewDescription}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <label className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-foreground">
                  <input
                    type="checkbox"
                    checked={showRedFlags}
                    onChange={(event) => setShowRedFlags(event.target.checked)}
                    className="h-4 w-4 rounded border-input"
                    data-testid="red-flags-toggle"
                  />
                  {en.templates.showRedFlags}
                </label>

                <div
                  role="group"
                  aria-label={en.templates.viewportLabel}
                  className="flex items-center gap-1 rounded-lg border border-border bg-surface-muted p-1"
                >
                  <Button
                    variant={viewport === 'desktop' ? 'secondary' : 'ghost'}
                    size="sm"
                    aria-pressed={viewport === 'desktop'}
                    onClick={() => setViewport('desktop')}
                    data-testid="viewport-desktop"
                  >
                    <Monitor className="h-4 w-4" aria-hidden="true" />
                    {en.templates.desktop}
                  </Button>
                  <Button
                    variant={viewport === 'mobile' ? 'secondary' : 'ghost'}
                    size="sm"
                    aria-pressed={viewport === 'mobile'}
                    onClick={() => setViewport('mobile')}
                    data-testid="viewport-mobile"
                  >
                    <Smartphone className="h-4 w-4" aria-hidden="true" />
                    {en.templates.mobile}
                  </Button>
                </div>

                <Button
                  ref={closeButtonRef}
                  variant="ghost"
                  size="icon"
                  onClick={closePreview}
                  aria-label={en.templates.closePreview}
                  data-testid="close-template-preview"
                >
                  <X className="h-5 w-5" aria-hidden="true" />
                </Button>
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
              <div className="min-h-0 flex-1 overflow-auto bg-background p-4 md:p-6">
                <div
                  data-testid="preview-viewport"
                  data-viewport={viewport}
                  className={cn(
                    'mx-auto min-h-64 rounded-xl border border-border bg-surface p-4 text-sm leading-6 text-foreground transition-[max-width,width] motion-reduce:transition-none md:p-6',
                    viewport === 'mobile'
                      ? 'w-full max-w-[360px]'
                      : 'w-full max-w-[680px]',
                  )}
                >
                  {previewLoading ? (
                    <div role="status" className="space-y-3">
                      <span className="sr-only">{en.templates.previewLoading}</span>
                      <div className="h-4 w-1/2 animate-pulse rounded bg-surface-muted" />
                      <div className="h-4 w-3/4 animate-pulse rounded bg-surface-muted" />
                      <div className="h-4 w-2/3 animate-pulse rounded bg-surface-muted" />
                      <div className="mt-6 h-24 w-full animate-pulse rounded bg-surface-muted" />
                    </div>
                  ) : previewError ? (
                    <Alert variant="danger" title={en.templates.previewErrorTitle}>
                      <div className="space-y-3">
                        <p>{en.templates.previewErrorBody}</p>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setPreviewReloadKey((key) => key + 1)}
                          data-testid="retry-template-preview"
                        >
                          {en.templates.retry}
                        </Button>
                      </div>
                    </Alert>
                  ) : preview ? (
                    <div
                      dangerouslySetInnerHTML={{ __html: preview.html }}
                      data-testid="template-preview-content"
                    />
                  ) : null}
                </div>
                <p className="mx-auto mt-3 max-w-[680px] text-xs leading-5 text-muted-foreground">
                  {en.templates.simulationNote}
                </p>
              </div>

              {showRedFlags ? (
                <aside
                  aria-label={en.templates.redFlagsPanel}
                  className="w-full shrink-0 overflow-auto border-t border-border bg-surface-muted p-4 lg:w-80 lg:border-l lg:border-t-0 md:p-6"
                  data-testid="red-flags-panel"
                >
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-strong">
                    {en.templates.redFlagsPanel}
                  </h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {en.templates.learnerView}
                  </p>
                  {previewLoading ? (
                    <div className="mt-4 space-y-3" aria-hidden="true">
                      <div className="h-4 w-full animate-pulse rounded bg-surface" />
                      <div className="h-4 w-4/5 animate-pulse rounded bg-surface" />
                    </div>
                  ) : preview && preview.red_flags.length > 0 ? (
                    <ul className="mt-4 space-y-4">
                      {preview.red_flags.map((flag) => (
                        <li key={flag.id} className="flex gap-2">
                          <Flag
                            className="mt-0.5 h-4 w-4 shrink-0 text-danger-strong"
                            aria-hidden="true"
                          />
                          <div>
                            <p className="text-sm font-semibold leading-5 text-foreground">
                              {flag.label}
                            </p>
                            <p className="mt-1 text-xs leading-5 text-muted-foreground">
                              {flag.explanation}
                            </p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-muted-foreground">
                      {en.templates.noRedFlags}
                    </p>
                  )}
                </aside>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
