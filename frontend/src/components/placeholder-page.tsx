import type { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/page-header';
import { en } from '@/content/en';

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

export function PlaceholderPage({ title, description, icon: Icon }: PlaceholderPageProps) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <span
            className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-tint text-primary-strong"
            aria-hidden="true"
          >
            <Icon className="h-6 w-6" />
          </span>
          <h2 className="text-lg font-semibold leading-7 text-foreground">
            {en.placeholder.title}
          </h2>
          <p className="max-w-md text-sm leading-6 text-muted-foreground">{en.placeholder.body}</p>
        </CardContent>
      </Card>
    </>
  );
}
