'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

import { Alert } from '@/components/ui/alert';
import { Button, buttonVariants } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SkeletonList } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/toast';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { en } from '@/content/en';

const PAGE_SIZE = 50;

interface AuditEvent {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_user_id: string | null;
  actor_email: string | null;
  reason: string | null;
  request_id: string | null;
  before: unknown;
  after: unknown;
  created_at: string;
}

interface AuditListResponse {
  events: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

interface Filters {
  action: string;
  entityType: string;
  entityId: string;
  actor: string;
  dateFrom: string;
  dateTo: string;
}

const EMPTY_FILTERS: Filters = {
  action: '',
  entityType: '',
  entityId: '',
  actor: '',
  dateFrom: '',
  dateTo: '',
};

function format(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.split(`{${key}}`).join(String(value)),
    template,
  );
}

function dateLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function details(event: AuditEvent): string {
  const payload = event.after ?? event.before;
  if (payload == null) {
    return en.app.dash;
  }
  const text = JSON.stringify(payload);
  return text.length > 180 ? `${text.slice(0, 177)}...` : text;
}

function toIso(value: string): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function buildQuery(filters: Filters, offset: number): string {
  const params = new URLSearchParams();
  if (filters.action.trim()) params.set('action', filters.action.trim());
  if (filters.entityType.trim()) params.set('entity_type', filters.entityType.trim());
  if (filters.entityId.trim()) params.set('entity_id', filters.entityId.trim());
  if (filters.actor.trim()) params.set('actor_user_id', filters.actor.trim());
  const from = toIso(filters.dateFrom);
  if (from) params.set('date_from', from);
  const to = toIso(filters.dateTo);
  if (to) params.set('date_to', to);
  params.set('limit', String(PAGE_SIZE));
  params.set('offset', String(offset));
  return params.toString();
}

async function getCsrfToken(): Promise<string> {
  const response = await fetch('/api/v1/auth/csrf', {
    method: 'GET',
    cache: 'no-store',
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw new Error('csrf_unavailable');
  }
  const data = (await response.json()) as { csrf_token?: string };
  if (!data.csrf_token) {
    throw new Error('csrf_unavailable');
  }
  return data.csrf_token;
}

export default function AuditLogWorkspace() {
  const { showToast } = useToast();
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exportError, setExportError] = useState('');
  const [exporting, setExporting] = useState(false);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.floor(offset / PAGE_SIZE) + 1;

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/v1/audit?${buildQuery(applied, offset)}`, {
        cache: 'no-store',
      });
      if (!response.ok) {
        throw new Error('audit_unavailable');
      }
      const data = (await response.json()) as AuditListResponse;
      setEvents(data.events);
      setTotal(data.total);
    } catch {
      setEvents([]);
      setTotal(0);
      setError(en.audit.errorBody);
    } finally {
      setLoading(false);
    }
  }, [applied, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  function onApply(event: React.FormEvent) {
    event.preventDefault();
    setOffset(0);
    setApplied({ ...filters });
  }

  function onReset() {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    setOffset(0);
  }

  async function onExport() {
    if (exporting) {
      return;
    }
    setExporting(true);
    setExportError('');
    try {
      const csrf = await getCsrfToken();
      const payload = {
        action: applied.action.trim() || null,
        entity_type: applied.entityType.trim() || null,
        entity_id: applied.entityId.trim() || null,
        actor_user_id: applied.actor.trim() || null,
        date_from: toIso(applied.dateFrom),
        date_to: toIso(applied.dateTo),
      };
      const response = await fetch('/api/v1/audit/export', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error('export_failed');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'audit-log.csv';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      showToast(en.audit.downloadToast);
    } catch {
      setExportError(en.audit.exportErrorBody);
      showToast(en.audit.exportErrorTitle, 'error');
    } finally {
      setExporting(false);
    }
  }

  const countLabel = useMemo(
    () =>
      total === 1
        ? en.audit.countOne
        : format(en.audit.count, { count: total }),
    [total],
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{en.audit.filtersTitle}</CardTitle>
          <CardDescription>{en.audit.filtersDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onApply} className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="audit-action">{en.audit.actionLabel}</Label>
              <Input
                id="audit-action"
                className="mt-1"
                value={filters.action}
                placeholder={en.audit.actionPlaceholder}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, action: event.target.value }))
                }
              />
            </div>
            <div>
              <Label htmlFor="audit-entity-type">{en.audit.entityTypeLabel}</Label>
              <Input
                id="audit-entity-type"
                className="mt-1"
                value={filters.entityType}
                placeholder={en.audit.entityTypePlaceholder}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, entityType: event.target.value }))
                }
              />
            </div>
            <div>
              <Label htmlFor="audit-entity-id">{en.audit.entityIdLabel}</Label>
              <Input
                id="audit-entity-id"
                className="mt-1"
                value={filters.entityId}
                placeholder={en.audit.entityIdPlaceholder}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, entityId: event.target.value }))
                }
              />
            </div>
            <div>
              <Label htmlFor="audit-actor">{en.audit.actorLabel}</Label>
              <Input
                id="audit-actor"
                className="mt-1"
                value={filters.actor}
                placeholder={en.audit.actorPlaceholder}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, actor: event.target.value }))
                }
              />
            </div>
            <div>
              <Label htmlFor="audit-date-from">{en.audit.dateFromLabel}</Label>
              <Input
                id="audit-date-from"
                type="datetime-local"
                className="mt-1"
                value={filters.dateFrom}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, dateFrom: event.target.value }))
                }
              />
            </div>
            <div>
              <Label htmlFor="audit-date-to">{en.audit.dateToLabel}</Label>
              <Input
                id="audit-date-to"
                type="datetime-local"
                className="mt-1"
                value={filters.dateTo}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, dateTo: event.target.value }))
                }
              />
            </div>
            <div className="flex flex-wrap items-center gap-2 md:col-span-2">
              <Button type="submit">{en.audit.apply}</Button>
              <Button type="button" variant="secondary" onClick={onReset}>
                {en.audit.reset}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={exporting}
                aria-busy={exporting}
                onClick={() => void onExport()}
                data-testid="audit-export"
              >
                {exporting ? en.audit.exporting : en.audit.exportCsv}
              </Button>
              <Link href="/settings" className={buttonVariants({ variant: 'ghost' })}>
                {en.audit.backToSettings}
              </Link>
            </div>
          </form>
          {exportError !== '' && (
            <Alert variant="danger" title={en.audit.exportErrorTitle} className="mt-4">
              {exportError}
            </Alert>
          )}
        </CardContent>
      </Card>

      {error !== '' && (
        <Alert variant="danger" title={en.audit.errorTitle}>
          {error}
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{countLabel}</CardTitle>
          {loading && (
            <CardDescription role="status">{en.audit.loading}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {loading && events.length === 0 ? (
            <SkeletonList rows={5} />
          ) : events.length === 0 && error === '' ? (
            <div className="py-6 text-center">
              <p className="font-semibold">{en.audit.emptyTitle}</p>
              <p className="mt-1 text-sm text-muted-foreground">{en.audit.emptyBody}</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{en.audit.timeColumn}</TableHead>
                  <TableHead>{en.audit.actionColumn}</TableHead>
                  <TableHead>{en.audit.entityColumn}</TableHead>
                  <TableHead>{en.audit.actorColumn}</TableHead>
                  <TableHead>{en.audit.reasonColumn}</TableHead>
                  <TableHead>{en.audit.detailsColumn}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="whitespace-nowrap">
                      {dateLabel(event.created_at)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{event.action}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {event.entity_type}
                      {event.entity_id ? `:${event.entity_id}` : ''}
                    </TableCell>
                    <TableCell>{event.actor_email ?? en.app.dash}</TableCell>
                    <TableCell>{event.reason ?? en.app.dash}</TableCell>
                    <TableCell className="max-w-md font-mono text-xs">
                      {details(event)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">
              {format(en.audit.pageLabel, { page, pages })}
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={offset === 0 || loading}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
              >
                {en.audit.previous}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={offset + PAGE_SIZE >= total || loading}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
              >
                {en.audit.next}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
