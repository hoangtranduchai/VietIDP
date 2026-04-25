import { useState } from 'react'

export default function DocumentViewer({ imageUrl, stamps = [], filename }) {
  const [zoom, setZoom] = useState(1)

  return (
    <div className="pane pane-source">
      <div className="pane-header">
        <span className="pane-header-label">SOURCE DOCUMENT</span>
        <div style={{display: 'flex', gap: 4}}>
          <button className="btn" style={{padding: '4px 8px', border: 'none'}}
            onClick={() => setZoom(z => Math.min(z + 0.2, 3))}>
            <span className="material-symbols-outlined" style={{fontSize: 18}}>zoom_in</span>
          </button>
          <button className="btn" style={{padding: '4px 8px', border: 'none'}}
            onClick={() => setZoom(z => Math.max(z - 0.2, 0.4))}>
            <span className="material-symbols-outlined" style={{fontSize: 18}}>zoom_out</span>
          </button>
          <button className="btn" style={{padding: '4px 8px', border: 'none'}}
            onClick={() => setZoom(1)}>
            <span className="material-symbols-outlined" style={{fontSize: 18}}>fit_screen</span>
          </button>
        </div>
      </div>
      <div className="pane-body">
        <div className="document-viewer">
          {imageUrl ? (
            <div className="document-canvas" style={{transform: `scale(${zoom})`, transformOrigin: 'top center'}}>
              <img src={imageUrl} alt={filename || 'Document'} />
              {/* YOLO Stamp BBox overlays */}
              {stamps.map((stamp, i) => (
                <div key={i} style={{
                  position: 'absolute',
                  left: stamp.x1, top: stamp.y1,
                  width: stamp.x2 - stamp.x1,
                  height: stamp.y2 - stamp.y1,
                  border: '2px solid #e63946',
                  borderRadius: 4,
                  background: 'rgba(230,57,70,0.08)',
                  pointerEvents: 'none',
                }}>
                  <span style={{
                    position: 'absolute', top: -20, left: 0,
                    background: '#e63946', color: 'white',
                    fontSize: 10, padding: '1px 6px', borderRadius: 3,
                  }}>
                    Stamp {Math.round(stamp.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="document-placeholder">
              <span className="material-symbols-outlined">description</span>
              <h3>No document loaded</h3>
              <p>Upload a PDF or image to begin processing</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
