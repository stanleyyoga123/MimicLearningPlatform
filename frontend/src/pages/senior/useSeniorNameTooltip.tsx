import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import './seniorNameTooltip.css';

type Placement = 'right' | 'bottom';

type VisibleTooltip = {
  title: string;
  anchor: HTMLElement;
  placement: Placement;
};

const VIEWPORT_PADDING = 8;
const ANCHOR_GAP = 8;

function clamp(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(value, maximum));
}

export function useSeniorNameTooltip() {
  const [visible, setVisible] = useState<VisibleTooltip | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelHide = useCallback(() => {
    if (hideTimer.current !== null) {
      clearTimeout(hideTimer.current);
      hideTimer.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    cancelHide();
    setVisible(null);
  }, [cancelHide]);

  const show = useCallback((anchor: HTMLElement, title: string, placement: Placement) => {
    cancelHide();
    setVisible({ anchor, title, placement });
  }, [cancelHide]);

  const scheduleHide = useCallback(() => {
    cancelHide();
    hideTimer.current = setTimeout(() => setVisible(null), 120);
  }, [cancelHide]);

  useLayoutEffect(() => {
    const tooltip = tooltipRef.current;
    if (!visible || !tooltip) return;

    const anchor = visible.anchor.getBoundingClientRect();
    const width = tooltip.offsetWidth;
    const height = tooltip.offsetHeight;
    const maxLeft = Math.max(VIEWPORT_PADDING, window.innerWidth - width - VIEWPORT_PADDING);
    const maxTop = Math.max(VIEWPORT_PADDING, window.innerHeight - height - VIEWPORT_PADDING);

    let left: number;
    let top: number;
    if (visible.placement === 'right' && anchor.right + ANCHOR_GAP + width <= window.innerWidth - VIEWPORT_PADDING) {
      left = anchor.right + ANCHOR_GAP;
      top = anchor.top;
    } else {
      left = visible.placement === 'right' ? anchor.left : anchor.left + anchor.width / 2 - width / 2;
      top = anchor.bottom + ANCHOR_GAP;
      if (top + height > window.innerHeight - VIEWPORT_PADDING) {
        top = anchor.top - height - ANCHOR_GAP;
      }
    }

    tooltip.style.left = `${clamp(left, VIEWPORT_PADDING, maxLeft)}px`;
    tooltip.style.top = `${clamp(top, VIEWPORT_PADDING, maxTop)}px`;
    tooltip.style.visibility = 'visible';
  }, [visible]);

  useEffect(() => {
    if (!visible) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') hide();
    };
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('scroll', hide, true);
      window.removeEventListener('resize', hide);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [visible, hide]);

  useEffect(() => () => cancelHide(), [cancelHide]);

  const tooltip = visible ? createPortal(
    <div
      ref={tooltipRef}
      className="senior-name-tooltip"
      role="tooltip"
      style={{ visibility: 'hidden' }}
      onMouseEnter={cancelHide}
      onMouseLeave={hide}
    >{visible.title}</div>,
    document.body,
  ) : null;

  return { show, scheduleHide, hide, tooltip };
}
