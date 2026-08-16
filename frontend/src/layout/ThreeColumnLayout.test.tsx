import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ThreeColumnLayout from "./ThreeColumnLayout";

describe("ThreeColumnLayout", () => {
  it("renders left, center, and right panes", () => {
    render(
      <ThreeColumnLayout
        left={<div>Left Pane</div>}
        center={<div>Center Pane</div>}
        right={<div>Right Pane</div>}
      />,
    );
    expect(screen.getByTestId("pane-left")).toBeInTheDocument();
    expect(screen.getByTestId("pane-center")).toBeInTheDocument();
    expect(screen.getByTestId("pane-right")).toBeInTheDocument();
    expect(screen.getByText("Left Pane")).toBeInTheDocument();
    expect(screen.getByText("Center Pane")).toBeInTheDocument();
    expect(screen.getByText("Right Pane")).toBeInTheDocument();
  });
});
