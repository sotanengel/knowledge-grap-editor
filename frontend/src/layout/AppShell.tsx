import { Outlet } from "react-router-dom";
import Header from "./Header";

export default function AppShell() {
  return (
    <div className="app">
      <Header />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
