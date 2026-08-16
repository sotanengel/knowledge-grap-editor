import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import BrowsePage from "./pages/BrowsePage";
import HomePage from "./pages/HomePage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  return (
    <div className="app">
      <Header />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/browse" element={<BrowsePage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </div>
  );
}
