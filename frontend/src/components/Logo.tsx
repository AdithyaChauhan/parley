// Parley's own logo: a teal speech bubble with a "P" (D8: not the reference logo)
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} role="img" aria-label="Parley">
      <path
        d="M7 3h18a5 5 0 0 1 5 5v12a5 5 0 0 1-5 5H14l-6 5v-5H7a5 5 0 0 1-5-5V8a5 5 0 0 1 5-5z"
        className="fill-primary"
      />
      <text x="16" y="19.5" textAnchor="middle" fontSize="15" fontWeight="700" className="fill-white">
        P
      </text>
    </svg>
  )
}
