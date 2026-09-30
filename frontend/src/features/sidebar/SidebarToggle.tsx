import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import './sidebarToggle.css';

type SidebarToggleProps = { expanded: boolean; onToggle: () => void };

export function SidebarToggle({ expanded, onToggle }: SidebarToggleProps) {
  return <button
    type="button"
    className="sidebar-toggle"
    aria-controls="mimic-sidebar"
    aria-expanded={expanded}
    aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
    title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
    onClick={onToggle}
  >{expanded ? <PanelLeftClose size={18} aria-hidden="true" /> : <PanelLeftOpen size={18} aria-hidden="true" />}</button>;
}
