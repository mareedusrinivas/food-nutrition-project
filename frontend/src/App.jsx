import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home.jsx';
import Result from './pages/Result.jsx';

// Maps the old Flask routes:
//   '/'        -> Home (live camera feed + capture button)
//   '/result'  -> Result (prediction + nutrition info)
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/result" element={<Result />} />
    </Routes>
  );
}
