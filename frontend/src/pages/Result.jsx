import { Link, useSearchParams } from 'react-router-dom';
import { FiRotateCcw, FiInbox } from 'react-icons/fi';
import MainLayout from '../layouts/MainLayout.jsx';
import NutritionCard from '../components/NutritionCard.jsx';
import useResultParams from '../hooks/useResultParams.js';
import { resolveImageUrl } from '../services/api.js';

/**
 * Result — equivalent of templates/result.html ("Food Prediction Result").
 * Reads prediction + nutrition data from the query string (the values the
 * Flask Jinja template used to render server-side).
 */
export default function Result() {
  const [searchParams] = useSearchParams();
  const { prediction, image, nutrients, hasData } = useResultParams(searchParams);

  if (!hasData) {
    return (
      <MainLayout title="Food Prediction Result">
        <div className="card nutrition-card" role="status">
          <FiInbox aria-hidden="true" />
          <h3>No result yet</h3>
          <p>Upload a photo of the food to see its nutritional information.</p>
          <Link className="retake-button" to="/">
            <FiRotateCcw aria-hidden="true" /> Go to Upload
          </Link>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title="Food Prediction Result">
      <NutritionCard
        prediction={prediction}
        imageUrl={resolveImageUrl(image)}
        nutrients={nutrients}
      />
      <Link className="retake-button" to="/">
        <FiRotateCcw aria-hidden="true" /> Analyze Another Image
      </Link>
    </MainLayout>
  );
}
