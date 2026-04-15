"use client";

import { useState } from "react";
import { DeckAppearance } from "../lib/api";

interface Props {
  results: DeckAppearance[];
}

type SortKey = "date" | "placement" | "format" | "deck" | "zone" | "copies";
type SortDir = "asc" | "desc";

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

const FORMAT_COLORS: Record<string, string> = {
  TCG: "bg-blue-500/15 text-blue-300",
  OCG: "bg-red-500/15 text-red-300",
  Genesys: "bg-green-500/15 text-green-300",
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

function formatBadge(format: string | null) {
  if (!format) return <span className="text-[#4A4A6A]">—</span>;
  const cls = FORMAT_COLORS[format] ?? "bg-[#2A2A4A] text-[#8888AA]";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {format}
    </span>
  );
}

function sortRows(rows: DeckAppearance[], key: SortKey, dir: SortDir): DeckAppearance[] {
  const factor = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    switch (key) {
      case "date":
        return factor * a.tournament_date.localeCompare(b.tournament_date);
      case "placement": {
        const rankA = PLACEMENT_ORDER[a.placement ?? ""] ?? 99;
        const rankB = PLACEMENT_ORDER[b.placement ?? ""] ?? 99;
        return factor * (rankA - rankB);
      }
      case "format":
        return factor * (a.format ?? "").localeCompare(b.format ?? "");
      case "deck":
        return factor * (a.deck_archetype ?? "").localeCompare(b.deck_archetype ?? "");
      case "zone":
        return factor * a.card_zone.localeCompare(b.card_zone);
      case "copies":
        return factor * (a.card_quantity - b.card_quantity);
      default:
        return 0;
    }
  });
}

interface HeaderProps {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onSort: (key: SortKey) => void;
}

function SortableHeader({ label, sortKey, current, dir, onSort }: HeaderProps) {
  const active = current === sortKey;
  return (
    <th
      className="px-4 py-3 font-medium cursor-pointer select-none whitespace-nowrap group"
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <span className={`text-xs transition ${active ? "text-[#C9A84C]" : "text-[#3A3A5A] group-hover:text-[#6B6B8A]"}`}>
          {active ? (dir === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </span>
    </th>
  );
}

export function TournamentTable({ results }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "copies" ? "desc" : "asc");
    }
  }

  const sorted = sortRows(results, sortKey, sortDir);

  return (
    <div className="overflow-x-auto rounded-xl border border-[#2A2A4A]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#2A2A4A] text-[#6B6B8A] text-left">
            <th className="px-4 py-3 font-medium">Tournament</th>
            <SortableHeader label="Date" sortKey="date" current={sortKey} dir={sortDir} onSort={handleSort} />
            <SortableHeader label="Placement" sortKey="placement" current={sortKey} dir={sortDir} onSort={handleSort} />
            <SortableHeader label="Format" sortKey="format" current={sortKey} dir={sortDir} onSort={handleSort} />
            <SortableHeader label="Deck" sortKey="deck" current={sortKey} dir={sortDir} onSort={handleSort} />
            <SortableHeader label="Zone" sortKey="zone" current={sortKey} dir={sortDir} onSort={handleSort} />
            <SortableHeader label="Copies" sortKey="copies" current={sortKey} dir={sortDir} onSort={handleSort} />
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
              <td className="px-4 py-3">{formatBadge(row.format)}</td>
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
