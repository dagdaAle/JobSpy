interface IconProps {
  name: string;
  className?: string;
  filled?: boolean;
}

/** Thin wrapper around a Material Symbols Outlined glyph. */
export function Icon({ name, className = "", filled = false }: IconProps) {
  return (
    <span
      className={`material-symbols-outlined ${filled ? "fill-icon" : ""} ${className}`}
      aria-hidden="true"
    >
      {name}
    </span>
  );
}
