import { useState } from 'react'
import { useLocale } from '../LocaleContext'

export default function DocumentViewer({ imageUrl, stamps = [], filename }) {
  const [zoom, setZoom] = useState(1)
  const { t } = useLocale()

  return (
    <div className="pane pane-source">
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{fontSize: 16, color: 'var(--accent-cyan)'}}>description</span>
          {t('sourceDoc')}
        </span>
        <div style={{display: 'flex', gap: 4}}>
          <button className="btn" style={{padding: '4px 8px', border: 'none', background: 'var(--bg-hover)'}}
            onClick={() => setZoom(z => Math.min(z + 0.2, 3))}>
            <span className="material-symbols-outlined" style={{fontSize: 16}}>zoom_in</span>
          </button>
          <button className="btn" style={{padding: '4px 8px', border: 'none', background: 'var(--bg-hover)'}}
            onClick={() => setZoom(z => Math.max(z - 0.2, 0.4))}>
            <span className="material-symbols-outlined" style={{fontSize: 16}}>zoom_out</span>
          </button>
          <button className="btn" style={{padding: '4px 8px', border: 'none', background: 'var(--bg-hover)'}}
            onClick={() => setZoom(1)}>
            <span className="material-symbols-outlined" style={{fontSize: 16}}>fit_screen</span>
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
                  border: '2px dashed var(--accent-error)',
                  borderRadius: 4,
                  background: 'rgba(248,113,113,0.08)',
                  pointerEvents: 'none',
                  animation: 'glowPulse 2s ease-in-out infinite',
                }}>
                  <span style={{
                    position: 'absolute', top: -22, left: 0,
                    background: 'var(--accent-error)', color: 'white',
                    fontSize: 10, padding: '2px 8px', borderRadius: 4,
                    fontWeight: 600, fontFamily: 'var(--font-mono)',
                    boxShadow: '0 0 8px rgba(248,113,113,0.3)',
                  }}>
                    Stamp {Math.round(stamp.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="document-placeholder">
              <span className="material-symbols-outlined">description</span>
              <h3>{t('noDoc')}</h3>
              <p>{t('noDocSub')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
