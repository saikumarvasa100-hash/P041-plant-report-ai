import { useEffect, useRef } from "react";

interface Props {
  title: string;
  /** Rendered under the title in the drawer head, e.g. a status mark. */
  badge?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

/** Right-side detail drawer. Escape closes, focus moves in and returns. */
export default function Drawer({ title, badge, onClose, children, footer }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    triggerRef.current = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      triggerRef.current?.focus();
    };
  }, [onClose]);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={panelRef}
      >
        <div className="drawer-head">
          <div>
            <h2 className="drawer-title">{title}</h2>
            {badge}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label={`Close ${title}`}>
            ✕
          </button>
        </div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-foot">{footer}</div>}
      </div>
    </>
  );
}
