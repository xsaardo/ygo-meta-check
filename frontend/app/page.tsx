"use client";

import Image from "next/image";
import { useState } from "react";
import { CardSearch } from "./components/CardSearch";
import { MetaBadge } from "./components/MetaBadge";
import { TournamentTable } from "./components/TournamentTable";
import { CardPrices, CardSuggestion, SearchResult, getCardPrices, searchCard } from "./lib/api";

const MONTH_OPTIONS = [1, 2, 3, 6] as const;

// Extra deck card types — all others belong to the main deck
const EXTRA_DECK_TYPES = new Set([
  "Fusion Monster",
  "Synchro Monster",
  "XYZ Monster",
  "Link Monster",
  "Pendulum Effect Fusion Monster",
  "Synchro Pendulum Effect Monster",
  "XYZ Pendulum Effect Monster",
  "Pendulum Flip Effect Monster",
]);

function detectZone(type: string): "main" | "extra" {
  return EXTRA_DECK_TYPES.has(type) ? "extra" : "main";
}

const ZONE_OVERRIDES = [
  { value: "side", label: "Side Deck" },
  { value: "", label: "All Zones" },
] as const;

export default function HomePage() {
  const [selectedCard, setSelectedCard] = useState<CardSuggestion | null>(null);
  const [months, setMonths] = useState(3);
  // null = auto-detect from card type; explicit string = user override
  const [zoneOverride, setZoneOverride] = useState<string | null>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [prices, setPrices] = useState<CardPrices | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function effectiveZone(card: CardSuggestion | null, override: string | null): string | undefined {
    if (override !== null) return override || undefined;
    if (!card) return undefined;
    return detectZone(card.type);
  }

  async function handleCardSelect(card: CardSuggestion) {
    setSelectedCard(card);
    setZoneOverride(null); // reset to auto on new card
    setError(null);
    setIsLoading(true);
    setPrices(null);
    try {
      const zone = effectiveZone(card, null);
      const [data, priceData] = await Promise.all([
        searchCard(card.name, months, zone),
        getCardPrices(card.id),
      ]);
      if (!data) throw new Error("Search failed");
      setResult(data);
      setPrices(priceData);
    } catch {
      setError("Failed to fetch results. Is the backend running?");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function refetch(newMonths = months, newOverride = zoneOverride) {
    if (!selectedCard) return;
    setIsLoading(true);
    setError(null);
    try {
      const zone = effectiveZone(selectedCard, newOverride);
      const data = await searchCard(selectedCard.name, newMonths, zone);
      if (!data) throw new Error("Search failed");
      setResult(data);
    } catch {
      setError("Failed to fetch results.");
    } finally {
      setIsLoading(false);
    }
  }

  const autoZoneLabel = selectedCard
    ? detectZone(selectedCard.type) === "extra" ? "Extra Deck" : "Main Deck"
    : "Auto";

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
                refetch(m, zoneOverride);
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
          {/* Auto button — shows detected deck type */}
          <button
            onClick={() => {
              setZoneOverride(null);
              refetch(months, null);
            }}
            className={`px-3 py-1 rounded text-sm font-medium transition ${
              zoneOverride === null
                ? "bg-[#2A2A4A] text-white"
                : "text-[#8888AA] hover:text-white"
            }`}
          >
            {autoZoneLabel}
          </button>

          {/* Manual overrides */}
          {ZONE_OVERRIDES.map((z) => (
            <button
              key={z.value}
              onClick={() => {
                setZoneOverride(z.value);
                refetch(months, z.value);
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition ${
                zoneOverride === z.value
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
              {prices && (prices.tcgplayer || prices.cardmarket) && (
                <div className="flex flex-wrap gap-3 pt-1">
                  {prices.tcgplayer && (
                    <span className="text-xs text-[#8888AA]">
                      TCGPlayer{" "}
                      <span className="text-white font-medium">${prices.tcgplayer}</span>
                    </span>
                  )}
                  {prices.cardmarket && (
                    <span className="text-xs text-[#8888AA]">
                      Cardmarket{" "}
                      <span className="text-white font-medium">€{prices.cardmarket}</span>
                    </span>
                  )}
                </div>
              )}
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
