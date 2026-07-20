import { useEffect, useState } from "react";
import { getHealth } from "../services/api";

export function HomePage() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    getHealth()
      .then(() => setStatus("online"))
      .catch(() => setStatus("offline"));
  }, []);

  return (
    <main>
      <h1>Gestão de Aluguéis</h1>
      <p>Status da API: {status}</p>
    </main>
  );
}
