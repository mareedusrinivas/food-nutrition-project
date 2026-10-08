import { Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home.jsx';
import Result from './pages/Result.jsx';

// Maps the old Flask routes:
//   '/'        -> Home (live camera feed + capture button)
//   '/result'  -> Result (prediction + nutrition info)
//   '*'        -> NotFound (SPA fallback for unknown client-side routes)

function NotFound() {
  return (
    <div className="page page--center">
      <header className="app-header">
        <h1>Page Not Found</h1>
      </header>
      <main>
        <div className="card nutrition-card">
          <h3>The page you are looking for does not exist.</h3>
          <Link className="retake-button" to="/">
            Back to Upload
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/result" element={<Result />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
