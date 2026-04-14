"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { autocomplete, CardSuggestion } from "../lib/api";

interface Props {
  onSelect: (card: CardSuggestion) => void;
  isLoading: boolean;
}

export function CardSearch({ onSelect, isLoading }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<CardSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current);
    if (query.length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    debounce.current = setTimeout(async () => {
      const results = await autocomplete(query);
      setSuggestions(results);
      setOpen(results.length > 0);
      setActiveIdx(-1);
    }, 250);
    return () => {
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      selectCard(suggestions[activeIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  function selectCard(card: CardSuggestion) {
    setQuery(card.name);
    setOpen(false);
    setSuggestions([]);
    onSelect(card);
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl mx-auto">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="Search a card name… (e.g. Ash Blossom & Joyous Spring)"
          disabled={isLoading}
          className="w-full px-5 py-4 pr-12 rounded-xl bg-[#1A1A2E] border border-[#2A2A4A] text-white placeholder-[#6B6B8A] text-lg focus:outline-none focus:border-[#C9A84C] focus:ring-1 focus:ring-[#C9A84C] transition disabled:opacity-50"
        />
        {isLoading ? (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="w-5 h-5 border-2 border-[#C9A84C] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : query ? (
          <button
            onClick={() => { setQuery(""); setSuggestions([]); setOpen(false); }}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B6B8A] hover:text-white transition"
          >
            ✕
          </button>
        ) : (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B6B8A] text-xl">⚡</span>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 w-full mt-2 rounded-xl bg-[#1A1A2E] border border-[#2A2A4A] overflow-hidden shadow-2xl">
          {suggestions.map((card, idx) => (
            <li
              key={card.id}
              onMouseDown={() => selectCard(card)}
              onMouseEnter={() => setActiveIdx(idx)}
              className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition ${
                idx === activeIdx ? "bg-[#2A2A4A]" : "hover:bg-[#222238]"
              }`}
            >
              <Image
                src={card.image_url_small}
                alt={card.name}
                width={36}
                height={52}
                className="rounded object-cover flex-shrink-0"
              />
              <div>
                <div className="text-white font-medium">{card.name}</div>
                <div className="text-[#6B6B8A] text-sm">{card.type}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
