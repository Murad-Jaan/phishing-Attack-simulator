import * as React from 'react';
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from 'lucide-react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const alertVariants = cva('flex w-full gap-3 rounded-lg border p-4 text-sm', {
  variants: {
    variant: {
      info: 'border-border bg-surface-muted text-foreground',
      success: 'border-success-tint-border bg-success-tint text-foreground',
      warning: 'border-warning-tint-border bg-warning-tint text-foreground',
      danger: 'border-danger-tint-border bg-danger-tint text-foreground',
    },
  },
  defaultVariants: {
    variant: 'info',
  },
});

export const alertVariantsIcons = {
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
  danger: AlertCircle,
} as const;

type AlertVariant = NonNullable<VariantProps<typeof alertVariants>['variant']>;

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title: string;
}

const iconTone: Record<AlertVariant, string> = {
  info: 'text-primary-strong',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger-strong',
};

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = 'info', title, children, ...props }, ref) => {
    const Icon = alertVariantsIcons[variant ?? 'info'];
    return (
      <div
        ref={ref}
        role="alert"
        className={cn(alertVariants({ variant }), className)}
        {...props}
      >
        <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', iconTone[variant ?? 'info'])} aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <p className="font-semibold leading-5 text-foreground">{title}</p>
          <div className="text-sm leading-5 text-muted-foreground">{children}</div>
        </div>
      </div>
    );
  },
);
Alert.displayName = 'Alert';

export { Alert };
