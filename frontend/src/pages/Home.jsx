import { useEffect, useRef } from 'react';
import LiveFeed from '../components/LiveFeed.jsx';

// Equivalent of templates/index.html ("Live Camera Feed" page)
export default function Home() {
  const videoSectionRef = useRef(null);

  // Scroll to the video section when the page is loaded (from original index.html script)
  useEffect(() => {
    if (videoSectionRef.current) {
      videoSectionRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  return (
    <>
      <header>
        <h1>Live Food Detection</h1>
      </header>
      <main>
        <div className="upload-section" id="video-section" ref={videoSectionRef}>
          <LiveFeed />
        </div>
      </main>
    </>
  );
}
