import React, { useState } from 'react';
import { EvidenceItem } from '../types';
import { Image as ImageIcon, Maximize2, X } from 'lucide-react';

interface EvidenceGalleryProps {
  items: EvidenceItem[];
}

export const EvidenceGallery: React.FC<EvidenceGalleryProps> = ({ items }) => {
  const [selectedImage, setSelectedImage] = useState<EvidenceItem | null>(null);

  if (!items || items.length === 0) {
    return null;
  }

  // Backend URL from Vercel environment variable.
  // Example:
  // VITE_API_URL=https://centralign-ai-9imx.onrender.com
  const API_BASE = (import.meta.env.VITE_API_URL || window.location.origin).replace(
    /\/+$/,
    ''
  );

  /**
   * Convert the backend's stored screenshot path
   * into a browser-accessible URL.
   */
  const getImageUrl = (path: string) => {
    if (!path) {
      return '';
    }

    // Already an absolute URL
    if (/^https?:\/\//i.test(path)) {
      return path;
    }

    // Normalize Windows paths and remove whitespace
    let normalizedPath = path.trim().replace(/\\/g, '/');

    // Remove ./ or ../ prefixes
    normalizedPath = normalizedPath.replace(/^(\.\.\/|\.\/)+/, '');

    // If backend returns something like:
    // /evidence/file.png
    // evidence/file.png
    // ./evidence/file.png
    //
    // normalize all of them to:
    // /evidence/file.png
    const evidenceIndex = normalizedPath.indexOf('evidence/');

    if (evidenceIndex !== -1) {
      normalizedPath = normalizedPath.substring(evidenceIndex);
    }

    // Remove leading slash before rebuilding the URL
    normalizedPath = normalizedPath.replace(/^\/+/, '');

    return `${API_BASE}/${normalizedPath}`;
  };

  return (
    <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm">

      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
            <ImageIcon className="w-5 h-5" />
          </div>

          <div>
            <h2 className="text-base font-semibold text-white">
              Execution Evidence & Screenshots
            </h2>

            <p className="text-xs text-slate-400">
              Verifiable visual artifacts captured at critical milestones
            </p>
          </div>
        </div>

        <span className="text-xs font-mono text-slate-400">
          {items.length} Artifact{items.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Evidence Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

        {items.map((item, idx) => {
          const imageUrl = getImageUrl(item.path);

          return (
            <div
              key={item.id || idx}
              onClick={() => setSelectedImage(item)}
              className="group relative bg-slate-900 border border-slate-700 rounded-xl overflow-hidden cursor-pointer hover:border-indigo-500/70 transition shadow-md"
            >

              {/* Image */}
              <div className="aspect-video w-full bg-slate-950 overflow-hidden relative">

                <img
                  src={imageUrl}
                  alt={item.description || 'Execution evidence'}
                  className="w-full h-full object-cover object-top group-hover:scale-105 transition duration-300"
                  onError={(e) => {
                    console.error('Failed to load evidence image:', imageUrl);

                    const img = e.currentTarget;

                    img.onerror = null;

                    img.src =
                      'data:image/svg+xml;utf8,' +
                      '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">' +
                      '<rect fill="%231e293b" width="300" height="200"/>' +
                      '<text fill="%2364748b" font-family="sans-serif" font-size="12" dy="10.5" font-weight="bold" x="50%" y="50%" text-anchor="middle">' +
                      'Screenshot Captured' +
                      '</text>' +
                      '</svg>';
                  }}
                />

                {/* Hover overlay */}
                <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center pointer-events-none">
                  <div className="p-2 rounded-full bg-slate-900/80 text-white backdrop-blur-sm">
                    <Maximize2 className="w-4 h-4" />
                  </div>
                </div>

              </div>

              {/* Caption */}
              <div className="p-3">

                <p className="text-xs font-medium text-slate-200 line-clamp-1">
                  {item.description || 'Screenshot evidence'}
                </p>

                <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                  {new Date(item.created_at).toLocaleTimeString()}
                </span>

              </div>

            </div>
          );
        })}

      </div>

      {/* Modal / Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >

          <div
            className="bg-slate-900 border border-slate-700 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >

            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">

              <div>
                <h4 className="text-sm font-semibold text-white">
                  {selectedImage.description || 'Evidence View'}
                </h4>

                <span className="text-xs text-slate-400 font-mono">
                  {new Date(selectedImage.created_at).toLocaleString()}
                </span>
              </div>

              <button
                onClick={() => setSelectedImage(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>

            </div>

            {/* Full Image */}
            <div className="p-4 overflow-auto flex-1 flex items-center justify-center bg-slate-950">

              <img
                src={getImageUrl(selectedImage.path)}
                alt={selectedImage.description || 'Screenshot'}
                className="max-w-full max-h-[70vh] object-contain rounded-lg border border-slate-800"
                onError={(e) => {
                  console.error(
                    'Failed to load selected evidence image:',
                    getImageUrl(selectedImage.path)
                  );

                  e.currentTarget.style.display = 'none';
                }}
              />

            </div>

          </div>

        </div>
      )}

    </div>
  );
};

export default EvidenceGallery;