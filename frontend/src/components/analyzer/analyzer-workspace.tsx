'use client';

import { useId, useState } from 'react';
import { FileText, Link2, ShieldAlert, Upload } from 'lucide-react';

import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { en } from '@/content/en';
import {
  AnalyzerApiError,
  analyzeEml,
  analyzePaste,
  reportAnalysis,
  type AnalyzerAnalysis,
} from '@/lib/api/analyzer';
import { cn } from '@/lib/utils';

type Tab = 'paste' | 'upload';
type Verdict = AnalyzerAnalysis['label'];

const COPY = en.analyzer;

const SAMPLE = {
  sender: 'security@paypa1-support.com',
  subject: 'URGENT: Your account will be suspended!',
  body: 'Dear Customer, we detected unusual activity. Verify your account within 24 hours or it will be permanently closed.',
  link: 'http://paypa1-verify.com/login',
};

const VERDICT_TEXT: Record<Verdict, string> = {
  Safe: COPY.verdictSafe,
  Suspicious: COPY.verdictSuspicious,
  'Likely phishing': COPY.verdictLikely,
};

const LABEL_BADGE: Record<Verdict, 'secondary' | 'outline' | 'destructive'> = {
  Safe: 'secondary',
  Suspicious: 'outline',
  'Likely phishing': 'destructive',
};

const SCORE_TEXT: Record<Verdict, string> = {
  Safe: 'text-success',
  Suspicious: 'text-warning',
  'Likely phishing': 'text-danger-strong',
};

const METER_FILL: Record<Verdict, string> = {
  Safe: 'bg-success',
  Suspicious: 'bg-warning',
  'Likely phishing': 'bg-danger-strong',
};

const SEGMENTS = Array.from({ length: 20 }, (_, index) => index);

export function AnalyzerWorkspace() {
  const ids = useId();
  const [tab, setTab] = useState<Tab>('paste');
  const [sender, setSender] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [link, setLink] = useState('');
  const [orgDomain, setOrgDomain] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnalyzerAnalysis | null>(null);
  const [reporting, setReporting] = useState(false);
  const [reported, setReported] = useState(false);
  const [reportError, setReportError] = useState('');

  const pastePanelId = `${ids}-paste-panel`;
  const uploadPanelId = `${ids}-upload-panel`;
  const pasteTabId = `${ids}-paste-tab`;
  const uploadTabId = `${ids}-upload-tab`;

  function loadSample() {
    setTab('paste');
    setSender(SAMPLE.sender);
    setSubject(SAMPLE.subject);
    setBody(SAMPLE.body);
    setLink(SAMPLE.link);
    setError('');
    setReportError('');
    setReported(false);
    setResult(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setReportError('');
    setReported(false);

    if (!consent) {
      setError(COPY.consentError);
      return;
    }
    if (tab === 'upload' && !file) {
      setError(COPY.fileError);
      return;
    }

    setBusy(true);
    try {
      const analysis =
        tab === 'paste'
          ? await analyzePaste({
              sender,
              subject,
              body,
              link,
              org_domain: orgDomain.trim() || undefined,
              consent,
            })
          : await analyzeEml(file as File, consent, orgDomain.trim() || undefined);
      setResult(analysis);
    } catch (caught) {
      if (caught instanceof AnalyzerApiError) {
        if (caught.code === 'file_too_large') {
          setError(COPY.tooLarge);
        } else if (caught.fields.file) {
          setError(caught.fields.file);
        } else {
          setError(caught.message || COPY.errorBody);
        }
      } else {
        setError(COPY.errorBody);
      }
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  async function handleReport() {
    if (!result) {
      return;
    }
    setReporting(true);
    setReportError('');
    try {
      await reportAnalysis(result.label, result.rule_ids);
      setReported(true);
    } catch {
      setReportError(COPY.reportErrorBody);
    } finally {
      setReporting(false);
    }
  }

  const filledSegments = result ? Math.ceil(result.score / 5) : 0;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle as="h2">{COPY.tabsLabel}</CardTitle>
          <CardDescription>{COPY.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-6" onSubmit={handleSubmit} noValidate>
            <div
              role="tablist"
              aria-label={COPY.tabsLabel}
              className="inline-flex flex-wrap gap-2 rounded-xl border border-border bg-surface-muted p-1"
            >
              <button
                id={pasteTabId}
                type="button"
                role="tab"
                aria-selected={tab === 'paste'}
                aria-controls={pastePanelId}
                data-testid="analyzer-tab-paste"
                onClick={() => setTab('paste')}
                className={cn(
                  'inline-flex min-h-11 items-center gap-2 rounded-lg px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  tab === 'paste'
                    ? 'bg-surface text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <FileText className="h-4 w-4" aria-hidden="true" />
                {COPY.pasteTab}
              </button>
              <button
                id={uploadTabId}
                type="button"
                role="tab"
                aria-selected={tab === 'upload'}
                aria-controls={uploadPanelId}
                data-testid="analyzer-tab-upload"
                onClick={() => setTab('upload')}
                className={cn(
                  'inline-flex min-h-11 items-center gap-2 rounded-lg px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  tab === 'upload'
                    ? 'bg-surface text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Upload className="h-4 w-4" aria-hidden="true" />
                {COPY.uploadTab}
              </button>
            </div>

            {tab === 'paste' ? (
              <div
                id={pastePanelId}
                role="tabpanel"
                aria-labelledby={pasteTabId}
                className="grid gap-4 sm:grid-cols-2"
              >
                <div className="space-y-2">
                  <Label htmlFor={`${ids}-sender`}>{COPY.senderLabel}</Label>
                  <Input
                    id={`${ids}-sender`}
                    value={sender}
                    onChange={(event) => setSender(event.target.value)}
                    placeholder={COPY.senderPlaceholder}
                    autoComplete="off"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`${ids}-subject`}>{COPY.subjectLabel}</Label>
                  <Input
                    id={`${ids}-subject`}
                    value={subject}
                    onChange={(event) => setSubject(event.target.value)}
                    autoComplete="off"
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor={`${ids}-body`}>{COPY.bodyLabel}</Label>
                  <textarea
                    id={`${ids}-body`}
                    value={body}
                    onChange={(event) => setBody(event.target.value)}
                    placeholder={COPY.bodyPlaceholder}
                    rows={7}
                    className="flex min-h-32 w-full rounded-lg border border-input bg-surface px-3 py-2 text-base text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background md:text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`${ids}-link`}>{COPY.linkLabel}</Label>
                  <Input
                    id={`${ids}-link`}
                    value={link}
                    onChange={(event) => setLink(event.target.value)}
                    placeholder={COPY.linkPlaceholder}
                    autoComplete="off"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`${ids}-org`}>{COPY.orgDomainLabel}</Label>
                  <Input
                    id={`${ids}-org`}
                    value={orgDomain}
                    onChange={(event) => setOrgDomain(event.target.value)}
                    placeholder={COPY.orgDomainPlaceholder}
                    autoComplete="off"
                  />
                </div>
              </div>
            ) : (
              <div
                id={uploadPanelId}
                role="tabpanel"
                aria-labelledby={uploadTabId}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor={`${ids}-file`}>{COPY.fileLabel}</Label>
                  <input
                    id={`${ids}-file`}
                    data-testid="analyzer-file"
                    type="file"
                    accept=".eml,.txt,message/rfc822"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                    className="block w-full cursor-pointer rounded-lg border border-input bg-surface px-3 py-2 text-sm text-foreground file:mr-3 file:rounded-md file:border-0 file:bg-surface-muted file:px-3 file:py-2 file:text-sm file:font-semibold file:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  <p className="text-sm text-muted-foreground">{COPY.fileHelp}</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`${ids}-upload-org`}>{COPY.orgDomainLabel}</Label>
                  <Input
                    id={`${ids}-upload-org`}
                    value={orgDomain}
                    onChange={(event) => setOrgDomain(event.target.value)}
                    placeholder={COPY.orgDomainPlaceholder}
                    autoComplete="off"
                  />
                </div>
              </div>
            )}

            <div className="flex items-start gap-3">
              <input
                id={`${ids}-consent`}
                data-testid="analyzer-consent"
                type="checkbox"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
                className="mt-0.5 h-5 w-5 rounded border-input text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              <Label htmlFor={`${ids}-consent`} className="font-normal leading-6">
                {COPY.consentLabel}
              </Label>
            </div>

            {error ? (
              <Alert variant="danger" title={COPY.errorTitle}>
                {error}
              </Alert>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" data-testid="analyzer-submit" disabled={busy}>
                <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                {busy ? COPY.analyzing : COPY.submit}
              </Button>
              <Button
                type="button"
                variant="secondary"
                data-testid="analyzer-load-sample"
                onClick={loadSample}
              >
                {COPY.loadSample}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div aria-live="polite">
        {result ? (
          <Card data-testid="analyzer-result">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1">
                  <CardTitle as="h2">{COPY.resultTitle}</CardTitle>
                  <CardDescription>{VERDICT_TEXT[result.label]}</CardDescription>
                </div>
                <Badge
                  variant={LABEL_BADGE[result.label]}
                  data-testid="analyzer-label"
                  className="text-sm"
                >
                  {VERDICT_TEXT[result.label]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-8">
              <div className="space-y-3">
                <div className="flex items-baseline justify-between gap-4">
                  <p className="text-sm font-semibold text-foreground">{COPY.scoreLabel}</p>
                  <p
                    data-testid="analyzer-score"
                    className={cn('text-2xl font-bold tabular-nums', SCORE_TEXT[result.label])}
                  >
                    {result.score}
                    <span className="text-sm font-medium text-muted-foreground">/100</span>
                  </p>
                </div>
                <div
                  role="meter"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={result.score}
                  aria-valuetext={`${VERDICT_TEXT[result.label]}, ${result.score} of 100`}
                  aria-label={COPY.scoreLabel}
                  data-testid="analyzer-meter"
                  className="flex gap-1"
                >
                  {SEGMENTS.map((segment) => (
                    <span
                      key={segment}
                      aria-hidden="true"
                      className={cn(
                        'h-2 flex-1 rounded-full',
                        segment < filledSegments ? METER_FILL[result.label] : 'bg-border',
                      )}
                    />
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-base font-semibold text-foreground">{COPY.findingsTitle}</h3>
                {result.findings.length > 0 ? (
                  <ul data-testid="analyzer-findings" className="space-y-4">
                    {result.findings.map((finding, index) => (
                      <li
                        key={`${finding.rule_id}-${index}`}
                        className="rounded-xl border border-border bg-surface-muted p-4"
                      >
                        <div className="mb-1 flex flex-wrap items-center gap-2">
                          <Badge variant="outline">{finding.rule_id}</Badge>
                          <span className="text-xs font-medium text-muted-foreground">
                            +{finding.weight}
                          </span>
                        </div>
                        <p className="text-sm leading-6 text-foreground">{finding.reason}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p data-testid="analyzer-findings" className="text-sm text-muted-foreground">
                    {COPY.findingsEmpty}
                  </p>
                )}
              </div>

              <div className="grid gap-8 lg:grid-cols-2">
                <div className="space-y-3">
                  <h3 className="flex items-center gap-2 text-base font-semibold text-foreground">
                    <Link2 className="h-4 w-4" aria-hidden="true" />
                    {COPY.linksTitle}
                  </h3>
                  <p className="text-sm text-muted-foreground">{COPY.linksNote}</p>
                  {result.links.length > 0 ? (
                    <ul data-testid="analyzer-links" className="space-y-2">
                      {result.links.map((found, index) => (
                        <li
                          key={`${found.host}-${index}`}
                          className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm"
                        >
                          <span className="font-semibold text-foreground">{found.host}</span>
                          {found.text ? (
                            <span className="ml-2 text-muted-foreground">{found.text}</span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p data-testid="analyzer-links" className="text-sm text-muted-foreground">
                      {COPY.linksEmpty}
                    </p>
                  )}
                </div>

                <div className="space-y-3">
                  <h3 className="text-base font-semibold text-foreground">{COPY.actionsTitle}</h3>
                  <ul data-testid="analyzer-actions" className="list-disc space-y-2 pl-5">
                    {result.what_to_do.map((action) => (
                      <li key={action} className="text-sm leading-6 text-foreground">
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-base font-semibold text-foreground">{COPY.parsedTitle}</h3>
                <dl className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">{COPY.fromLabel}</dt>
                    <dd className="break-words text-sm font-semibold text-foreground">
                      {result.parsed.from || COPY.none}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">
                      {COPY.replyToLabel}
                    </dt>
                    <dd className="break-words text-sm font-semibold text-foreground">
                      {result.parsed.reply_to || COPY.none}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-sm font-medium text-muted-foreground">
                      {COPY.subjectLabel}
                    </dt>
                    <dd className="break-words text-sm font-semibold text-foreground">
                      {result.parsed.subject || COPY.none}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-sm font-medium text-muted-foreground">
                      {COPY.attachmentsLabel}
                    </dt>
                    <dd className="break-words text-sm font-semibold text-foreground">
                      {result.parsed.attachments.length > 0
                        ? result.parsed.attachments.join(', ')
                        : COPY.noAttachments}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="flex flex-wrap items-center gap-3 border-t border-border pt-6">
                <Button
                  type="button"
                  data-testid="analyzer-report"
                  onClick={handleReport}
                  disabled={reporting || reported}
                >
                  {reporting ? COPY.reporting : COPY.report}
                </Button>
                {reported ? (
                  <p data-testid="analyzer-reported" className="text-sm text-success">
                    {COPY.reported}
                  </p>
                ) : null}
              </div>
              {reportError ? (
                <Alert variant="danger" title={COPY.reportErrorTitle}>
                  {reportError}
                </Alert>
              ) : null}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
