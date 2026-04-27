import { useState, useMemo } from 'react';
import { Calendar } from 'lucide-react';

/**
 * useDateRangeFilter — small hook that filters an array by a date field.
 *
 * Returns: { filtered, FilterBar, range }
 *   - filtered: filtered + sorted-by-date-desc array
 *   - FilterBar: pre-built JSX of preset chips + custom date inputs
 *   - range: current selection key (for badges/labels)
 */
export function useDateRangeFilter(items, dateKey = 'created_at') {
  const [range, setRange] = useState('all');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const filtered = useMemo(() => {
    if (!Array.isArray(items)) return [];
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    let from = null;
    let to = null;
    switch (range) {
      case 'today':
        from = startOfToday;
        break;
      case '7d':
        from = new Date(startOfToday); from.setDate(from.getDate() - 6);
        break;
      case '30d':
        from = new Date(startOfToday); from.setDate(from.getDate() - 29);
        break;
      case '90d':
        from = new Date(startOfToday); from.setDate(from.getDate() - 89);
        break;
      case 'this_month':
        from = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      case 'last_month':
        from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        to = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      case 'this_year':
        from = new Date(now.getFullYear(), 0, 1);
        break;
      case 'custom':
        if (customFrom) from = new Date(customFrom);
        if (customTo) { to = new Date(customTo); to.setDate(to.getDate() + 1); }
        break;
      default:
        from = null;
    }

    const out = items.filter((it) => {
      const raw = it[dateKey];
      if (!raw) return false;
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) return false;
      if (from && d < from) return false;
      if (to && d >= to) return false;
      return true;
    });

    // Sort desc by date so paginated/long lists stay newest-first
    out.sort((a, b) => new Date(b[dateKey] || 0) - new Date(a[dateKey] || 0));
    return out;
  }, [items, dateKey, range, customFrom, customTo]);

  const presets = [
    { key: 'all', label: 'All' },
    { key: 'today', label: 'Today' },
    { key: '7d', label: '7 days' },
    { key: '30d', label: '30 days' },
    { key: '90d', label: '90 days' },
    { key: 'this_month', label: 'This Month' },
    { key: 'last_month', label: 'Last Month' },
    { key: 'this_year', label: 'This Year' },
    { key: 'custom', label: 'Custom' }
  ];

  const FilterBar = (
    <div className="flex flex-wrap items-center gap-2 mb-3" data-testid="date-range-filter">
      <Calendar className="w-4 h-4 text-slate-400" />
      {presets.map(p => (
        <button
          key={p.key}
          type="button"
          onClick={() => setRange(p.key)}
          data-testid={`date-filter-${p.key}`}
          className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
            range === p.key
              ? 'bg-sky-500 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {p.label}
        </button>
      ))}
      {range === 'custom' && (
        <div className="flex items-center gap-2 ml-1">
          <input
            type="date"
            value={customFrom}
            onChange={(e) => setCustomFrom(e.target.value)}
            className="rounded-md border border-slate-200 px-2 py-1 text-xs"
            data-testid="date-filter-from"
          />
          <span className="text-slate-400 text-xs">to</span>
          <input
            type="date"
            value={customTo}
            onChange={(e) => setCustomTo(e.target.value)}
            className="rounded-md border border-slate-200 px-2 py-1 text-xs"
            data-testid="date-filter-to"
          />
        </div>
      )}
      <span className="ml-auto text-xs text-slate-400" data-testid="date-filter-count">
        {filtered.length} entries
      </span>
    </div>
  );

  return { filtered, FilterBar, range };
}
