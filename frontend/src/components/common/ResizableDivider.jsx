import { useEffect, useRef, useCallback } from 'react';
import { COLORS, Z_INDEX } from '../../styles/tokens';

function ResizableDivider({ side, visible = true, onWidthChange, onDragStateChange, containerRef }) {
  const isDraggingRef = useRef(false);

  const handleMouseMove = useCallback((e) => {
    if (!isDraggingRef.current || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const mouseX = e.clientX - containerRect.left;

    if (side === 'left') {
      const newWidth = Math.max(15, Math.min(35, (mouseX / containerWidth) * 100));
      onWidthChange(newWidth);
    } else {
      const mousePercent = (mouseX / containerWidth) * 100;
      const newWidth = Math.max(15, Math.min(35, 100 - mousePercent));
      onWidthChange(newWidth);
    }
  }, [side, onWidthChange, containerRef]);

  const handleMouseUp = useCallback(() => {
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      onDragStateChange?.(false);
    }
  }, [onDragStateChange]);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    isDraggingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    onDragStateChange?.(true);
  }, [onDragStateChange]);

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  if (!visible) return null;

  return (
    <div
      onMouseDown={handleMouseDown}
      style={{
        width: '4px',
        height: '100%',
        background: COLORS.border,
        cursor: 'col-resize',
        position: 'relative',
        zIndex: Z_INDEX.divider,
        flexShrink: 0,
      }}
      onMouseEnter={(e) => { e.target.style.background = COLORS.primary; }}
      onMouseLeave={(e) => { e.target.style.background = COLORS.border; }}
    >
      <div style={{
        position: 'absolute',
        left: '1px',
        top: '50%',
        transform: 'translateY(-50%)',
        width: '2px',
        height: '20px',
        background: COLORS.textTertiary,
        borderRadius: '2px',
      }} />
    </div>
  );
}

export default ResizableDivider;
