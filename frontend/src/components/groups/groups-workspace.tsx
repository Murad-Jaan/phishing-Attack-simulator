'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Users, Upload } from 'lucide-react';

import { Alert } from '@/components/ui/alert';
import { badgeVariants } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { en } from '@/content/en';
import { cn } from '@/lib/utils';

interface Group {
  id: string;
  name: string;
  description: string | null;
  department: string | null;
  member_count: number;
  min_group_size: number;
  suppressed: boolean;
}

interface Target {
  id: string;
  email: string;
  display_name: string | null;
}

interface GroupDetail extends Group {
  members: Target[];
}

interface ImportRowError {
  row: number;
  message: string;
  line: string;
}

interface ImportResult {
  imported: number;
  skipped: number;
  total: number;
  errors: ImportRowError[];
}

function format(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.split(`{${key}}`).join(String(value)),
    template
  );
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

async function errorMessage(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as {
      error?: { code?: string; message?: string };
    };
    if (data.error?.code === 'duplicate_member') {
      return en.groups.duplicateMember;
    }
    return data.error?.message || en.groups.genericError;
  } catch {
    return en.groups.genericError;
  }
}

export default function GroupsWorkspace() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GroupDetail | null>(null);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [groupsError, setGroupsError] = useState('');
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');

  const [showNewGroup, setShowNewGroup] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [department, setDepartment] = useState('');
  const [description, setDescription] = useState('');
  const [creatingGroup, setCreatingGroup] = useState(false);

  const [memberEmail, setMemberEmail] = useState('');
  const [memberName, setMemberName] = useState('');
  const [addingMember, setAddingMember] = useState(false);

  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importFileError, setImportFileError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadGroups = useCallback(async () => {
    setGroupsLoading(true);
    setGroupsError('');
    try {
      const res = await apiRequest('/api/v1/groups');
      if (!res.ok) {
        throw new Error(await errorMessage(res));
      }
      const data = (await res.json()) as { groups: Group[] };
      setGroups(data.groups);
      setSelectedId((current) => {
        if (current && data.groups.some((g) => g.id === current)) {
          return current;
        }
        return data.groups[0]?.id ?? null;
      });
    } catch {
      setGroupsError(en.groups.groupsErrorBody);
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  const loadGroup = useCallback(async (groupId: string) => {
    setDetailLoading(true);
    setDetailError('');
    try {
      const res = await apiRequest(`/api/v1/groups/${groupId}`);
      if (!res.ok) {
        throw new Error(await errorMessage(res));
      }
      const data = (await res.json()) as { group: GroupDetail };
      setDetail(data.group);
    } catch {
      setDetailError(en.groups.groupsErrorBody);
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  useEffect(() => {
    if (selectedId) {
      void loadGroup(selectedId);
    } else {
      setDetail(null);
    }
  }, [selectedId, loadGroup]);

  async function onCreateGroup(event: React.FormEvent) {
    event.preventDefault();
    if (creatingGroup) {
      return;
    }
    setActionError('');
    setNotice('');
    setCreatingGroup(true);
    try {
      const res = await apiRequest('/api/v1/groups', {
        method: 'POST',
        body: JSON.stringify({ name: groupName, department, description }),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { group: Group };
      setGroupName('');
      setDepartment('');
      setDescription('');
      setShowNewGroup(false);
      setNotice(en.groups.noticeGroupCreated);
      setSelectedId(data.group.id);
      await loadGroups();
      await loadGroup(data.group.id);
    } catch {
      setActionError(en.groups.genericError);
    } finally {
      setCreatingGroup(false);
    }
  }

  async function onAddMember(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedId || addingMember) {
      return;
    }
    setActionError('');
    setNotice('');
    setAddingMember(true);
    try {
      const res = await apiRequest(`/api/v1/groups/${selectedId}/members`, {
        method: 'POST',
        body: JSON.stringify({ email: memberEmail, display_name: memberName }),
      });
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { group: GroupDetail };
      setDetail(data.group);
      setMemberEmail('');
      setMemberName('');
      setNotice(en.groups.noticeUserAdded);
      await loadGroups();
    } catch {
      setActionError(en.groups.genericError);
    } finally {
      setAddingMember(false);
    }
  }

  async function onRemoveMember(target: Target) {
    if (!selectedId) {
      return;
    }
    setActionError('');
    setNotice('');
    try {
      const res = await apiRequest(
        `/api/v1/groups/${selectedId}/members/${target.id}`,
        { method: 'DELETE' }
      );
      if (!res.ok) {
        setActionError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { group: GroupDetail };
      setDetail(data.group);
      setNotice(en.groups.noticeMemberRemoved);
      await loadGroups();
    } catch {
      setActionError(en.groups.genericError);
    }
  }

  async function onImport(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedId || importing || !csvFile) {
      return;
    }
    setActionError('');
    setNotice('');
    setImportFileError('');
    setImportResult(null);
    setImporting(true);
    try {
      const body = new FormData();
      body.append('file', csvFile);
      const res = await apiRequest(`/api/v1/groups/${selectedId}/import`, {
        method: 'POST',
        body,
      });
      if (!res.ok) {
        setImportFileError(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { group: GroupDetail; result: ImportResult };
      setDetail(data.group);
      setImportResult(data.result);
      setNotice(en.groups.noticeImported);
      setCsvFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await loadGroups();
    } catch {
      setImportFileError(en.groups.genericError);
    } finally {
      setImporting(false);
    }
  }

  const detailGroup = detail;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{en.groups.title}</h1>
          <p className="mt-1 max-w-prose text-sm text-muted-foreground">{en.groups.subtitle}</p>
        </div>
        <Button
          type="button"
          onClick={() => setShowNewGroup((open) => !open)}
          aria-expanded={showNewGroup}
          data-testid="new-group"
        >
          <Users aria-hidden="true" size={16} />
          {en.groups.newGroup}
        </Button>
      </div>

      {notice !== '' && (
        <p role="status" className="mb-4 text-sm font-medium text-success">
          {notice}
        </p>
      )}
      {actionError !== '' && (
        <Alert
          variant="danger"
          title={en.groups.actionErrorTitle}
          className="mb-4"
          data-testid="groups-action-error"
        >
          {actionError}
        </Alert>
      )}

      {showNewGroup && (
        <Card className="mb-6" data-testid="new-group-card">
          <CardHeader>
            <h2 className="text-xl font-semibold">{en.groups.createGroupTitle}</h2>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreateGroup} className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="group-name">{en.groups.nameLabel}</Label>
                <Input
                  id="group-name"
                  className="mt-1"
                  required
                  value={groupName}
                  placeholder={en.groups.namePlaceholder}
                  onChange={(e) => setGroupName(e.target.value)}
                  data-testid="group-name"
                />
              </div>
              <div>
                <Label htmlFor="group-department">{en.groups.departmentLabel}</Label>
                <Input
                  id="group-department"
                  className="mt-1"
                  value={department}
                  placeholder={en.groups.departmentPlaceholder}
                  onChange={(e) => setDepartment(e.target.value)}
                  data-testid="group-department"
                />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="group-description">{en.groups.descriptionLabel}</Label>
                <Input
                  id="group-description"
                  className="mt-1"
                  value={description}
                  placeholder={en.groups.descriptionPlaceholder}
                  onChange={(e) => setDescription(e.target.value)}
                  data-testid="group-description"
                />
              </div>
              <div className="md:col-span-2">
                <Button type="submit" disabled={creatingGroup} aria-busy={creatingGroup} data-testid="create-group">
                  {creatingGroup ? en.groups.creatingGroup : en.groups.createGroup}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="h-fit" data-testid="group-list">
          <CardHeader>
            <h2 className="text-lg font-semibold">{en.groups.groupListTitle}</h2>
          </CardHeader>
          <CardContent>
            {groupsLoading && (
              <p role="status" className="text-sm text-muted-foreground">
                {en.groups.groupsLoading}
              </p>
            )}
            {!groupsLoading && groupsError !== '' && (
              <Alert variant="danger" title={en.groups.groupsErrorTitle}>
                <p>{groupsError}</p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => void loadGroups()}
                >
                  {en.groups.retry}
                </Button>
              </Alert>
            )}
            {!groupsLoading && groupsError === '' && groups.length === 0 && (
              <div>
                <p className="font-medium">{en.groups.noGroupsTitle}</p>
                <p className="mt-1 text-sm text-muted-foreground">{en.groups.noGroupsBody}</p>
              </div>
            )}
            {!groupsLoading && groups.length > 0 && (
              <ul className="flex flex-col gap-2">
                {groups.map((group) => {
                  const selected = group.id === selectedId;
                  return (
                    <li key={group.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(group.id)}
                        aria-pressed={selected}
                        className={cn(
                          'w-full rounded-lg border px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                          selected
                            ? 'border-primary bg-primary-tint'
                            : 'border-border hover:bg-accent hover:text-accent-foreground'
                        )}
                        data-testid={`group-option-${group.id}`}
                      >
                        <span className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{group.name}</span>
                          {group.suppressed && (
                            <span className={cn(badgeVariants({ variant: 'outline' }), 'text-warning')}>
                              {en.groups.suppressedBadge}
                            </span>
                          )}
                        </span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {format(en.groups.memberCount, { count: group.member_count })} ·{' '}
                          {group.department || en.groups.departmentFallback}
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
          {!selectedId && !groupsLoading && groupsError === '' && (
            <Card>
              <CardContent>
                <p className="font-medium">{en.groups.noGroupsTitle}</p>
                <p className="mt-1 text-sm text-muted-foreground">{en.groups.noGroupsBody}</p>
              </CardContent>
            </Card>
          )}

          {selectedId && (
            <Card data-testid="group-detail">
              <CardHeader>
                {detailLoading && (
                  <p role="status" className="text-sm text-muted-foreground">
                    {en.groups.membersLoading}
                  </p>
                )}
                {!detailLoading && detailError !== '' && (
                  <Alert variant="danger" title={en.groups.membersErrorTitle}>
                    <p>{detailError}</p>
                  </Alert>
                )}
                {!detailLoading && detailGroup && (
                  <>
                    <h2 className="text-xl font-semibold">{detailGroup.name}</h2>
                    <CardDescription>
                      {format(en.groups.memberCount, { count: detailGroup.member_count })}
                      {' · '}
                      {detailGroup.department || en.groups.departmentFallback}
                    </CardDescription>
                  </>
                )}
              </CardHeader>
              {!detailLoading && detailGroup && (
                <CardContent>
                  {detailGroup.suppressed && (
                    <Alert
                      variant="warning"
                      title={en.groups.suppressedTitle}
                      className="mb-4"
                      data-testid="suppression-warning"
                    >
                      {format(en.groups.suppressedBody, {
                        count: detailGroup.member_count,
                        minimum: detailGroup.min_group_size,
                      })}
                    </Alert>
                  )}
                  <h3 className="mb-2 text-lg font-semibold">{en.groups.membersTitle}</h3>
                  {detailGroup.members.length === 0 ? (
                    <div className="rounded-lg border border-border p-4">
                      <p className="font-medium">{en.groups.emptyMembersTitle}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {en.groups.emptyMembersBody}
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-sm">
                        <caption className="sr-only">
                          {format(en.groups.memberCount, { count: detailGroup.member_count })}
                        </caption>
                        <thead>
                          <tr className="border-b border-border text-left">
                            <th scope="col" className="px-2 py-2 font-medium">
                              {en.groups.emailColumn}
                            </th>
                            <th scope="col" className="px-2 py-2 font-medium">
                              {en.groups.displayNameColumn}
                            </th>
                            <th scope="col" className="px-2 py-2 text-right font-medium">
                              {en.groups.actionsColumn}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {detailGroup.members.map((member) => (
                            <tr key={member.id} className="border-b border-border last:border-0">
                              <td className="px-2 py-2">{member.email}</td>
                              <td className="px-2 py-2">
                                {member.display_name || en.groups.noDisplayName}
                              </td>
                              <td className="px-2 py-2 text-right">
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => void onRemoveMember(member)}
                                  aria-label={format(en.groups.removeMember, {
                                    email: member.email,
                                  })}
                                >
                                  {en.groups.remove}
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          )}

          {selectedId && detailGroup && (
            <Card data-testid="add-user-card">
              <CardHeader>
                <h2 className="text-lg font-semibold">{en.groups.addUserTitle}</h2>
              </CardHeader>
              <CardContent>
                <form onSubmit={onAddMember} className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="member-email">{en.groups.emailLabel}</Label>
                    <Input
                      id="member-email"
                      type="email"
                      className="mt-1"
                      required
                      autoComplete="email"
                      placeholder={en.groups.emailPlaceholder}
                      value={memberEmail}
                      onChange={(e) => setMemberEmail(e.target.value)}
                      data-testid="member-email"
                    />
                  </div>
                  <div>
                    <Label htmlFor="member-name">{en.groups.displayNameLabel}</Label>
                    <Input
                      id="member-name"
                      className="mt-1"
                      placeholder={en.groups.displayNamePlaceholder}
                      value={memberName}
                      onChange={(e) => setMemberName(e.target.value)}
                      data-testid="member-name"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Button type="submit" disabled={addingMember} aria-busy={addingMember} data-testid="add-user">
                      {addingMember ? en.groups.addingUser : en.groups.addUser}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {selectedId && detailGroup && (
            <Card data-testid="import-card">
              <CardHeader>
                <h2 className="text-lg font-semibold">{en.groups.importTitle}</h2>
                <CardDescription>{en.groups.importHelp}</CardDescription>
              </CardHeader>
              <CardContent>
                <a
                  href="/api/v1/groups/import-template"
                  download
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-medium text-primary-strong underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <Upload aria-hidden="true" size={16} />
                  {en.groups.templateLabel}
                </a>
                <form onSubmit={onImport} className="mt-4 flex flex-col gap-4">
                  <div>
                    <Label htmlFor="csv-file">{en.groups.fileLabel}</Label>
                    <Input
                      id="csv-file"
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,text/csv"
                      className="mt-1"
                      onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                      data-testid="csv-file"
                    />
                  </div>
                  <div>
                    <Button
                      type="submit"
                      disabled={importing || !csvFile}
                      aria-busy={importing}
                      data-testid="import-csv"
                    >
                      {importing ? en.groups.importingCsv : en.groups.importCsv}
                    </Button>
                  </div>
                </form>

                {importFileError !== '' && (
                  <Alert
                    variant="danger"
                    title={en.groups.actionErrorTitle}
                    className="mt-4"
                    data-testid="import-file-error"
                  >
                    {importFileError}
                  </Alert>
                )}

                {importResult && (
                  <div className="mt-4" data-testid="import-result">
                    <p role="status" className="text-sm font-medium">
                      {format(en.groups.importSummary, {
                        imported: importResult.imported,
                        total: importResult.total,
                        skipped: importResult.skipped,
                      })}
                    </p>
                    {importResult.errors.length > 0 && (
                      <div className="mt-3">
                        <h3 className="mb-2 text-sm font-semibold">
                          {en.groups.importErrorsTitle}
                        </h3>
                        <div className="overflow-x-auto">
                          <table className="w-full border-collapse text-sm">
                            <caption className="sr-only">{en.groups.importErrorsTitle}</caption>
                            <thead>
                              <tr className="border-b border-border text-left">
                                <th scope="col" className="px-2 py-2 font-medium">
                                  {en.groups.rowColumn}
                                </th>
                                <th scope="col" className="px-2 py-2 font-medium">
                                  {en.groups.problemColumn}
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {importResult.errors.map((error, index) => (
                                <tr
                                  key={`${error.row}-${index}`}
                                  className="border-b border-border last:border-0"
                                >
                                  <td className="px-2 py-2">{error.row}</td>
                                  <td className="px-2 py-2">{error.message}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
