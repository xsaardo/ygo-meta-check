const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CardSuggestion {
  id: number;
  name: string;
  type: string;
  image_url_small: string;
  archetype?: string;
}

export interface DeckAppearance {
  tournament_name: string;
  tournament_date: string;
  tournament_url: string;
  placement: string | null;
  player_name: string | null;
  deck_archetype: string | null;
  deck_url: string;
  card_zone: string;
  card_quantity: number;
  format: string | null;
}

export interface SearchResult {
  card_name: string;
  meta_relevant: boolean;
  total_appearances: number;
  results: DeckAppearance[];
}

export interface CardPrices {
  tcgplayer: string | null;
  cardmarket: string | null;
}

export interface Stats {
  tournament_count: number;
  deck_count: number;
  card_entry_count: number;
  oldest_tournament: string | null;
  newest_tournament: string | null;
}

export async function autocomplete(q: string): Promise<CardSuggestion[]> {
  if (q.length < 2) return [];
  const res = await fetch(`${API_URL}/api/autocomplete?q=${encodeURIComponent(q)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function searchCard(
  cardName: string,
  months = 3,
  zone?: string
): Promise<SearchResult | null> {
  const params = new URLSearchParams({ card: cardName, months: String(months) });
  if (zone) params.set("zone", zone);
  const res = await fetch(`${API_URL}/api/search?${params}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getCardPrices(cardId: number): Promise<CardPrices | null> {
  const res = await fetch(`${API_URL}/api/prices/${cardId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getStats(): Promise<Stats | null> {
  const res = await fetch(`${API_URL}/api/stats`, { next: { revalidate: 300 } });
  if (!res.ok) return null;
  return res.json();
}
