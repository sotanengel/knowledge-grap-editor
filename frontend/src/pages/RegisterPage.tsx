import { useState } from "react";
import RegisterEdgeWizard from "../components/RegisterEdgeWizard";
import RegisterNodeWizard from "../components/RegisterNodeWizard";

type RegisterMode = "choose" | "node" | "edge";

export default function RegisterPage() {
  const [mode, setMode] = useState<RegisterMode>("choose");

  if (mode === "node") {
    return (
      <main className="page register-page">
        <RegisterNodeWizard onCancel={() => setMode("choose")} />
      </main>
    );
  }

  if (mode === "edge") {
    return (
      <main className="page register-page">
        <RegisterEdgeWizard onCancel={() => setMode("choose")} />
      </main>
    );
  }

  return (
    <main className="page register-page">
      <section className="register-choose">
        <h2>登録するものを選ぶ</h2>
        <div className="choose-cards">
          <button type="button" className="choose-card" onClick={() => setMode("node")}>
            <strong>ノードを登録</strong>
            <span>人物・組織・製品などのエンティティ</span>
          </button>
          <button type="button" className="choose-card" onClick={() => setMode("edge")}>
            <strong>関係を登録</strong>
            <span>ノード同士のつながり</span>
          </button>
        </div>
      </section>
    </main>
  );
}
