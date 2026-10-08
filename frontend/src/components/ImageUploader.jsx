import { useCallback, useRef, useState } from 'react';
import { FiUploadCloud, FiX } from 'react-icons/fi';

/**
 * ImageUploader — click-or-drag-and-drop area for choosing a food photo.
 * Replaces the old live-camera feed: no webcam is ever opened.
 * Shows an instant local preview of the selected image with a clear button.
 */
export default function ImageUploader({ previewUrl, fileName, onSelect, onClear, disabled }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const openPicker = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleFiles = useCallback((fileList) => {
    const next = fileList && fileList[0];
    if (next) onSelect(next);
  }, [onSelect]);

  return (
    <div className="image-uploader">
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.bmp,image/*"
        onChange={(e) => {
          handleFiles(e.target.files);
          // Reset so selecting the same file again still fires onChange.
          e.target.value = '';
        }}
        style={{ display: 'none' }}
        aria-hidden="true"
        tabIndex={-1}
      />

      {previewUrl ? (
        <div className="image-uploader__preview">
          <img src={previewUrl} alt={`Selected photo: ${fileName}`} />
          <button
            type="button"
            className="image-uploader__clear"
            onClick={onClear}
            disabled={disabled}
            aria-label="Remove selected image"
            title="Remove selected image"
          >
            <FiX aria-hidden="true" />
          </button>
          <p className="image-uploader__name">{fileName}</p>
        </div>
      ) : (
        <div
          role="button"
          tabIndex={0}
          className={`image-uploader__dropzone${dragging ? ' image-uploader__dropzone--dragging' : ''}`}
          onClick={openPicker}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              openPicker();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (!disabled) handleFiles(e.dataTransfer.files);
          }}
          aria-label="Choose an image of food — click or drag and drop"
        >
          <FiUploadCloud className="image-uploader__icon" aria-hidden="true" />
          <p><strong>Click to upload</strong> or drag &amp; drop</p>
          <p className="image-uploader__hint">JPG, PNG or WEBP · max 10 MB</p>
        </div>
      )}
    </div>
  );
}
