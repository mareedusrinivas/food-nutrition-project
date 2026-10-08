import { useNavigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout.jsx';
import LiveFeed from '../components/LiveFeed.jsx';
import CaptureButton from '../components/CaptureButton.jsx';
import ErrorMessage from '../components/ErrorMessage.jsx';
import useCapture from '../hooks/useCapture.js';

/**
 * Home — equivalent of templates/index.html ("Live Camera Feed" page):
 * live MJPEG feed + "Capture Image" button that posts to the backend and
 * navigates to the React /result route with the prediction payload.
 */
export default function Home() {
  const navigate = useNavigate();
  const { capture, processing, error, clearError } = useCapture();

  const handleCapture = async () => {
    const data = await capture();
    if (!data) return; // hook already surfaced the error inline

    // Navigate to the result page with prediction + nutrition data
    const params = new URLSearchParams({
      prediction: data.prediction ?? 'Unknown',
      image: data.image ?? '',
      calories: data.calories ?? 'N/A',
      carbohydrates: data.carbohydrates ?? 'N/A',
      protein: data.protein ?? 'N/A',
      fat: data.fat ?? 'N/A',
      fiber: data.fiber ?? 'N/A',
      sugar: data.sugar ?? 'N/A',
    });
    navigate(`/result?${params.toString()}`);
  };

  return (
    <MainLayout title="Live Food Detection">
      <section className="upload-section" id="video-section" aria-label="Live camera feed">
        <LiveFeed />
        <CaptureButton onCapture={handleCapture} processing={processing} />
        <ErrorMessage message={error} onDismiss={clearError} />
      </section>
    </MainLayout>
  );
}
