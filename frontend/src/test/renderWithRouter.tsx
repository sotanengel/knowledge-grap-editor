import type { ReactElement } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter, type MemoryRouterProps } from "react-router-dom";

interface Options extends Omit<RenderOptions, "wrapper"> {
  routerProps?: MemoryRouterProps;
}

export function renderWithRouter(ui: ReactElement, options: Options = {}) {
  const { routerProps, ...renderOptions } = options;
  return render(ui, {
    wrapper: ({ children }) => (
      <MemoryRouter {...routerProps}>{children}</MemoryRouter>
    ),
    ...renderOptions,
  });
}
