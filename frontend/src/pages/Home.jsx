import { useNavigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout.jsx';
import ImageUploader from '../components/ImageUploader.jsx';
import LiveFeed from '../components/LiveFeed.jsx';
import CaptureButton from '../components/CaptureButton.jsx';
import ErrorMessage from '../components/ErrorMessage.jsx';
import useImageUpload from '../hooks/useImageUpload.js';
import useCapture from '../hooks/useCapture.js';

// The app is upload-driven: no webcam is opened by default. Set
// VITE_ENABLE_CAMERA=1 (frontend/.env) *and* run the backend with
// ENABLE_CAMERA=1 to bring back the old live-feed capture flow.
const CAMERA_ENABLED = import.meta.env.VITE_ENABLE_CAMERA === '1';

/** Build the /result query string from a prediction payload. */
function resultParams(data) {
  return new URLSearchParams({
    prediction: data.prediction ?? 'Unknown',
    image: data.image ?? '',
    calories: data.calories ?? 'N/A',
    carbohydrates: data.carbohydrates ?? 'N/A',
    protein: data.protein ?? 'N/A',
    fat: data.fat ?? 'N/A',
    fiber: data.fiber ?? 'N/A',
    sugar: data.sugar ?? 'N/A',
  });
}

/** Shared navigation to the Result page after a successful analysis. */
function useGoToResult() {
  const navigate = useNavigate();
  return (data) => {
    if (!data) return; // hooks already surfaced the error inline
    navigate(`/result?${resultParams(data).toString()}`);
  };
}

/**
 * UploadHome — the default "Food Detection" page: pick/drag-drop a photo,
 * press Analyze, and navigate to /result with the prediction + nutrition
 * payload. No camera device is ever touched.
 */
function UploadHome() {
  const goToResult = useGoToResult();
  const {
    file, previewUrl, selectFile, clearFile,
    analyze, processing, error, clearError,
  } = useImageUpload();

  const handleAnalyze = async () => {
    goToResult(await analyze());
  };

  return (
    <MainLayout title="Food Detection">
      <section className="upload-section" id="upload-section" aria-label="Upload a food photo">
        <h2 className="upload-section__title">Upload a Food Photo</h2>
        <p className="upload-section__subtitle">
          Choose an image of your meal and we&apos;ll detect the food and show
          its nutritional information.
        </p>

        <ImageUploader
          previewUrl={previewUrl}
          fileName={file?.name ?? ''}
          onSelect={selectFile}
          onClear={clearFile}
          disabled={processing}
        />

        <CaptureButton
          onCapture={handleAnalyze}
          processing={processing}
          label="Analyze Image"
        />

        <ErrorMessage message={error} onDismiss={clearError} />
      </section>
    </MainLayout>
  );
}

/**
 * CameraHome — legacy live-camera feed page (templates/index.html equivalent),
 * preserved behind VITE_ENABLE_CAMERA=1 so the original feature still works.
 */
function CameraHome() {
  const goToResult = useGoToResult();
  const { capture, processing, error, clearError } = useCapture();

  const handleCapture = async () => {
    goToResult(await capture());
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

export default function Home() {
  return CAMERA_ENABLED ? <CameraHome /> : <UploadHome />;
}
