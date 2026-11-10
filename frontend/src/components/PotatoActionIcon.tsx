import type { LucideIcon } from 'lucide-react'

export type PotatoActionTone = 'teal' | 'amber' | 'blue' | 'cyan' | 'orange' | 'violet' | 'rose' | 'indigo' | 'green'

type Props = {
  icon: LucideIcon
  tone?: PotatoActionTone
  size?: 'sm' | 'md' | 'lg'
}

export function PotatoActionIcon({ icon: Icon, tone = 'green', size = 'md' }: Props) {
  return (
    <span className={`potato-action-icon tone-${tone} size-${size}`} aria-hidden="true">
      <svg className="potato-action-shape" viewBox="0 0 64 64" focusable="false">
        <path d="M19.8 8.8C27.1 4.8 38 5.2 45.5 9.9c7.4 4.7 11.7 13.6 10.1 22.2-1.3 7.1-4.9 15.4-11.4 19.4-6.9 4.3-17.5 5.4-25.1 1.9C10.6 49.5 6.2 40 7.3 30.8c1.1-9.3 5.1-18 12.5-22Z" />
        <circle cx="20" cy="24" r="1.8" />
        <circle cx="43" cy="20" r="1.5" />
        <circle cx="39" cy="42" r="1.7" />
        <path className="potato-action-leaf" d="M42.5 10.2c2.5-4.2 6.6-6 11.2-5.1-.6 4.7-3.4 8-8.4 9.1" />
      </svg>
      <Icon className="potato-action-glyph" strokeWidth={1.9} />
    </span>
  )
}
