import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../../api/__mocks__/client";
import OntologyExplorer from "./OntologyExplorer";

vi.mock("../../api/client");

describe("OntologyExplorer", () => {
  beforeEach(() => {
    resetApiMock();
    api.getSchemaV2.mockResolvedValue({
      classes: [
        {
          iri: "urn:kg:class:Person",
          id: "Person",
          label: "人物",
          description: "人間を表す概念",
          aliases: [],
          examples: [],
          subclass_of: ["Agent"],
          equivalent_class: [],
          disjoint_with: [],
        },
      ],
      properties: [
        {
          iri: "urn:kg:property:name",
          id: "name",
          label: "名前",
          description: "",
          property_type: "DatatypeProperty",
          domain: ["Entity"],
          range: ["string"],
          sub_property_of: [],
          inverse_of: null,
          characteristics: ["FunctionalProperty"],
          editor_required: false,
          aliases: [],
        },
        {
          iri: "urn:kg:relationship:worksFor",
          id: "worksFor",
          label: "所属",
          description: "組織に所属",
          property_type: "ObjectProperty",
          domain: ["Person"],
          range: ["Organization"],
          sub_property_of: [],
          inverse_of: null,
          characteristics: [],
          editor_required: false,
          aliases: [],
        },
      ],
    });
    api.getConsistency.mockResolvedValue({ consistent: true, inconsistencies: [] });
  });

  it("shows class list and detail with v2 schema", async () => {
    render(<OntologyExplorer />);
    await waitFor(() => {
      expect(screen.getByTestId("ontology-explorer")).toBeInTheDocument();
      expect(screen.getByTestId("class-detail")).toBeInTheDocument();
      expect(screen.getByTestId("consistency-status")).toHaveTextContent("整合性: OK");
      expect(screen.getByRole("heading", { name: "Person" })).toBeInTheDocument();
    });
  });
});
