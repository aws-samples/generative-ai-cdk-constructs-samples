import { BDAProvider } from "@/contexts/BDAContext";

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