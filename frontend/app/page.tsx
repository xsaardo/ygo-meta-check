"use client";

import Image from "next/image";
import { useState } from "react";
import { CardSearch } from "./components/CardSearch";
import { MetaBadge } from "./components/MetaBadge";
import { TournamentTable } from "./components/TournamentTable";
import { CardSuggestion, SearchResult, searchCard } from "./lib/api";

const MONTH_OPTIONS = [1, 2, 3, 6] as const;
const ZONE_OPTIONS = [
  { value: "", label: "All Zones" },
  { value: "main", label: "Main Deck" },
  { value: "extra", label: "Extra Deck" },
  { value: "side", label: "Side Deck" },
];

export default function HomePage() {
  const [selectedCard, setSelectedCard] = useState<CardSuggestion | null>(null);
  const [months, setMonths] = useState(3);
  const [zone, setZone] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCardSelect(card: CardSuggestion) {
    setSelectedCard(card);
    setError(null);
    setIsLoading(true);
    try {
      const data = await searchCard(card.name, months, zone || undefined);
      if (!data) throw new Error("Search failed");
      setResult(data);
    } catch {
      setError("Failed to fetch results. Is the backend running?");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function refetch(newMonths = months, newZone = zone) {
    if (!selectedCard) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await searchCard(selectedCard.name, newMonths, newZone || undefined);
      if (!data) throw new Error("Search failed");
      setResult(data);
    } catch {
      setError("Failed to fetch results.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-12 md:py-20">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-3 tracking-tight">
          ⚡ YGO Meta Check
        </h1>
        <p className="text-[#6B6B8A] text-lg max-w-xl mx-auto">
          Search any card to see if it has tournament meta relevance in the last{" "}
          {months} months.
        </p>
      </div>

      {/* Search */}
      <CardSearch onSelect={handleCardSelect} isLoading={isLoading} />

      {/* Filters */}
      <div className="flex flex-wrap justify-center gap-3 mt-6">
        {/* Month filter */}
        <div className="flex items-center gap-2 bg-[#1A1A2E] border border-[#2A2A4A] rounded-lg px-3 py-2">
          <span className="text-[#6B6B8A] text-sm">Last</span>
          {MONTH_OPTIONS.map((m) => (
            <button
              key={m}
              onClick={() => {
                setMonths(m);
                refetch(m, zone);
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition ${
                months === m
                  ? "bg-[#C9A84C] text-black"
                  : "text-[#8888AA] hover:text-white"
              }`}
            >
              {m}mo
            </button>
          ))}
        </div>

        {/* Zone filter */}
        <div className="flex items-center gap-1 bg-[#1A1A2E] border border-[#2A2A4A] rounded-lg px-2 py-2">
          {ZONE_OPTIONS.map((z) => (
            <button
              key={z.value}
              onClick={() => {
                setZone(z.value);
                refetch(months, z.value);
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition ${
                zone === z.value
                  ? "bg-[#2A2A4A] text-white"
                  : "text-[#8888AA] hover:text-white"
              }`}
            >
              {z.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="max-w-2xl mx-auto mt-8 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm text-center">
          {error}
        </div>
      )}

      {/* Results */}
      {result && selectedCard && (
        <div className="max-w-5xl mx-auto mt-10 space-y-6">
          {/* Card identity */}
          <div className="flex items-start gap-5 p-5 rounded-xl bg-[#1A1A2E] border border-[#2A2A4A]">
            <Image
              src={selectedCard.image_url_small}
              alt={selectedCard.name}
              width={60}
              height={88}
              className="rounded-md flex-shrink-0 shadow-lg"
            />
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-white">{result.card_name}</h2>
              <div className="text-[#6B6B8A] text-sm">{selectedCard.type}</div>
              <MetaBadge relevant={result.meta_relevant} count={result.total_appearances} />
            </div>
          </div>

          {/* Table */}
          {result.results.length > 0 ? (
            <TournamentTable results={result.results} />
          ) : (
            <div className="text-center py-16 text-[#6B6B8A]">
              <div className="text-5xl mb-4">🃏</div>
              <p className="text-lg">No confirmed tournament decklists found for this card.</p>
              <p className="text-sm mt-2 max-w-md mx-auto">
                This card may be played in tournaments where decklists weren't submitted to
                YGOPRODeck, or it may genuinely not be in the current meta.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !isLoading && !error && (
        <div className="text-center mt-20 text-[#6B6B8A]">
          <div className="text-6xl mb-4">🔍</div>
          <p className="text-lg">Type a card name to check its meta relevance</p>
          <p className="text-sm mt-1">Data sourced from ygoprodeck.com tournament decklists</p>
        </div>
      )}
    </main>
  );
}
