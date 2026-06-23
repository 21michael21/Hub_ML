import { Dashboard } from "./pages/Dashboard";
import { HubMLPreview } from "./pages/HubMLPreview";

export default function App() {
  if (window.location.pathname === "/hubml-preview") {
    return <HubMLPreview />;
  }

  return <Dashboard />;
}
