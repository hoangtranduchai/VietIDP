import { useState, useEffect } from 'react'
import { useLocale } from '../LocaleContext'

export default function DocumentViewer({ imageUrl, documentUrl = null, useGeneratedPagePreviews = false, stamps = [], highlightBboxes = null, filename, pages = [], pageCount = 0, onPageRequest, style, onToggleCollapse, isCollapsed }) {
  const [zoom, setZoom] = useState(1)
  const [imgSize, setImgSize] = useState({ w: 1, h: 1 })
  const [currentPageIndex, setCurrentPageIndex] = useState(0)
  const [currentStampIndex, setCurrentStampIndex] = useState(-1)
  const { t } = useLocale()
  
  const isPdf = (filename || imageUrl || '').toLowerCase().endsWith('.pdf')
  const usesImagePages = !isPdf || useGeneratedPagePreviews

  const totalPages = Math.max(pageCount, pages.length, imageUrl ? 1 : 0)
  const allPages = Array.from({ length: totalPages }, (_, index) => pages[index] || null)
  const currentImage = allPages[currentPageIndex] || null

  useEffect(() => {
    setCurrentPageIndex((current) => Math.min(current, Math.max(totalPages - 1, 0)))
  }, [totalPages])

  useEffect(() => {
    if (usesImagePages && onPageRequest && totalPages > 0) {
      onPageRequest(currentPageIndex)
    }
  }, [currentPageIndex, onPageRequest, totalPages, usesImagePages])

  useEffect(() => {
    if (highlightBboxes && highlightBboxes.length > 0) {
      const firstBbox = highlightBboxes[0]
      const pageIdx = (firstBbox.page || 1) - 1
      if (currentPageIndex !== pageIdx) {
        setCurrentPageIndex(pageIdx)
      }
    }
  }, [highlightBboxes, currentPageIndex])

  const handleNextStamp = () => {
    if (stamps.length === 0) return
    const nextIdx = (currentStampIndex + 1) % stamps.length
    setCurrentStampIndex(nextIdx)
    if (stamps[nextIdx].page) setCurrentPageIndex(stamps[nextIdx].page - 1)
  }

  const handlePrevStamp = () => {
    if (stamps.length === 0) return
    const prevIdx = (currentStampIndex - 1 + stamps.length) % stamps.length
    setCurrentStampIndex(prevIdx)
    if (stamps[prevIdx].page) setCurrentPageIndex(stamps[prevIdx].page - 1)
  }

  return (
    <div className="pane pane-source" style={{ ...style, transition: isCollapsed ? 'width 0.3s var(--ease)' : 'none', position: 'relative' }}>
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
          {onToggleCollapse && (
            <button className="btn" style={{padding: '4px 8px', border: 'none', background: 'var(--bg-hover)', marginLeft: 8}}
              onClick={onToggleCollapse} title={isCollapsed ? 'Mở rộng cột bên' : 'Thu gọn cột bên'}>
              <span className="material-symbols-outlined" style={{fontSize: 16}}>
                {isCollapsed ? 'keyboard_double_arrow_left' : 'keyboard_double_arrow_right'}
              </span>
            </button>
          )}
        </div>
      </div>
      <div className="pane-body" style={{ display: 'flex', flexDirection: 'row', position: 'relative' }}>
        
        {/* Thumbnail Sidebar */}
        {usesImagePages && totalPages > 0 && (
          <div style={{
            width: 80, borderRight: '1px solid var(--border)', background: 'var(--bg-elevated)',
            display: 'flex', flexDirection: 'column', gap: 10, padding: 10, overflowY: 'auto', flexShrink: 0
          }}>
            {allPages.map((pageUrl, idx) => (
              <div
                key={idx}
                onClick={() => setCurrentPageIndex(idx)}
                style={{
                  width: '100%', aspectRatio: '1/1.4', borderRadius: 4, cursor: 'pointer',
                  border: currentPageIndex === idx ? '2px solid var(--accent)' : '1px solid var(--border)',
                  overflow: 'hidden', position: 'relative',
                  background: 'white', opacity: currentPageIndex === idx ? 1 : 0.6,
                  transition: 'all 0.2s',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}
              >
                {pageUrl ? (
                  <img src={pageUrl} style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt={`Page ${idx + 1}`} />
                ) : (
                  <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--text-muted)' }}>hourglass_top</span>
                )}
                {stamps.length > 0 && currentPageIndex === idx && (
                  <div style={{ position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-error)' }} />
                )}
                <div style={{ position: 'absolute', bottom: 0, width: '100%', background: 'rgba(0,0,0,0.6)', color: 'white', fontSize: 9, textAlign: 'center', padding: '2px 0' }}>{idx + 1}</div>
              </div>
            ))}
          </div>
        )}

        {/* Main Viewer */}
        <div className="document-viewer" style={{ flex: 1, position: 'relative', overflow: 'auto' }}>
          
          {/* Stamp Navigator Overlay */}
          {usesImagePages && stamps.length > 0 && (
            <div style={{
              position: 'absolute', top: 16, right: 16, zIndex: 100,
              background: 'rgba(10, 14, 23, 0.85)', backdropFilter: 'blur(10px)',
              border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-full)',
              padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 12,
              boxShadow: '0 4px 15px rgba(0,0,0,0.2)'
            }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>
                {stamps.length} Con dấu
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <button onClick={handlePrevStamp} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>chevron_left</span>
                </button>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', minWidth: 36, textAlign: 'center' }}>
                  {currentStampIndex >= 0 ? currentStampIndex + 1 : '-'} / {stamps.length}
                </span>
                <button onClick={handleNextStamp} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>chevron_right</span>
                </button>
              </div>
            </div>
          )}

          {isPdf && !useGeneratedPagePreviews ? (
            documentUrl ? (
              <div className="document-canvas" style={{ height: '100%', minHeight: 600 }}>
                <iframe src={`${documentUrl}#toolbar=0&navpanes=0&scrollbar=0`} width="100%" height="100%" style={{ border: 'none', borderRadius: 4 }} title="PDF Document" />
              </div>
            ) : (
              <div className="document-placeholder">
                <span className="material-symbols-outlined">description</span>
                <h3>{t('noDoc')}</h3>
                <p>{t('noDocSub')}</p>
              </div>
            )
          ) : currentImage ? (
            <div className="document-canvas" style={{ width: `${zoom * 100}%`, transition: 'width 0.2s var(--ease)', margin: '0 auto', position: 'relative' }}>
              <img
                src={currentImage}
                alt={filename || 'Document'}
                onLoad={(e) => setImgSize({ w: e.target.naturalWidth || 1, h: e.target.naturalHeight || 1 })}
              />
              {/* YOLO Stamp BBox overlays */}
              {stamps.map((stamp, i) => {
                if ((stamp.page || 1) !== currentPageIndex + 1) return null

                return (
                  <div key={i} style={{
                    position: 'absolute',
                    left: `${(stamp.x1 / imgSize.w) * 100}%`, top: `${(stamp.y1 / imgSize.h) * 100}%`,
                    width: `${((stamp.x2 - stamp.x1) / imgSize.w) * 100}%`,
                    height: `${((stamp.y2 - stamp.y1) / imgSize.h) * 100}%`,
                    border: currentStampIndex === i ? '3px solid var(--accent-error)' : '2px solid rgba(248,113,113,0.6)',
                    borderRadius: 4,
                    background: currentStampIndex === i ? 'rgba(248,113,113,0.2)' : 'rgba(248,113,113,0.05)',
                    pointerEvents: 'none',
                    animation: currentStampIndex === i ? 'glowPulse 1.5s ease-in-out infinite' : 'none',
                    boxShadow: currentStampIndex === i ? '0 0 25px rgba(248,113,113,0.6), inset 0 0 15px rgba(248,113,113,0.3)' : 'none',
                    zIndex: currentStampIndex === i ? 20 : 10,
                    transition: 'all 0.3s'
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
                      Dấu pháp lý - Confidence: {Math.round(stamp.confidence * 100)}%
                    </div>
                  </div>
                )
              })}

              {/* Text Grounding BBox overlays */}
              {highlightBboxes && highlightBboxes.map((bbox, i) => {
                if ((bbox.page || 1) !== currentPageIndex + 1) return null

                return (
                  <div key={`hl-${i}`} style={{
                    position: 'absolute',
                    left: `${(bbox.x1 / imgSize.w) * 100}%`, top: `${(bbox.y1 / imgSize.h) * 100}%`,
                    width: `${((bbox.x2 - bbox.x1) / imgSize.w) * 100}%`,
                    height: `${((bbox.y2 - bbox.y1) / imgSize.h) * 100}%`,
                    border: '2px solid var(--accent-cyan)',
                    borderRadius: 2,
                    background: 'rgba(34, 211, 238, 0.2)',
                    pointerEvents: 'none',
                    boxShadow: '0 0 10px rgba(34, 211, 238, 0.5), inset 0 0 5px rgba(34, 211, 238, 0.3)',
                    zIndex: 15,
                  }} />
                )
              })}
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
