import { Outlet } from "react-router-dom";
import { ToastProvider } from "../components/ui/ToastProvider";
import Header from "./Header";

export default function AppShell() {
  return (
    <ToastProvider>
      <div className="app">
        <Header />
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </ToastProvider>
  );
}
