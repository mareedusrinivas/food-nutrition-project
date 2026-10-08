import { useEffect } from 'react';

/**
 * Parse the query string of the /result route into a typed result object.
 * Replaces the Jinja context variables used by the old result.html template.
 */
const NUTRIENT_FIELDS = [
  'calories',
  'carbohydrates',
  'protein',
  'fat',
  'fiber',
  'sugar',
];

export default function useResultParams(searchParams) {
  const prediction = searchParams.get('prediction') || 'Unknown';
  const image = searchParams.get('image') || '';

  const nutrients = {};
  NUTRIENT_FIELDS.forEach((field) => {
    const raw = searchParams.get(field);
    nutrients[field] = raw === null || raw === '' ? 'N/A' : raw;
  });

  const hasData = Boolean(prediction && prediction !== 'Unknown') || Boolean(image);

  // Keep the document title in sync with the page (was <title> per template).
  useEffect(() => {
    document.title = 'Food Prediction Result';
    return () => {
      document.title = 'Live Food Detection';
    };
  }, []);

  return { prediction, image, nutrients, hasData };
}
