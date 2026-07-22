import { Toaster } from "sonner";

import { AuthProvider } from "@/context/AuthContext";
import { AppRoutes } from "./routes/AppRoutes";

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
      <Toaster richColors position="top-right" />
    </AuthProvider>
  );
}

export default App;
