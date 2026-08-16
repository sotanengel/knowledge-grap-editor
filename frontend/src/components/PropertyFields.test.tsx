import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../api/__mocks__/client";
import PropertyFields from "./PropertyFields";

const onChange = vi.fn();

vi.mock("../api/client");

describe("PropertyFields", () => {
  beforeEach(() => {
    resetApiMock();
    onChange.mockClear();
  });

  it("shows hint when no class selected", () => {
    render(<PropertyFields classId="" values={{}} onChange={onChange} />);
    expect(screen.getByText(/型を選択すると/)).toBeInTheDocument();
  });

  it("renders properties from API", async () => {
    api.getClassProperties.mockResolvedValue([
      { id: "name", label: "名前", description: "名称", domain: [], range: [], required: true, aliases: [] },
    ]);
    render(<PropertyFields classId="Person" values={{}} onChange={onChange} />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText("名称")).toBeInTheDocument();
    });
  });

  it("shows error when API fails", async () => {
    api.getClassProperties.mockRejectedValue(new Error("取得失敗"));
    render(<PropertyFields classId="Person" values={{}} onChange={onChange} />);
    await waitFor(() => {
      expect(screen.getByText("取得失敗")).toBeInTheDocument();
    });
  });

  it("shows hint when no properties defined", async () => {
    api.getClassProperties.mockResolvedValue([]);
    render(<PropertyFields classId="Person" values={{}} onChange={onChange} />);
    await waitFor(() => {
      expect(screen.getByText(/属性はありません/)).toBeInTheDocument();
    });
  });

  it("calls onChange when field edited", async () => {
    api.getClassProperties.mockResolvedValue([
      { id: "name", label: "名前", description: "", domain: [], range: [], required: false, aliases: [] },
    ]);
    const user = userEvent.setup();
    render(<PropertyFields classId="Person" values={{}} onChange={onChange} />);
    await waitFor(() => screen.getByPlaceholderText("name"));
    await user.type(screen.getByPlaceholderText("name"), "山田");
    expect(onChange).toHaveBeenCalled();
  });
});
