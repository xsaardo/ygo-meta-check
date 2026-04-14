import { DeckAppearance } from "../lib/api";

interface Props {
  results: DeckAppearance[];
}

const ZONE_LABELS: Record<string, string> = {
  main: "Main",
  extra: "Extra",
  side: "Side",
};

const PLACEMENT_ORDER: Record<string, number> = {
  Winner: 1,
  "Runner-Up": 2,
  "Top 4": 3,
  "Top 8": 4,
  "Top 16": 5,
  "Top 32": 6,
};

function placementBadge(placement: string | null) {
  if (!placement) return null;
  const colors: Record<string, string> = {
    Winner: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
    "Runner-Up": "bg-slate-400/20 text-slate-300 border-slate-400/40",
    "Top 4": "bg-orange-500/20 text-orange-400 border-orange-500/40",
    "Top 8": "bg-blue-500/20 text-blue-400 border-blue-500/40",
  };
  const cls = colors[placement] ?? "bg-[#2A2A4A] text-[#8888AA] border-[#3A3A5A]";
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full border text-xs font-medium ${cls}`}>
      {placement}
    </span>
  );
}

function zoneBadge(zone: string) {
  const colors: Record<string, string> = {
    main: "bg-blue-500/15 text-blue-300",
    extra: "bg-purple-500/15 text-purple-300",
    side: "bg-slate-500/15 text-slate-300",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[zone] ?? ""}`}>
      {ZONE_LABELS[zone] ?? zone}
    </span>
  );
}

export function TournamentTable({ results }: Props) {
  const sorted = [...results].sort((a, b) => {
    // Primary: placement rank, secondary: date desc
    const rankA = PLACEMENT_ORDER[a.placement ?? ""] ?? 99;
    const rankB = PLACEMENT_ORDER[b.placement ?? ""] ?? 99;
    if (rankA !== rankB) return rankA - rankB;
    return b.tournament_date.localeCompare(a.tournament_date);
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-[#2A2A4A]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#2A2A4A] text-[#6B6B8A] text-left">
            <th className="px-4 py-3 font-medium">Tournament</th>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 font-medium">Placement</th>
            <th className="px-4 py-3 font-medium">Deck</th>
            <th className="px-4 py-3 font-medium">Zone</th>
            <th className="px-4 py-3 font-medium">Copies</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[#1E1E35] hover:bg-[#1A1A2E] transition"
            >
              <td className="px-4 py-3">
                <a
                  href={row.tournament_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#C9A84C] hover:underline font-medium"
                >
                  {row.tournament_name}
                </a>
              </td>
              <td className="px-4 py-3 text-[#8888AA] whitespace-nowrap">
                {new Date(row.tournament_date).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </td>
              <td className="px-4 py-3">{placementBadge(row.placement)}</td>
              <td className="px-4 py-3">
                <a
                  href={row.deck_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white hover:text-[#C9A84C] transition flex items-center gap-1"
                >
                  {row.deck_archetype ?? "Unknown"}
                  <span className="text-[#6B6B8A] text-xs">↗</span>
                </a>
              </td>
              <td className="px-4 py-3">{zoneBadge(row.card_zone)}</td>
              <td className="px-4 py-3 text-center">
                <span className="font-mono font-bold text-white">×{row.card_quantity}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
