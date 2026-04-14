interface Props {
  relevant: boolean;
  count: number;
}

export function MetaBadge({ relevant, count }: Props) {
  if (relevant) {
    return (
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-semibold text-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          META RELEVANT
        </span>
        <span className="text-[#6B6B8A] text-sm">
          Found in <span className="text-white font-medium">{count}</span> tournament deck{count !== 1 ? "s" : ""}
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-3">
      <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/20 border border-red-500/40 text-red-400 font-semibold text-sm">
        <span className="w-2 h-2 rounded-full bg-red-400" />
        NOT IN RECENT META
      </span>
      <span className="text-[#6B6B8A] text-sm">No tournament appearances found</span>
    </div>
  );
}
