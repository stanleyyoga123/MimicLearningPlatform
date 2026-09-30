import { useState } from 'react';

const storageKey = 'mimic.sidebar.expanded';

function initialVisibility(): boolean {
  try {
    const saved = window.localStorage.getItem(storageKey);
    return saved === 'false' ? false : true;
  } catch {
    return true;
  }
}

export function useSidebarVisibility() {
  const [expanded, setExpanded] = useState(initialVisibility);

  const toggle = () => {
    setExpanded((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(storageKey, String(next));
      } catch {
        // The control remains usable when browser storage is unavailable.
      }
      return next;
    });
  };

  return { expanded, toggle };
}
