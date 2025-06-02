import { BDAProvider } from "@/contexts/BDAContext";
import { BrowserRouter as Router, Routes } from "react-router-dom";

function App() {
  return (
    <BDAProvider>
      <Router>
        <Routes>
          {/* Routes configuration */}
        </Routes>
      </Router>
    </BDAProvider>
  );
}

export default App; 