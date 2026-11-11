'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Send, ShieldCheck } from 'lucide-react';

import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { en } from '@/content/en';
import { cn } from '@/lib/utils';

type CampaignStatus =
  | 'draft'
  | 'pending_authorization'
  | 'approved'
  | 'scheduled'
  | 'running'
  | 'paused'
  | 'completed'
  | 'cancelled';

type AuthorizationStatus = 'requested' | 'approved' | 'rejected' | 'expired' | 'revoked';

interface Authorization {
  id: string;
  campaign_id: string;
  campaign_name: string | null;
  status: AuthorizationStatus;
  reason: string | null;
  requested_by: string | null;
  requested_by_email: string | null;
  approved_by: string | null;
  approved_by_email: string | null;
  group_id: string;
  group_name: string | null;
  template_id: string;
  template_name: string | null;
  template_version: number;
  target_count: number;
  sending_domain: string;
  scheduled_send_time: string;
  start_date: string;
  end_date: string;
  requested_at: string | null;
  decided_at: string | null;
}

interface Campaign {
  id: string;
  name: string;
  description: string | null;
  template_id: string | null;
  template_version: number | null;
  template_name: string | null;
  group_id: string | null;
  group_name: string | null;
  target_count: number;
  send_time: string | null;
  sending_domain: string;
  status: CampaignStatus;
  created_by_email: string | null;
  authorization: Authorization | null;
  created_at: string | null;
  updated_at: string | null;
}

interface TemplateOption {
  id: string;
  name: string;
  sender: string;
  subject: string;
  difficulty: string;
  status: string;
  version: number;
}

interface GroupOption {
  id: string;
  name: string;
  member_count: number;
  min_group_size: number;
  suppressed: boolean;
}

interface CampaignsWorkspaceProps {
  isAdmin: boolean;
}

const STEP_KEYS = [
  'stepTemplate',
  'stepGroup',
  'stepSchedule',
  'stepReview',
  'stepLaunch',
] as const;

function format(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.split(`{${key}}`).join(String(value)),
    template,
  );
}

function dateLabel(value: string | null): string {
  if (!value) {
    return en.app.dash;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function toLocalInput(value: string | null): string {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function toIso(value: string): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function statusLabel(status: CampaignStatus): string {
  const labels: Record<CampaignStatus, string> = {
    draft: en.campaigns.statusDraft,
    pending_authorization: en.campaigns.statusPendingAuthorization,
    approved: en.campaigns.statusApproved,
    scheduled: en.campaigns.statusScheduled,
    running: en.campaigns.statusRunning,
    paused: en.campaigns.statusPaused,
    completed: en.campaigns.statusCompleted,
    cancelled: en.campaigns.statusCancelled,
  };
  return labels[status];
}

function statusVariant(status: CampaignStatus) {
  if (status === 'approved' || status === 'running') {
    return 'default' as const;
  }
  if (status === 'cancelled' || status === 'paused') {
    return 'destructive' as const;
  }
  return 'secondary' as const;
}

async function getCsrfToken(): Promise<string> {
  const res = await fetch('/api/v1/auth/csrf', {
    method: 'GET',
    cache: 'no-store',
    credentials: 'same-origin',
  });
  if (!res.ok) {
    throw new Error('csrf_unavailable');
  }
  const data = (await res.json()) as { csrf_token?: string };
  if (!data.csrf_token) {
    throw new Error('csrf_unavailable');
  }
  return data.csrf_token;
}

async function apiRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (method !== 'GET') {
    headers.set('X-CSRF-Token', await getCsrfToken());
  }
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  return fetch(path, {
    ...init,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  });
}

async function errorFields(res: Response): Promise<Record<string, string>> {
  try {
    const data = (await res.json()) as {
      error?: { fields?: Record<string, string>; message?: string; code?: string };
    };
    return data.error?.fields ?? {};
  } catch {
    return {};
  }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as {
      error?: { message?: string; code?: string };
    };
    return data.error?.message || en.campaigns.genericError;
  } catch {
    return en.campaigns.genericError;
  }
}

export default function CampaignsWorkspace({ isAdmin }: CampaignsWorkspaceProps) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Campaign | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [step, setStep] = useState(0);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [creating, setCreating] = useState(false);

  const [templates, setTemplates] = useState<TemplateOption[]>([]);
  const [groups, setGroups] = useState<GroupOption[]>([]);
  const [optionsError, setOptionsError] = useState('');

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [templateId, setTemplateId] = useState('');
  const [groupId, setGroupId] = useState('');
  const [sendTime, setSendTime] = useState('');
  const [sendingDomain, setSendingDomain] = useState('');

  const [testRecipient, setTestRecipient] = useState('sandbox@example.test');
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState('');
  const [testError, setTestError] = useState('');

  const [requesting, setRequesting] = useState(false);
  const [missing, setMissing] = useState<Record<string, string>>({});
  const [confirming, setConfirming] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [pausing, setPausing] = useState(false);

  const [approvals, setApprovals] = useState<Authorization[]>([]);
  const [approvalsLoading, setApprovalsLoading] = useState(false);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [decidingId, setDecidingId] = useState<string | null>(null);

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const detailRef = useRef<Campaign | null>(null);
  const selectedIdRef = useRef<string | null>(null);
  const listRequestRef = useRef(0);

  useEffect(() => {
    detailRef.current = detail;
  }, [detail]);

  const loadCampaigns = useCallback(async () => {
    const requestId = listRequestRef.current + 1;
    listRequestRef.current = requestId;
    setListLoading(true);
    setListError('');
    try {
      const res = await apiRequest('/api/v1/campaigns');
      if (!res.ok) {
        throw new Error(await errorMessage(res));
      }
      const data = (await res.json()) as { campaigns: Campaign[] };
      if (listRequestRef.current !== requestId) {
        return;
      }
      setCampaigns(data.campaigns);
      setSelectedId((current) => {
        if (current && data.campaigns.some((item) => item.id === current)) {
          return current;
        }
        return data.campaigns[0]?.id ?? null;
      });
    } catch {
      if (listRequestRef.current === requestId) {
        setListError(en.campaigns.listErrorBody);
      }
    } finally {
      if (listRequestRef.current === requestId) {
        setListLoading(false);
      }
    }
  }, []);

  const loadOptions = useCallback(async () => {
    setOptionsError('');
    try {
      const [templateRes, groupRes] = await Promise.all([
        apiRequest('/api/v1/templates?status=published'),
        apiRequest('/api/v1/groups'),
      ]);
      if (!templateRes.ok || !groupRes.ok) {
        throw new Error('options_unavailable');
      }
      const templateData = (await templateRes.json()) as { templates: TemplateOption[] };
      const groupData = (await groupRes.json()) as { groups: GroupOption[] };
      setTemplates(templateData.templates);
      setGroups(groupData.groups);
    } catch {
      setOptionsError(en.campaigns.genericError);
    }
  }, []);

  const loadApprovals = useCallback(async () => {
    if (!isAdmin) {
      return;
    }
    setApprovalsLoading(true);
    try {
      const res = await apiRequest('/api/v1/authorizations?status=requested');
      if (!res.ok) {
        throw new Error('approvals_unavailable');
      }
      const data = (await res.json()) as { authorizations: Authorization[] };
      setApprovals(data.authorizations);
    } catch {
      setApprovals([]);
    } finally {
      setApprovalsLoading(false);
    }
  }, [isAdmin]);

  const loadCampaign = useCallback(async (campaignId: string) => {
    setDetailLoading(true);
    setDetailError('');
    try {
      const res = await apiRequest(`/api/v1/campaigns/${campaignId}`);
      if (!res.ok) {
        throw new Error(await errorMessage(res));
      }
      const data = (await res.json()) as { campaign: Campaign };
      if (selectedIdRef.current !== campaignId) {
        return;
      }
      const campaign = data.campaign;
      setDetail(campaign);
      setName(campaign.name);
      setDescription(campaign.description ?? '');
      setTemplateId(campaign.template_id ?? '');
      setGroupId(campaign.group_id ?? '');
      setSendTime(toLocalInput(campaign.send_time));
      setSendingDomain(campaign.sending_domain);
      setStep((current) => {
        if (current !== 0) {
          return current;
        }
        if (campaign.status === 'draft') {
          return 0;
        }
        return 4;
      });
    } catch {
      if (selectedIdRef.current === campaignId) {
        setDetailError(en.campaigns.loadErrorBody);
        setDetail(null);
      }
    } finally {
      if (selectedIdRef.current === campaignId) {
        setDetailLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadCampaigns();
    void loadOptions();
    void loadApprovals();
  }, [loadCampaigns, loadOptions, loadApprovals]);

  useEffect(() => {
    selectedIdRef.current = selectedId;
    if (selectedId) {
      setStep(0);
      void loadCampaign(selectedId);
    } else {
      setDetail(null);
    }
  }, [selectedId, loadCampaign]);

  const buildPatch = useCallback((): Record<string, unknown> => {
    const campaign = detailRef.current;
    if (!campaign) {
      return {};
    }
    const patch: Record<string, unknown> = {};
    if (name !== campaign.name) {
      patch.name = name;
    }
    if ((description || '') !== (campaign.description ?? '')) {
      patch.description = description || null;
    }
    if ((templateId || null) !== campaign.template_id) {
      patch.template_id = templateId || null;
    }
    if ((groupId || null) !== campaign.group_id) {
      patch.group_id = groupId || null;
    }
    const iso = toIso(sendTime);
    if ((iso || null) !== campaign.send_time) {
      patch.send_time = iso;
    }
    if ((sendingDomain || '') !== campaign.sending_domain) {
      patch.sending_domain = sendingDomain;
    }
    return patch;
  }, [name, description, templateId, groupId, sendTime, sendingDomain]);

  const persistDraft = useCallback(async (): Promise<Campaign | null> => {
    const campaign = detailRef.current;
    if (!campaign || campaign.status !== 'draft') {
      return campaign;
    }
    const patch = buildPatch();
    if (Object.keys(patch).length === 0) {
      return campaign;
    }
    setSaveState('saving');
    const res = await apiRequest(`/api/v1/campaigns/${campaign.id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
    if (!res.ok) {
      setSaveState('error');
      setActionError(await errorMessage(res));
      return null;
    }
    const data = (await res.json()) as { campaign: Campaign };
    setDetail(data.campaign);
    detailRef.current = data.campaign;
    setCampaigns((rows) =>
      rows.map((row) => (row.id === data.campaign.id ? data.campaign : row)),
    );
    setSaveState('saved');
    return data.campaign;
  }, [buildPatch]);

  useEffect(() => {
    if (!detail || detail.status !== 'draft') {
      return;
    }
    const patch = buildPatch();
    if (Object.keys(patch).length === 0) {
      return;
    }
    setSaveState('saving');
    if (saveTimer.current) {
      clearTimeout(saveTimer.current);
    }
    saveTimer.current = setTimeout(() => {
      void persistDraft();
    }, 700);
    return () => {
      if (saveTimer.current) {
        clearTimeout(saveTimer.current);
      }
    };
  }, [buildPatch, detail, persistDraft]);

  async function onCreate(event: React.FormEvent) {
    event.preventDefault();
    if (creating) {
      return;
    }
    setActionError('');
    setNotice('');
    setCreating(true);
    try {
      const res = await apiRequest('/api/v1/campaigns', {
        method: 'POST',
        body: JSON.stringify({ name: newName, description: newDescription }),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { campaign: Campaign };
      setNewName('');
      setNewDescription('');
      setShowCreate(false);
      setNotice(en.campaigns.noticeCreated);
      selectedIdRef.current = data.campaign.id;
      setSelectedId(data.campaign.id);
      setDetail(data.campaign);
      setName(data.campaign.name);
      setDescription(data.campaign.description ?? '');
      setSendingDomain(data.campaign.sending_domain);
      setSendTime('');
      setTemplateId('');
      setGroupId('');
      setStep(0);
      await loadCampaigns();
    } catch {
      setActionError(en.campaigns.genericError);
    } finally {
      setCreating(false);
    }
  }

  async function onRequestAuthorization() {
    const campaign = await persistDraft();
    if (!campaign) {
      return;
    }
    setRequesting(true);
    setActionError('');
    setMissing({});
    try {
      const res = await apiRequest(`/api/v1/campaigns/${campaign.id}/request-authorization`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const fields = await errorFields(res);
        if (Object.keys(fields).length > 0) {
          setMissing(fields);
        } else {
          setActionError(await errorMessage(res));
        }
        return;
      }
      const data = (await res.json()) as { campaign: Campaign };
      setDetail(data.campaign);
      detailRef.current = data.campaign;
      setNotice(en.campaigns.authorizationRequested);
      await loadCampaigns();
      await loadApprovals();
    } catch {
      setActionError(en.campaigns.genericError);
    } finally {
      setRequesting(false);
    }
  }

  async function onTestSend() {
    if (!detail || testSending) {
      return;
    }
    setTestSending(true);
    setTestResult('');
    setTestError('');
    try {
      const res = await apiRequest(`/api/v1/campaigns/${detail.id}/test-send`, {
        method: 'POST',
        body: JSON.stringify({ recipient: testRecipient }),
      });
      if (!res.ok) {
        const fields = await errorFields(res);
        setTestError(fields.recipient || (await errorMessage(res)));
        return;
      }
      const data = (await res.json()) as { recipient: string };
      setTestResult(format(en.campaigns.testSendSuccess, { recipient: data.recipient }));
    } catch {
      setTestError(en.campaigns.genericError);
    } finally {
      setTestSending(false);
    }
  }

  async function onLaunch() {
    if (!detail || launching) {
      return;
    }
    setLaunching(true);
    setActionError('');
    setMissing({});
    try {
      const res = await apiRequest(`/api/v1/campaigns/${detail.id}/launch`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const fields = await errorFields(res);
        if (Object.keys(fields).length > 0) {
          setMissing(fields);
        } else {
          setActionError(await errorMessage(res));
        }
        return;
      }
      const data = (await res.json()) as { campaign: Campaign };
      setConfirming(false);
      setDetail(data.campaign);
      detailRef.current = data.campaign;
      setNotice(en.campaigns.noticeLaunched);
      await loadCampaigns();
    } catch {
      setActionError(en.campaigns.genericError);
    } finally {
      setLaunching(false);
    }
  }

  async function onPause() {
    if (!detail || pausing) {
      return;
    }
    setPausing(true);
    setActionError('');
    try {
      const res = await apiRequest(`/api/v1/campaigns/${detail.id}/pause`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { campaign: Campaign };
      setDetail(data.campaign);
      detailRef.current = data.campaign;
      setNotice(en.campaigns.noticePaused);
      await loadCampaigns();
    } catch {
      setActionError(en.campaigns.genericError);
    } finally {
      setPausing(false);
    }
  }

  async function onCancel() {
    if (!detail) {
      return;
    }
    if (!window.confirm(en.campaigns.cancelConfirm)) {
      return;
    }
    setActionError('');
    try {
      const res = await apiRequest(`/api/v1/campaigns/${detail.id}/cancel`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { campaign: Campaign };
      setDetail(data.campaign);
      detailRef.current = data.campaign;
      setNotice(en.campaigns.noticeCancelled);
      await loadCampaigns();
      await loadApprovals();
    } catch {
      setActionError(en.campaigns.genericError);
    }
  }

  async function onApprove(authorization: Authorization) {
    setDecidingId(authorization.id);
    setActionError('');
    try {
      const res = await apiRequest(`/api/v1/authorizations/${authorization.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      setNotice(en.campaigns.approvalDone);
      await loadApprovals();
      await loadCampaigns();
      if (selectedId === authorization.campaign_id) {
        await loadCampaign(authorization.campaign_id);
      }
    } catch {
      setActionError(en.campaigns.genericError);
    } finally {
      setDecidingId(null);
    }
  }

  async function onReject(authorization: Authorization) {
    const reason = rejectReason.trim();
    if (!reason) {
      setActionError(en.campaigns.rejectReasonRequired);
      return;
    }
    setDecidingId(authorization.id);
    setActionError('');
    try {
      const res = await apiRequest(`/api/v1/authorizations/${authorization.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      setRejectingId(null);
      setRejectReason('');
      setNotice(en.campaigns.rejectionDone);
      await loadApprovals();
      await loadCampaigns();
    } catch {
      setActionError(en.campaigns.genericError);
    } finally {
      setDecidingId(null);
    }
  }

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === templateId) ?? null,
    [templates, templateId],
  );
  const selectedGroup = useMemo(
    () => groups.find((group) => group.id === groupId) ?? null,
    [groups, groupId],
  );
  const authorization = detail?.authorization ?? null;
  const canEdit = detail?.status === 'draft';
  const complete = Boolean(templateId && groupId && sendTime && sendingDomain);
  const stepName = en.campaigns[STEP_KEYS[step]];

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{en.campaigns.title}</h1>
          <p className="mt-1 max-w-prose text-sm text-muted-foreground">
            {en.campaigns.subtitle}
          </p>
        </div>
        <Button
          type="button"
          onClick={() => setShowCreate((open) => !open)}
          aria-expanded={showCreate}
          data-testid="new-campaign"
        >
          <Send aria-hidden="true" size={16} />
          {en.campaigns.newCampaign}
        </Button>
      </div>

      {notice !== '' && (
        <p role="status" className="mb-4 text-sm font-medium text-success">
          {notice}
        </p>
      )}
      {actionError !== '' && (
        <Alert variant="danger" title={en.campaigns.actionErrorTitle} className="mb-4">
          {actionError}
        </Alert>
      )}
      {optionsError !== '' && (
        <Alert variant="danger" title={en.campaigns.actionErrorTitle} className="mb-4">
          {optionsError}
        </Alert>
      )}

      {showCreate && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle as="h2">{en.campaigns.createTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreate} className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="campaign-name">{en.campaigns.nameLabel}</Label>
                <Input
                  id="campaign-name"
                  className="mt-1"
                  required
                  value={newName}
                  placeholder={en.campaigns.namePlaceholder}
                  onChange={(event) => setNewName(event.target.value)}
                  data-testid="campaign-name"
                />
              </div>
              <div>
                <Label htmlFor="campaign-description">{en.campaigns.descriptionLabel}</Label>
                <Input
                  id="campaign-description"
                  className="mt-1"
                  value={newDescription}
                  placeholder={en.campaigns.descriptionPlaceholder}
                  onChange={(event) => setNewDescription(event.target.value)}
                  data-testid="campaign-description"
                />
              </div>
              <div className="md:col-span-2">
                <Button
                  type="submit"
                  disabled={creating}
                  aria-busy={creating}
                  data-testid="create-campaign"
                >
                  {creating ? en.campaigns.creatingCampaign : en.campaigns.createCampaign}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {isAdmin && (
        <Card className="mb-6" data-testid="approvals-panel">
          <CardHeader>
            <CardTitle as="h2">{en.campaigns.approvalsTitle}</CardTitle>
            <CardDescription>{en.campaigns.approvalsHelp}</CardDescription>
          </CardHeader>
          <CardContent>
            {approvalsLoading && (
              <p role="status" className="text-sm text-muted-foreground">
                {en.campaigns.approvalsLoading}
              </p>
            )}
            {!approvalsLoading && approvals.length === 0 && (
              <p className="text-sm text-muted-foreground">{en.campaigns.approvalsEmpty}</p>
            )}
            {!approvalsLoading && approvals.length > 0 && (
              <ul className="flex flex-col gap-3">
                {approvals.map((item) => (
                  <li key={item.id} className="rounded-lg border border-border p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{item.campaign_name}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {format(en.campaigns.approvalScope, {
                            count: item.target_count,
                            group: item.group_name ?? en.app.dash,
                            time: dateLabel(item.scheduled_send_time),
                          })}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {format(en.campaigns.approvalRequestedBy, {
                            email: item.requested_by_email ?? en.app.dash,
                          })}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {item.template_name ?? en.app.dash} · v{item.template_version} ·{' '}
                          {item.sending_domain}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Button
                          type="button"
                          size="sm"
                          disabled={decidingId === item.id}
                          onClick={() => void onApprove(item)}
                          data-testid={`approve-${item.id}`}
                        >
                          {decidingId === item.id ? en.campaigns.approving : en.campaigns.approve}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            setRejectingId(rejectingId === item.id ? null : item.id);
                            setRejectReason('');
                          }}
                          data-testid={`reject-${item.id}`}
                        >
                          {en.campaigns.reject}
                        </Button>
                      </div>
                    </div>
                    {rejectingId === item.id && (
                      <div className="mt-3 flex flex-col gap-2">
                        <Label htmlFor={`reject-reason-${item.id}`}>
                          {en.campaigns.rejectReasonLabel}
                        </Label>
                        <Input
                          id={`reject-reason-${item.id}`}
                          value={rejectReason}
                          placeholder={en.campaigns.rejectReasonPlaceholder}
                          onChange={(event) => setRejectReason(event.target.value)}
                          data-testid={`reject-reason-${item.id}`}
                        />
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          className="self-start"
                          disabled={decidingId === item.id}
                          onClick={() => void onReject(item)}
                          data-testid={`reject-submit-${item.id}`}
                        >
                          {decidingId === item.id ? en.campaigns.rejecting : en.campaigns.reject}
                        </Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="h-fit" data-testid="campaign-list">
          <CardHeader>
            <CardTitle as="h2">{en.campaigns.campaignListTitle}</CardTitle>
            <CardDescription>{en.campaigns.campaignListDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            {listLoading && (
              <p role="status" className="text-sm text-muted-foreground">
                {en.campaigns.listLoading}
              </p>
            )}
            {!listLoading && listError !== '' && (
              <Alert variant="danger" title={en.campaigns.listErrorTitle}>
                <p>{listError}</p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => void loadCampaigns()}
                >
                  {en.campaigns.retry}
                </Button>
              </Alert>
            )}
            {!listLoading && listError === '' && campaigns.length === 0 && (
              <div>
                <p className="font-medium">{en.campaigns.emptyTitle}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {en.campaigns.emptyBody}
                </p>
              </div>
            )}
            {!listLoading && campaigns.length > 0 && (
              <ul className="flex flex-col gap-2">
                {campaigns.map((campaign) => {
                  const selected = campaign.id === selectedId;
                  return (
                    <li key={campaign.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(campaign.id)}
                        aria-pressed={selected}
                        className={cn(
                          'w-full rounded-lg border px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                          selected
                            ? 'border-primary bg-primary-tint'
                            : 'border-border hover:bg-accent hover:text-accent-foreground',
                        )}
                        data-testid={`campaign-option-${campaign.id}`}
                      >
                        <span className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{campaign.name}</span>
                          <Badge variant={statusVariant(campaign.status)}>
                            {statusLabel(campaign.status)}
                          </Badge>
                        </span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {campaign.group_name ?? en.campaigns.groupPlaceholder} ·{' '}
                          {campaign.target_count} {en.campaigns.reviewRecipients.toLowerCase()}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-6">
          {!selectedId && !listLoading && listError === '' && (
            <Card>
              <CardContent>
                <p className="font-medium">{en.campaigns.selectPrompt}</p>
              </CardContent>
            </Card>
          )}

          {selectedId && (
            <Card data-testid="campaign-detail">
              <CardHeader>
                {detailLoading && (
                  <p role="status" className="text-sm text-muted-foreground">
                    {en.common.loading}
                  </p>
                )}
                {!detailLoading && detailError !== '' && (
                  <Alert variant="danger" title={en.campaigns.loadErrorTitle}>
                    <p>{detailError}</p>
                  </Alert>
                )}
                {!detailLoading && detail && (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <CardTitle as="h2">{detail.name}</CardTitle>
                      <Badge variant={statusVariant(detail.status)} data-testid="campaign-status">
                        {statusLabel(detail.status)}
                      </Badge>
                    </div>
                    <CardDescription>
                      {detail.template_name ?? en.campaigns.templatePlaceholder} ·{' '}
                      {detail.group_name ?? en.campaigns.groupPlaceholder} ·{' '}
                      {detail.target_count} {en.campaigns.reviewRecipients.toLowerCase()}
                    </CardDescription>
                    {canEdit && (
                      <p
                        className="text-xs text-muted-foreground"
                        role="status"
                        data-testid="autosave-status"
                      >
                        {saveState === 'saving' && en.campaigns.autosaveSaving}
                        {saveState === 'saved' && en.campaigns.autosaveSaved}
                        {saveState === 'error' && en.campaigns.autosaveError}
                        {saveState === 'idle' && en.campaigns.autosaveIdle}
                      </p>
                    )}
                  </>
                )}
              </CardHeader>

              {!detailLoading && detail && (
                <CardContent>
                  <nav aria-label={en.campaigns.stepperLabel} className="mb-6">
                    <ol className="grid gap-2 sm:grid-cols-5">
                      {STEP_KEYS.map((key, index) => {
                        const current = index === step;
                        const done = index < step;
                        return (
                          <li key={key}>
                            <button
                              type="button"
                              onClick={() => setStep(index)}
                              aria-current={current ? 'step' : undefined}
                              className={cn(
                                'flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                                current
                                  ? 'border-primary bg-primary-tint text-primary-strong'
                                  : 'border-border text-muted-foreground hover:bg-surface-muted',
                              )}
                              data-testid={`wizard-step-${index}`}
                            >
                              <span
                                className={cn(
                                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px]',
                                  done
                                    ? 'border-success bg-success-tint text-success'
                                    : 'border-current',
                                )}
                                aria-hidden="true"
                              >
                                {done ? <Check size={12} /> : index + 1}
                              </span>
                              {en.campaigns[key]}
                            </button>
                          </li>
                        );
                      })}
                    </ol>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {format(en.campaigns.stepLabel, {
                        current: step + 1,
                        total: STEP_KEYS.length,
                        name: stepName,
                      })}
                    </p>
                  </nav>

                  {detail.status !== 'draft' && detail.status !== 'approved' && (
                    <Alert variant="info" title={statusLabel(detail.status)} className="mb-4">
                      {en.campaigns.readOnly}
                    </Alert>
                  )}

                  {missing && Object.keys(missing).length > 0 && (
                    <Alert
                      variant="warning"
                      title={en.campaigns.launchBlockedTitle}
                      className="mb-4"
                      data-testid="launch-missing"
                    >
                      <p>{en.campaigns.launchBlockedBody}</p>
                      <ul className="mt-2 list-disc pl-5">
                        {Object.entries(missing).map(([field, message]) => (
                          <li key={field}>
                            <span className="font-medium">{field}</span>: {message}
                          </li>
                        ))}
                      </ul>
                    </Alert>
                  )}

                  {step === 0 && (
                    <section aria-labelledby="template-heading">
                      <h3 id="template-heading" className="text-lg font-semibold">
                        {en.campaigns.templateTitle}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {en.campaigns.templateHelp}
                      </p>
                      <div className="mt-4 max-w-xl">
                        <Label htmlFor="campaign-template">{en.campaigns.templateLabel}</Label>
                        <select
                          id="campaign-template"
                          className="mt-1 flex min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2 text-base text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
                          value={templateId}
                          disabled={!canEdit}
                          onChange={(event) => setTemplateId(event.target.value)}
                          data-testid="campaign-template"
                        >
                          <option value="">{en.campaigns.templatePlaceholder}</option>
                          {templates.map((template) => (
                            <option key={template.id} value={template.id}>
                              {template.name} (v{template.version}, {template.difficulty})
                            </option>
                          ))}
                        </select>
                        {selectedTemplate && (
                          <p className="mt-2 text-xs text-muted-foreground">
                            {selectedTemplate.sender} · {selectedTemplate.subject}
                          </p>
                        )}
                      </div>
                    </section>
                  )}

                  {step === 1 && (
                    <section aria-labelledby="group-heading">
                      <h3 id="group-heading" className="text-lg font-semibold">
                        {en.campaigns.groupTitle}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {en.campaigns.groupHelp}
                      </p>
                      <div className="mt-4 max-w-xl">
                        <Label htmlFor="campaign-group">{en.campaigns.groupLabel}</Label>
                        <select
                          id="campaign-group"
                          className="mt-1 flex min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2 text-base text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
                          value={groupId}
                          disabled={!canEdit}
                          onChange={(event) => setGroupId(event.target.value)}
                          data-testid="campaign-group"
                        >
                          <option value="">{en.campaigns.groupPlaceholder}</option>
                          {groups.map((group) => (
                            <option key={group.id} value={group.id}>
                              {format(en.campaigns.groupOption, {
                                name: group.name,
                                count: group.member_count,
                              })}
                            </option>
                          ))}
                        </select>
                        {selectedGroup?.suppressed && (
                          <Alert variant="warning" title={en.campaigns.groupTitle} className="mt-3">
                            {format(en.campaigns.groupHelp, {
                              count: selectedGroup.member_count,
                            })}
                          </Alert>
                        )}
                      </div>
                    </section>
                  )}

                  {step === 2 && (
                    <section aria-labelledby="schedule-heading">
                      <h3 id="schedule-heading" className="text-lg font-semibold">
                        {en.campaigns.scheduleTitle}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {en.campaigns.scheduleHelp}
                      </p>
                      <div className="mt-4 grid max-w-xl gap-4 md:grid-cols-2">
                        <div>
                          <Label htmlFor="campaign-send-time">{en.campaigns.sendTimeLabel}</Label>
                          <Input
                            id="campaign-send-time"
                            type="datetime-local"
                            className="mt-1"
                            value={sendTime}
                            disabled={!canEdit}
                            onChange={(event) => setSendTime(event.target.value)}
                            data-testid="campaign-send-time"
                          />
                        </div>
                        <div>
                          <Label htmlFor="campaign-domain">
                            {en.campaigns.sendingDomainLabel}
                          </Label>
                          <Input
                            id="campaign-domain"
                            className="mt-1"
                            value={sendingDomain}
                            disabled={!canEdit}
                            onChange={(event) => setSendingDomain(event.target.value)}
                            aria-describedby="campaign-domain-help"
                            data-testid="campaign-domain"
                          />
                          <p
                            id="campaign-domain-help"
                            className="mt-1 text-xs text-muted-foreground"
                          >
                            {en.campaigns.sendingDomainHelp}
                          </p>
                        </div>
                      </div>
                    </section>
                  )}

                  {step === 3 && (
                    <section aria-labelledby="review-heading" data-testid="review-scope">
                      <h3 id="review-heading" className="text-lg font-semibold">
                        {en.campaigns.reviewTitle}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {en.campaigns.reviewHelp}
                      </p>
                      {!complete && (
                        <Alert variant="warning" title={en.campaigns.incompleteTitle} className="mt-4">
                          {en.campaigns.reviewIncomplete}
                        </Alert>
                      )}
                      <dl className="mt-4 grid gap-3 rounded-lg border border-border p-4 sm:grid-cols-2">
                        <div>
                          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {en.campaigns.reviewName}
                          </dt>
                          <dd className="mt-1 text-sm font-medium">{name}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {en.campaigns.reviewTemplate}
                          </dt>
                          <dd className="mt-1 text-sm">{selectedTemplate?.name ?? en.app.dash}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {en.campaigns.reviewGroup}
                          </dt>
                          <dd className="mt-1 text-sm">{selectedGroup?.name ?? en.app.dash}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {en.campaigns.reviewRecipients}
                          </dt>
                          <dd className="mt-1 text-sm">{selectedGroup?.member_count ?? 0}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {en.campaigns.reviewSendTime}
                          </dt>
                          <dd className="mt-1 text-sm">{dateLabel(toIso(sendTime))}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {en.campaigns.reviewDomain}
                          </dt>
                          <dd className="mt-1 text-sm">{sendingDomain}</dd>
                        </div>
                      </dl>
                    </section>
                  )}

                  {step === 4 && (
                    <section aria-labelledby="launch-heading" className="flex flex-col gap-6">
                      <div>
                        <h3 id="launch-heading" className="text-lg font-semibold">
                          {en.campaigns.launchTitle}
                        </h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {en.campaigns.launchHelp}
                        </p>
                      </div>

                      <div className="rounded-lg border border-border p-4">
                        <h4 className="font-semibold">{en.campaigns.testSendTitle}</h4>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {en.campaigns.testSendHelp}
                        </p>
                        <div className="mt-3 flex max-w-xl flex-col gap-2 sm:flex-row sm:items-end">
                          <div className="flex-1">
                            <Label htmlFor="test-recipient">
                              {en.campaigns.testSendRecipient}
                            </Label>
                            <Input
                              id="test-recipient"
                              className="mt-1"
                              value={testRecipient}
                              onChange={(event) => setTestRecipient(event.target.value)}
                              data-testid="test-send-recipient"
                            />
                          </div>
                          <Button
                            type="button"
                            variant="secondary"
                            disabled={testSending || !detail.template_id}
                            aria-busy={testSending}
                            onClick={() => void onTestSend()}
                            data-testid="test-send"
                          >
                            {testSending ? en.campaigns.testSending : en.campaigns.testSend}
                          </Button>
                        </div>
                        {testResult !== '' && (
                          <p
                            role="status"
                            className="mt-3 text-sm font-medium text-success"
                            data-testid="test-send-result"
                          >
                            {testResult}
                          </p>
                        )}
                        {testError !== '' && (
                          <Alert
                            variant="danger"
                            title={en.campaigns.testSendErrorTitle}
                            className="mt-3"
                          >
                            {testError}
                          </Alert>
                        )}
                      </div>

                      <div
                        className="rounded-lg border border-border p-4"
                        data-testid="authorization-status"
                      >
                        <h4 className="flex items-center gap-2 font-semibold">
                          <ShieldCheck size={16} aria-hidden="true" />
                          {en.campaigns.authorizationTitle}
                        </h4>
                        {!authorization && (
                          <p className="mt-2 text-sm text-muted-foreground">
                            {en.campaigns.authorizationNone}
                          </p>
                        )}
                        {authorization && (
                          <div className="mt-2 space-y-1 text-sm">
                            <p>
                              <span className="font-semibold">
                                {en.campaigns.authorizationStatus}:
                              </span>{' '}
                              {authorization.status}
                            </p>
                            <p className="text-muted-foreground">
                              {format(en.campaigns.approvalScope, {
                                count: authorization.target_count,
                                group: authorization.group_name ?? en.app.dash,
                                time: dateLabel(authorization.scheduled_send_time),
                              })}
                            </p>
                            {authorization.requested_by_email && (
                              <p className="text-muted-foreground">
                                {format(en.campaigns.approvalRequestedBy, {
                                  email: authorization.requested_by_email,
                                })}
                              </p>
                            )}
                            {authorization.approved_by_email && (
                              <p className="text-muted-foreground">
                                {en.campaigns.authorizationApprovedBy}:{' '}
                                {authorization.approved_by_email}
                              </p>
                            )}
                            <p className="text-muted-foreground">
                              {en.campaigns.authorizationWindow}:{' '}
                              {dateLabel(authorization.start_date)} –{' '}
                              {dateLabel(authorization.end_date)}
                            </p>
                            {authorization.reason && (
                              <p className="text-muted-foreground">
                                {en.campaigns.authorizationReason}: {authorization.reason}
                              </p>
                            )}
                            {authorization.status === 'requested' && (
                              <p className="text-muted-foreground">
                                {en.campaigns.authorizationNeeded}
                              </p>
                            )}
                            {authorization.status === 'approved' && (
                              <p className="font-medium text-success">
                                {en.campaigns.authorizationApproved}
                              </p>
                            )}
                            {authorization.status === 'rejected' && (
                              <p className="font-medium text-danger-strong">
                                {en.campaigns.authorizationRejected}
                              </p>
                            )}
                            {authorization.status === 'revoked' && (
                              <p className="font-medium text-danger-strong">
                                {en.campaigns.authorizationRevoked}
                              </p>
                            )}
                            {authorization.status === 'expired' && (
                              <p className="font-medium text-danger-strong">
                                {en.campaigns.authorizationExpired}
                              </p>
                            )}
                          </div>
                        )}
                        {(detail.status === 'draft' ||
                          (authorization &&
                            ['rejected', 'revoked', 'expired'].includes(
                              authorization.status,
                            ))) && (
                          <Button
                            type="button"
                            className="mt-3"
                            disabled={requesting}
                            aria-busy={requesting}
                            onClick={() => void onRequestAuthorization()}
                            data-testid="request-authorization"
                          >
                            {requesting
                              ? en.campaigns.authorizationRequesting
                              : en.campaigns.authorizationRequest}
                          </Button>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        {detail.status === 'approved' && !confirming && (
                          <Button
                            type="button"
                            onClick={() => setConfirming(true)}
                            data-testid="launch-campaign"
                          >
                            {en.campaigns.launchCampaign}
                          </Button>
                        )}
                        {(detail.status === 'scheduled' || detail.status === 'running') && (
                          <Button
                            type="button"
                            variant="secondary"
                            disabled={pausing}
                            aria-busy={pausing}
                            onClick={() => void onPause()}
                            data-testid="pause-campaign"
                          >
                            {en.campaigns.pauseCampaign}
                          </Button>
                        )}
                        {!['completed', 'cancelled'].includes(detail.status) && (
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={() => void onCancel()}
                            data-testid="cancel-campaign"
                          >
                            {en.campaigns.cancelCampaign}
                          </Button>
                        )}
                      </div>

                      {confirming && detail.status === 'approved' && (
                        <div
                          role="alertdialog"
                          aria-labelledby="confirm-heading"
                          aria-describedby="confirm-body"
                          className="rounded-lg border border-primary bg-primary-tint p-4"
                          data-testid="confirm-launch-dialog"
                        >
                          <h4 id="confirm-heading" className="font-semibold">
                            {en.campaigns.confirmTitle}
                          </h4>
                          <p id="confirm-body" className="mt-1 text-sm">
                            {format(en.campaigns.confirmImpact, {
                              count: detail.target_count,
                              time: dateLabel(detail.send_time),
                              group: detail.group_name ?? en.app.dash,
                            })}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {en.campaigns.confirmBody}
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button
                              type="button"
                              disabled={launching}
                              aria-busy={launching}
                              onClick={() => void onLaunch()}
                              data-testid="confirm-launch"
                            >
                              {launching ? en.campaigns.launching : en.campaigns.confirmLaunch}
                            </Button>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() => setConfirming(false)}
                            >
                              {en.common.cancel}
                            </Button>
                          </div>
                        </div>
                      )}
                    </section>
                  )}

                  <div className="mt-6 flex items-center justify-between gap-2 border-t border-border pt-4">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={step === 0}
                      onClick={() => setStep((current) => Math.max(0, current - 1))}
                      data-testid="wizard-back"
                    >
                      {en.campaigns.back}
                    </Button>
                    <Button
                      type="button"
                      disabled={step === 4 || (step >= 2 && !complete)}
                      onClick={() => setStep((current) => Math.min(4, current + 1))}
                      data-testid="wizard-next"
                    >
                      {en.campaigns.next}
                    </Button>
                  </div>
                </CardContent>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
