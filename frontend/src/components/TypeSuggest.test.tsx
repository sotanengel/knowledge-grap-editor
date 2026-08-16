import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../api/__mocks__/client";
import TypeSuggest from "./TypeSuggest";

vi.mock("../api/client");

describe("TypeSuggest", () => {
  beforeEach(() => {
    resetApiMock();
    api.suggestTypes.mockResolvedValue({
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
    });
  });

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

  it("displays label when value prop is set", async () => {
    render(<TypeSuggest value="Organization" onChange={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByRole("combobox")).toHaveValue("組織 (Organization)");
    });
  });

  it("selects with keyboard", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TypeSuggest value="" onChange={onChange} />);
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("組織 (Organization)"));
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith("Organization");
  });

  it("handles API failure without crashing", async () => {
    api.suggestTypes.mockRejectedValue(new Error("fail"));
    const user = userEvent.setup();
    render(<TypeSuggest value="" onChange={vi.fn()} />);
    await user.click(screen.getByRole("combobox"));
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("uses relationship suggest in relationship mode", async () => {
    api.suggestRelationships.mockResolvedValue({
      results: [{ id: "worksFor", label: "所属", description: "", score: 1 }],
    });
    const user = userEvent.setup();
    render(<TypeSuggest value="" onChange={vi.fn()} mode="relationship" />);
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(api.suggestRelationships).toHaveBeenCalled();
    });
  });
});
