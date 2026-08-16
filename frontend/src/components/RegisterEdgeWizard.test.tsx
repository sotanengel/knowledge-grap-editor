import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../api/__mocks__/client";
import RegisterEdgeWizard from "./RegisterEdgeWizard";
import { renderWithRouter } from "../test/renderWithRouter";

vi.mock("../api/client");

describe("RegisterEdgeWizard", () => {
  beforeEach(() => {
    resetApiMock();
    api.listNodes.mockResolvedValue([
      { id: "p1", label: "山田", type: "Person", properties: {} },
      { id: "o1", label: "Apple", type: "Organization", properties: {} },
    ]);
    api.listRelationships.mockResolvedValue([
      { id: "worksFor", label: "所属", description: "", domain: ["Person"], range: ["Organization"], aliases: [] },
    ]);
    api.suggestRelationships.mockResolvedValue({
      results: [{ id: "worksFor", label: "所属", description: "", score: 1 }],
    });
    api.createEdge.mockResolvedValue({
      id: "e1",
      subject: "p1",
      predicate: "worksFor",
      object: "o1",
      properties: {},
    });
  });

  it("shows load error when nodes cannot be fetched", async () => {
    api.listNodes.mockRejectedValue(new Error("接続失敗"));
    renderWithRouter(<RegisterEdgeWizard />);
    await waitFor(() => {
      expect(screen.getByText("接続失敗")).toBeInTheDocument();
    });
  });

  it("completes edge registration flow", async () => {
    const user = userEvent.setup();
    renderWithRouter(<RegisterEdgeWizard />);
    await waitFor(() => screen.getByText("山田"));
    await user.click(screen.getByText("山田"));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("worksFor"));
    await user.click(screen.getByText("worksFor"));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await waitFor(() => screen.getByText("Apple"));
    await user.click(screen.getByText("Apple"));
    await user.click(screen.getByRole("button", { name: "次へ" }));
    await user.click(screen.getByRole("button", { name: "登録する" }));
    await waitFor(() => {
      expect(api.createEdge).toHaveBeenCalled();
    });
    expect(screen.getByText("関係の登録が完了しました")).toBeInTheDocument();
  });
});
