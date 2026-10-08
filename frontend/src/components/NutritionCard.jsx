import { NUTRIENT_ROWS } from '../utils/nutrients.js';

/**
 * NutritionCard — reusable card that renders the captured image and the
 * nutrient list, extracted from the repeated markup of result.html's .card.
 */
export default function NutritionCard({ image, imageUrl, prediction, nutrients }) {
  return (
    <div className="card nutrition-card">
      {imageUrl && (
        <img
          src={imageUrl}
          alt={`Captured food predicted as ${prediction}`}
          onError={(e) => {
            // Hide broken thumbnails instead of showing the browser's icon.
            e.currentTarget.style.display = 'none';
          }}
        />
      )}
      <h3>Nutritional Information:</h3>
      <h2>Prediction: {prediction}</h2>
      <ul>
        {NUTRIENT_ROWS.map(({ key, label, unit }) => (
          <li key={key}>
            <strong>{label}:</strong> {nutrients[key]} {unit}
          </li>
        ))}
      </ul>
    </div>
  );
}
