import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./layout/AppShell";
import GraphPage from "./pages/GraphPage";
import OntologyPage from "./pages/OntologyPage";
import SearchPage from "./pages/SearchPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<GraphPage />} />
        <Route path="/browse" element={<Navigate to="/" replace />} />
        <Route path="/register" element={<Navigate to="/" replace />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/ontology" element={<OntologyPage />} />
      </Route>
    </Routes>
  );
}
