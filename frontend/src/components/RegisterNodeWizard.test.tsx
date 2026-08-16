import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../api/__mocks__/client";
import RegisterNodeWizard from "./RegisterNodeWizard";
import { renderWithRouter } from "../test/renderWithRouter";

vi.mock("../api/client");

describe("RegisterNodeWizard", () => {
  beforeEach(() => {
    resetApiMock();
    api.suggestTypes.mockResolvedValue({
      results: [{ id: "Organization", label: "組織", description: "", score: 1 }],
    });
    api.getClassProperties.mockResolvedValue([
      { id: "name", label: "名前", description: "", domain: [], range: [], required: false, aliases: [] },
    ]);
    api.createNode.mockResolvedValue({
      id: "ontology",
      label: "オントロジー",
      type: "Organization",
      properties: {},
    });
  });

  it("enables next immediately after label input with sync id preview", async () => {
    const user = userEvent.setup();
    renderWithRouter(<RegisterNodeWizard />);
    await user.type(screen.getByPlaceholderText("例: Apple"), "オントロジー");
    expect(screen.getByText("オントロジー", { selector: "code" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "次へ" })).toBeEnabled();
  });

  it("allows next when listNodes fails", async () => {
    api.listNodes.mockRejectedValue(new Error("network"));
    const user = userEvent.setup();
    renderWithRouter(<RegisterNodeWizard />);
    await user.type(screen.getByPlaceholderText("例: Apple"), "テスト");
    await waitFor(() => {
      expect(screen.getByText(/重複チェックできませんでした/)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "次へ" })).toBeEnabled();
  });

  it("completes full registration flow", async () => {
    const user = userEvent.setup();
    renderWithRouter(<RegisterNodeWizard />);
    await user.type(screen.getByPlaceholderText("例: Apple"), "Apple");
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("Organization"));
    await user.click(screen.getByText("Organization"));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("button", { name: "登録する" }));
    await waitFor(() => {
      expect(api.createNode).toHaveBeenCalledWith(
        expect.objectContaining({ label: "Apple", type: "Organization" }),
      );
    });
    expect(screen.getByText("登録が完了しました")).toBeInTheDocument();
  });

  it("shows error when createNode fails", async () => {
    api.createNode.mockRejectedValue(new Error("保存エラー"));
    const user = userEvent.setup();
    renderWithRouter(<RegisterNodeWizard />);
    await user.type(screen.getByPlaceholderText("例: Apple"), "Apple");
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("Organization"));
    await user.click(screen.getByText("Organization"));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("button", { name: "登録する" }));
    await waitFor(() => {
      expect(screen.getByText("保存エラー")).toBeInTheDocument();
    });
  });
});
