import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../../api/__mocks__/client";
import OntologyExplorer from "./OntologyExplorer";

vi.mock("../../api/client");

describe("OntologyExplorer", () => {
  beforeEach(() => {
    resetApiMock();
    api.listClasses.mockResolvedValue([
      {
        id: "Person",
        label: "人物",
        description: "人間を表す概念",
        aliases: [],
        parent_classes: [],
        examples: [],
      },
    ]);
    api.listRelationships.mockResolvedValue([
      {
        id: "worksFor",
        label: "所属",
        description: "組織に所属",
        domain: ["Person"],
        range: ["Organization"],
        aliases: [],
      },
    ]);
    api.getClassProperties.mockResolvedValue([
      { id: "name", label: "名前", description: "", domain: [], range: [], required: true, aliases: [] },
    ]);
  });

  it("shows class list and detail", async () => {
    render(<OntologyExplorer />);
    await waitFor(() => {
      expect(screen.getByTestId("ontology-explorer")).toBeInTheDocument();
      expect(screen.getByTestId("class-detail")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Person" })).toBeInTheDocument();
    });
  });
});
