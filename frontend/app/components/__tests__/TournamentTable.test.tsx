import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TournamentTable } from "../TournamentTable";
import type { DeckAppearance } from "../../lib/api";

const BASE_ROW: DeckAppearance = {
  tournament_name: "YCS Test",
  tournament_date: "2024-01-15",
  tournament_url: "https://ygoprodeck.com/tournament/ycs-test",
  placement: "Top 8",
  player_name: "Player One",
  deck_archetype: "Dark Magician",
  deck_url: "https://ygoprodeck.com/deck/dark-magician-abc123",
  card_zone: "main",
  card_quantity: 3,
  format: "TCG",
};

describe("TournamentTable — deck_url security (L4)", () => {
  it("renders a clickable link for a valid ygoprodeck.com deck_url", () => {
    render(<TournamentTable results={[BASE_ROW]} />);

    const link = screen.getByRole("link", { name: /dark magician/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", BASE_ROW.deck_url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders plain text (no link) for a deck_url with a non-ygoprodeck.com host", () => {
    const row = { ...BASE_ROW, deck_url: "https://attacker.example.com/evil" };
    render(<TournamentTable results={[row]} />);

    expect(screen.queryByRole("link", { name: /dark magician/i })).toBeNull();
    expect(screen.getByText("Dark Magician")).toBeInTheDocument();
  });

  it("renders plain text for a javascript: URI in deck_url", () => {
    const row = { ...BASE_ROW, deck_url: "javascript:alert(document.cookie)" };
    render(<TournamentTable results={[row]} />);

    expect(screen.queryByRole("link", { name: /dark magician/i })).toBeNull();
    expect(screen.getByText("Dark Magician")).toBeInTheDocument();
  });

  it("renders plain text for a data: URI in deck_url", () => {
    const row = { ...BASE_ROW, deck_url: "data:text/html,<script>alert(1)</script>" };
    render(<TournamentTable results={[row]} />);

    expect(screen.queryByRole("link", { name: /dark magician/i })).toBeNull();
    expect(screen.getByText("Dark Magician")).toBeInTheDocument();
  });

  it("falls back to 'Unknown' when deck_archetype is null and deck_url is unsafe", () => {
    const row = {
      ...BASE_ROW,
      deck_archetype: null,
      deck_url: "https://attacker.example.com/evil",
    };
    render(<TournamentTable results={[row]} />);

    // The tournament_name link is still present, but no link wraps "Unknown"
    expect(screen.queryByRole("link", { name: /unknown/i })).toBeNull();
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });
});
