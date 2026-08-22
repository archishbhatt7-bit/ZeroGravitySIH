import React, { useRef, useState, useEffect } from 'react';
import Globe from 'react-globe.gl';

function App() {
  const globeEl = useRef();
  const [satData, setSatData] = useState([]);

  useEffect(() => {
    // Boilerplate for satellite data
    setSatData([...Array(50).keys()].map(() => ({
      lat: (Math.random() - 0.5) * 180,
      lng: (Math.random() - 0.5) * 360,
      alt: Math.random() * 0.8 + 0.1,
      radius: Math.random() * 2,
      color: ['red', 'white', 'blue', 'green'][Math.round(Math.random() * 3)]
    })));
  }, []);

  return (
    <div className="dashboard-container">
      <div className="glass-panel left-panel">
        <h1>OrbVeil Dashboard</h1>
        <p>Satellite Risk Assessment & Conjunction Feed</p>
        <div className="feed">
          <div className="feed-item">No active conjunctions.</div>
        </div>
      </div>
      
      <div className="globe-container">
        <Globe
          ref={globeEl}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
          objectsData={satData}
          objectLabel="name"
          objectColor="color"
          objectAltitude="alt"
          objectRadius="radius"
          enablePointerInteraction={true}
        />
      </div>
    </div>
  );
}

export default App;
