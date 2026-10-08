import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// Live camera feed + capture button.
// Replaces the <img src="/live_feed"> and the static/js/script.js capture logic.
// The Flask backend exposes a JSON API at /api/capture that returns
// { prediction, image, calories, carbohydrates, protein, fat, fiber, sugar }.
export default function LiveFeed() {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleCapture = async () => {
    setProcessing(true);
    setError('');
    try {
      const response = await fetch('/api/capture', { method: 'POST' });
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      const data = await response.json();
      if (data.error) {
        throw new Error(data.error);
      }
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
    } catch (err) {
      console.error('Error capturing image:', err);
      setError(err.message || 'Failed to capture image. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <>
      <img src="/live_feed" id="video-feed" alt="Live Feed" />
      <button id="capture-button" onClick={handleCapture} disabled={processing}>
        {processing ? 'Processing...' : 'Capture Image'}
      </button>
      {error && <p style={{ color: '#ff4d4d', marginTop: '10px' }}>{error}</p>}
    </>
  );
}
