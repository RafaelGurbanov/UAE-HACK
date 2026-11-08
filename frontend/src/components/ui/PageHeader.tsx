import type { ReactNode } from 'react';

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl text-tx sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-mut">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}
