import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { CheckCircle2, Info, ShieldAlert, TriangleAlert } from 'lucide-react';

import { cn } from '@/lib/utils';

const alertVariants = cva(
  'flex w-full flex-col gap-1 rounded-lg border p-4 text-sm [&>svg]:h-5 [&>svg]:w-5 [&>svg]:shrink-0',
  {
    variants: {
      variant: {
        info: 'border-border bg-background text-foreground',
        success: 'border-success bg-success-tint text-foreground [&>svg]:text-success',
        warning: 'border-warning bg-warning-tint text-foreground [&>svg]:text-warning',
        danger: 'border-danger bg-danger-tint text-foreground [&>svg]:text-danger',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  }
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title: string;
  hideIcon?: boolean;
}

const alertVariantsIcons: Record<NonNullable<AlertProps['variant']>, React.ComponentType> = {
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
  danger: ShieldAlert,
};

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, title, hideIcon, children, ...props }, ref) => {
    const Icon = alertVariantsIcons[variant ?? 'info'];
    return (
      <div
        ref={ref}
        role="alert"
        tabIndex={-1}
        className={cn(alertVariants({ variant, className }))}
        {...props}
      >
        {!hideIcon && <Icon aria-hidden="true" />}
        <div className="text-left">
          <p className="font-medium">{title}</p>
          {children && <div className="text-muted-foreground">{children}</div>}
        </div>
      </div>
    );
  }
);
Alert.displayName = 'Alert';

export { Alert, alertVariants };
