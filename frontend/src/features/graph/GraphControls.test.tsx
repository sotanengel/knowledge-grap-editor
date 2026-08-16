import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import GraphControls from "./GraphControls";

describe("GraphControls", () => {
  it("calls zoom and layout handlers", async () => {
    const onZoomIn = vi.fn();
    const onZoomOut = vi.fn();
    const onFit = vi.fn();
    const onLayoutChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GraphControls
        layout="force"
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
        onFit={onFit}
        onLayoutChange={onLayoutChange}
      />,
    );
    await user.click(screen.getByLabelText("Zoom in"));
    expect(onZoomIn).toHaveBeenCalled();
    await user.selectOptions(screen.getByLabelText("Layout"), "hierarchical");
    expect(onLayoutChange).toHaveBeenCalledWith("hierarchical");
  });
});
