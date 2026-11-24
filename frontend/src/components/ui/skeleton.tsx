import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div aria-hidden="true" className={cn('skeleton rounded-md', className)} />;
}

interface SkeletonListProps {
  rows?: number;
  className?: string;
}

export function SkeletonList({ rows = 4, className }: SkeletonListProps) {
  return (
    <div aria-hidden="true" className={cn('space-y-2', className)}>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="rounded-lg border border-border p-4">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('flex h-56 items-end gap-2 rounded-lg border border-border p-4', className)}
    >
      {['h-2/5', 'h-2/3', 'h-1/2', 'h-4/5', 'h-3/5', 'h-full'].map((height, index) => (
        <Skeleton key={index} className={cn('flex-1', height)} />
      ))}
    </div>
  );
}
