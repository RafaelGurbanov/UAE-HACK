import { ShieldAlert } from 'lucide-react';
import { useT } from '../../i18n';
import { dimKey, layerKey, nodeKey } from '../../lib/labels';
import type { KBLayer, PipelineNode, ReadinessDimension } from '../../lib/types';

export function NodeBadges({ nodes }: { nodes: PipelineNode[] }) {
  const t = useT();
  return (
    <ul className="flex flex-wrap gap-2">
      {nodes.map((n) => (
        <li
          key={n}
          className="pill border border-gold/50 bg-gold/10 px-2.5 py-1 text-xs text-gold-ink"
          title={t(nodeKey(n))}
        >
          <span className="font-semibold">{n}</span> · {t(nodeKey(n))}
        </li>
      ))}
    </ul>
  );
}

export function DimensionBadges({ dims }: { dims: ReadinessDimension[] }) {
  const t = useT();
  return (
    <ul className="flex flex-wrap gap-2">
      {dims.map((d) => (
        <li key={d} className="pill border border-vio/40 bg-vio/10 px-2.5 py-1 text-xs text-tx">
          {t(dimKey(d))}
        </li>
      ))}
    </ul>
  );
}

const LAYER_STYLE: Record<KBLayer, string> = {
  uae_federal: 'border-teal/50 text-teal-ink',
  emirate: 'border-blu/50 text-blu-ink',
  global_example: 'border-vio/50 text-tx',
};

export function LayerPill({ layer }: { layer: KBLayer }) {
  const t = useT();
  return (
    <span className={`pill border px-2 py-0.5 text-[11px] ${LAYER_STYLE[layer]}`}>
      {t(layerKey(layer))}
    </span>
  );
}

export function RequiresDecision() {
  const t = useT();
  return (
    <p
      role="note"
      className="flex items-center gap-2 rounded-xl border border-amb/50 bg-amb/10 px-3 py-2 text-sm font-medium text-amb-ink"
    >
      <ShieldAlert size={16} aria-hidden /> {t('answer.requiresDecision')}
    </p>
  );
}
