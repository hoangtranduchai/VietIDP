import { useState } from 'react'
import { useLocale } from '../LocaleContext'

export default function DocumentViewer({ imageUrl, stamps = [], filename }) {
  const [zoom, setZoom] = useState(1)
  const [imgSize, setImgSize] = useState({ w: 1, h: 1 })
  const { t } = useLocale()
  
  const isPdf = imageUrl?.toLowerCase().endsWith('.pdf')

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
            isPdf ? (
              <div className="document-canvas" style={{ height: '100%', minHeight: 600 }}>
                <iframe src={`${imageUrl}#toolbar=0&navpanes=0&scrollbar=0`} width="100%" height="100%" style={{ border: 'none', borderRadius: 4 }} title="PDF Document" />
              </div>
            ) : (
              <div className="document-canvas" style={{transform: `scale(${zoom})`, transformOrigin: 'top center'}}>
                <img 
                  src={imageUrl} 
                  alt={filename || 'Document'} 
                  onLoad={(e) => setImgSize({ w: e.target.naturalWidth || 1, h: e.target.naturalHeight || 1 })}
                />
                {/* YOLO Stamp BBox overlays */}
                {stamps.map((stamp, i) => (
                  <div key={i} style={{
                    position: 'absolute',
                    left: `${(stamp.x1 / imgSize.w) * 100}%`, top: `${(stamp.y1 / imgSize.h) * 100}%`,
                    width: `${((stamp.x2 - stamp.x1) / imgSize.w) * 100}%`,
                    height: `${((stamp.y2 - stamp.y1) / imgSize.h) * 100}%`,
                    border: '2px solid var(--accent-error)',
                    borderRadius: 4,
                    background: 'rgba(248,113,113,0.1)',
                    pointerEvents: 'none',
                    animation: 'glowPulse 2s ease-in-out infinite',
                    boxShadow: '0 0 15px rgba(248,113,113,0.4), inset 0 0 10px rgba(248,113,113,0.2)',
                    zIndex: 10
                  }}>
                    <div style={{
                      position: 'absolute', top: -24, left: -2,
                      background: 'var(--accent-error)', color: 'white',
                      fontSize: 11, padding: '2px 8px', borderRadius: 4,
                      fontWeight: 700, fontFamily: 'var(--font-display)',
                      boxShadow: '0 2px 8px rgba(248,113,113,0.4)',
                      display: 'flex', alignItems: 'center', gap: 4,
                      whiteSpace: 'nowrap'
                    }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14 }}>verified</span>
                      YOLOv8: Stamp {Math.round(stamp.confidence * 100)}%
                    </div>
                  </div>
                ))}
              </div>
            )
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
