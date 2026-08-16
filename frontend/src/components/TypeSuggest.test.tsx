import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import TypeSuggest from "./TypeSuggest";

vi.mock("../api/client", () => ({
  api: {
    suggestTypes: vi.fn().mockResolvedValue({
      results: [
        {
          id: "Organization",
          label: "組織",
          description: "組織・企業",
          score: 0.9,
          examples: ["Apple"],
        },
        {
          id: "Product",
          label: "製品",
          description: "製品",
          score: 0.5,
          examples: [],
        },
      ],
    }),
    suggestRelationships: vi.fn().mockResolvedValue({ results: [] }),
  },
}));

describe("TypeSuggest", () => {
  it("shows suggestions on focus with empty query", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TypeSuggest value="" onChange={onChange} />);
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(screen.getByText("組織 (Organization)")).toBeInTheDocument();
    });
  });

  it("displays Japanese label after selection", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TypeSuggest value="" onChange={onChange} />);
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("組織 (Organization)"));
    await user.click(screen.getByText("組織 (Organization)"));
    expect(onChange).toHaveBeenCalledWith("Organization");
  });
});
