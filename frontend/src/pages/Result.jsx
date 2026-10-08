import { useSearchParams, useNavigate } from 'react-router-dom';
import backImg from '../assets/back.jpg';

// Equivalent of templates/result.html ("Food Prediction Result" page).
// Reads prediction + nutrition data from the query string
// (previously rendered by Flask via render_template context variables).
const cardStyle = {
  background: 'rgba(255, 255, 255, 0.9)',
  padding: '30px',
  borderRadius: '15px',
  boxShadow: '0 8px 15px rgba(0, 0, 0, 0.5)',
  maxWidth: '600px',
  width: '100%',
  textAlign: 'center',
};

const bodyStyle = {
  margin: 0,
  padding: 0,
  fontFamily: "'Poppins', sans-serif",
  color: '#fff',
  minHeight: '100vh',
  backgroundImage: `url(${backImg})`,
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  backgroundRepeat: 'no-repeat',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  flexDirection: 'column',
};

export default function Result() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const prediction = searchParams.get('prediction') || 'Unknown';
  const imagePath = searchParams.get('image') || '';
  const calories = searchParams.get('calories') || 'N/A';
  const carbohydrates = searchParams.get('carbohydrates') || 'N/A';
  const protein = searchParams.get('protein') || 'N/A';
  const fat = searchParams.get('fat') || 'N/A';
  const fiber = searchParams.get('fiber') || 'N/A';

  return (
    <div style={bodyStyle}>
      <header>
        <h1 style={{ color: '#ffe100' }}>Food Prediction Result</h1>
      </header>
      <main style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', width: '100%', padding: '10px' }}>
        <div className="card" style={cardStyle}>
          {imagePath && (
            <img
              src={`/${imagePath.replace(/^\/+/, '')}`}
              alt="Captured Food"
              style={{ maxWidth: '100%', borderRadius: '15px', boxShadow: '0 8px 15px rgba(0, 0, 0, 0.5)', margin: '15px 0' }}
            />
          )}
          <h3 style={{ margin: '10px 0', color: '#f20b0b' }}>Nutritional Information:</h3>
          <h2 style={{ margin: '10px 0', color: '#f20b0b' }}>Prediction: {prediction}</h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: '15px 0', textAlign: 'left' }}>
            <li style={{ margin: '5px 0', fontSize: '1.2rem', color: '#333' }}>
              <strong>Calories:</strong> {calories} kcal
            </li>
            <li style={{ margin: '5px 0', fontSize: '1.2rem', color: '#333' }}>
              <strong>Carbohydrates:</strong> {carbohydrates} g
            </li>
            <li style={{ margin: '5px 0', fontSize: '1.2rem', color: '#333' }}>
              <strong>Protein:</strong> {protein} g
            </li>
            <li style={{ margin: '5px 0', fontSize: '1.2rem', color: '#333' }}>
              <strong>Fat:</strong> {fat} g
            </li>
            <li style={{ margin: '5px 0', fontSize: '1.2rem', color: '#333' }}>
              <strong>Fiber:</strong> {fiber} g
            </li>
          </ul>
          <button onClick={() => navigate('/')}>Retake Image</button>
        </div>
      </main>
    </div>
  );
}
